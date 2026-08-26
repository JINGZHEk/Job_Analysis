"""端到端编排管线：采集治理 → 抽取 → 图谱写入 → 新岗位发现 → 匹配。

这是系统的核心引擎，FastAPI 与评测脚本都复用它。
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config, load_config
from .graph import TemporalGraph
from .ingest import IngestionPipeline
from .llm import build_extractor
from .models import Claim, MatchResult, Resume, RoleDefinition
from .resume_match import build_learning_path, diagnose_match, parse_resume
from .roles import STANDARD_ROLES, diff_role_skills, discover_roles
from .skills import category_of, extract_skills_from_text, normalize_skill
from .trust import compute_trust_score, trust_verdict


class Pipeline:
    def __init__(self, config: Optional[Config] = None, data_dir: Optional[Path] = None):
        self.config = config or load_config()
        self.data_dir = Path(data_dir) if data_dir else Path(self.config.get("app", "data_dir", default="data"))
        self.graph = TemporalGraph(self.data_dir / "graph")
        self.ingestor = IngestionPipeline(self.config)
        self.extractor = build_extractor(self.config)
        self._jobs: list[dict] = []          # 治理后的 job 记录
        self._raw_jobs: list[dict] = []      # 原始 job 记录

    # ---------- 数据加载 ----------
    def load_data(self) -> None:
        jds_path = self.data_dir / "jds.json"
        if jds_path.exists():
            self._raw_jobs = json.loads(jds_path.read_text(encoding="utf-8"))

    def run_ingestion(self) -> list[dict]:
        """治理：去重 + 打标签 + 可信度评分，返回治理后 job 列表。"""
        self.load_data()
        jobs = self.ingestor.run(self._raw_jobs)
        result = []
        for j in jobs:
            skills = extract_skills_from_text(j.description)
            # 跨源一致性：统计提到相同技能的 JD 数量
            source_count = min(3, 1 + sum(
                1 for k in jobs
                if k.job_id != j.job_id and
                bool(set(skills) & set(extract_skills_from_text(k.description)))
            ))
            comp = compute_trust_score(
                source_type=j.source.source_type,
                published_at=j.source.published_at,
                source_count=source_count,
                extraction_confidence=0.85,
                duplication_risk=j.duplication_risk,
                has_evidence=bool(j.description),
                is_verified=False,
                config=self.config,
            )
            d = j.to_dict()
            d["trust"] = comp
            d["trust"]["verdict"] = trust_verdict(comp["trust_score"], self.config)
            d["skills"] = skills
            result.append(d)
        self._jobs = result
        return result

    # ---------- 抽取 + 图谱 ----------
    def extract_all(self) -> list[dict]:
        """对每条 JD 做结构化抽取，返回抽取结果。"""
        extracted = []
        for j in self._jobs:
            ex = self.extractor.extract_job(j)
            ex["job_id"] = j["job_id"]
            ex["trust"] = j.get("trust", {})
            extracted.append(ex)
        return extracted

    def build_graph(self, reset: bool = False) -> TemporalGraph:
        """将抽取结果全量重建写入版本化图谱（幂等）。"""
        self.graph.clear()
        extracted = self.extract_all()
        for ex in extracted:
            role_id = f"role:{ex['job_title']}"
            self.graph.upsert_node(
                role_id, "Role", name=ex["job_title"],
                industry=ex.get("industry", ""),
                level=ex.get("level", ""),
            )
            # 职责
            for r in ex.get("responsibilities", [])[:5]:
                resp_id = f"resp:{r[:20]}"
                self.graph.upsert_node(resp_id, "Responsibility", name=r[:20])
                self.graph.add_edge(role_id, resp_id, "has_responsibility",
                                    source_id=ex["job_id"], evidence_span=r)
            # 技能
            trust = ex.get("trust", {})
            trust_score = trust.get("trust_score", 0.5)
            for s in ex.get("required_skills", []):
                self._add_skill_claim(role_id, s, ex, required=True, trust_score=trust_score)
            for s in ex.get("preferred_skills", []):
                self._add_skill_claim(role_id, s, ex, required=False, trust_score=trust_score)
        self.graph.commit("build graph from extracted jobs")
        return self.graph

    def _add_skill_claim(self, role_id: str, skill: str, ex: dict, required: bool, trust_score: float) -> None:
        canon = normalize_skill(skill) or skill
        skill_id = f"skill:{canon}"
        obs = datetime.now().isoformat()
        first = self.graph.G.nodes[skill_id].get("first_seen", "") if skill_id in self.graph.G else ""
        self.graph.upsert_node(
            skill_id, "Skill", name=canon, category=category_of(canon),
            first_seen=first or obs, last_seen=obs,
            occurrence_count=self.graph.G.nodes[skill_id].get("occurrence_count", 0) + 1
            if skill_id in self.graph.G else 1,
        )
        evidence = next((e["span"] for e in ex.get("evidence", [])
                         if e.get("field") == "required_skills" and skill in e.get("span", "")), "")
        self.graph.add_edge(
            role_id, skill_id, "requires" if required else "preferred_requires",
            source_id=ex["job_id"],
            evidence_span=evidence,
            observed_at=obs,
            valid_from=obs[:10],
            valid_to=None,
            trust_score=trust_score,
            confidence=0.85,
            verification_status="verified" if evidence else "unverified",
            review_status="published" if trust_score >= 0.45 else "pending",
            is_required=required,
        )

    # ---------- 岗位发现与更新 ----------
    def discover_new_roles(self, known_roles: list[str] | None = None) -> list[dict]:
        """发现候选新岗位。默认以 STANDARD_ROLES 作为已标准化岗位基线。"""
        baseline = known_roles if known_roles else STANDARD_ROLES
        roles = discover_roles(self._jobs, baseline, self.config)
        return [r.to_dict() for r in roles]

    def role_timeline(self, role_name: str, window_a: str, window_b: str) -> dict:
        """对比两个时间窗口的技能，返回演化 diff。"""
        def skills_in_window(before: str, after: str) -> list[dict]:
            out = []
            for j in self._jobs:
                pub = j.get("source", {}).get("published_at", "")
                if before <= pub < after and j.get("title") == role_name:
                    for s in extract_skills_from_text(j["description"]):
                        if not any(x["skill"] == s for x in out):
                            out.append({"skill": s, "is_required": True,
                                        "source_id": j["job_id"], "observed_at": pub})
            return out

        old_skills = skills_in_window(window_a, window_b)
        new_skills = skills_in_window(window_b, "9999")
        return diff_role_skills(role_name, old_skills, new_skills)

    # ---------- 全景图谱 ----------
    def panorama(self, industry: str = "", tech_stack: str = "", level: str = "") -> dict:
        return self.graph.subgraph_by_filter(industry, tech_stack, level)

    # ---------- 简历 + 匹配 ----------
    def parse_and_match(self, resume_text: str, role_name: str, resume_id: str = "", name: str = "") -> dict:
        resume = parse_resume(resume_text, resume_id, name)
        required, preferred = self._role_skill_sets(role_name)
        match = diagnose_match(resume, required, preferred, role_name, self.config)
        path = build_learning_path(match.missing_skills, {m.name for m in resume.skills})
        return {
            "resume": resume.to_dict(),
            "match": match.to_dict(),
            "learning_path": [s.to_dict() for s in path],
        }

    def _role_skill_sets(self, role_name: str) -> tuple[list[dict], list[dict]]:
        """聚合岗位技能集（技能名统一为去前缀的展示名）。

        采用频率聚合：某技能被该岗位 >= 60% 的 JD 抽取为「必备」才作为
        核心必备技能，>= 40% 抽取为「加分」才作为加分技能，避免把各公司
        采样差异导致的「并集污染」当作岗位画像。与评测口径一致。
        """
        jds_of_role = [j for j in self._jobs if j.get("title") == role_name]
        n = len(jds_of_role) or 1

        req_counter: Counter = Counter()
        pref_counter: Counter = Counter()
        for j in jds_of_role:
            ex = self.extractor.extract_job(j)
            for s in ex.get("required_skills", []):
                req_counter[normalize_skill(s) or s] += 1
            for s in ex.get("preferred_skills", []):
                pref_counter[normalize_skill(s) or s] += 1

        def _freq(c: Counter, threshold: float, is_required: bool) -> list[dict]:
            return [{"skill": s, "is_required": is_required,
                     "frequency": round(cnt / n, 2)}
                    for s, cnt in c.most_common() if cnt / n >= threshold]

        # 核心必备：>=60% JD 抽取；加分：>=40% JD 抽取
        req = _freq(req_counter, 0.6, True)
        pref = _freq(pref_counter, 0.4, False)

        if not req:
            # 回退到图谱并集
            role_id = f"role:{role_name}"
            sets = self.graph.role_skills(role_id)
            def _strip(items):
                out = []
                seen = set()
                for it in items:
                    name = it.get("name", it.get("skill", ""))
                    if name.startswith("skill:"):
                        name = name.split(":", 1)[1]
                    if name in seen:
                        continue
                    seen.add(name)
                    it["skill"] = name
                    out.append(it)
                return out
            return _strip(sets["required"]), _strip(sets["preferred"])
        return req, pref

    def known_roles(self) -> list[str]:
        return sorted({j.get("title", "") for j in self._jobs})


def bootstrap(data_dir: Optional[Path] = None, config: Optional[Config] = None) -> Pipeline:
    """一键构建：治理 + 抽取 + 图谱。"""
    p = Pipeline(config, data_dir)
    p.run_ingestion()
    p.build_graph()
    return p
