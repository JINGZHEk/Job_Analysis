"""新岗位发现与既有岗位动态更新（FR-04 / FR-05）。"""
from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from .config import Config
from .models import Evidence, RoleDefinition
from .skills import extract_skills_from_text

# 已标准化的既有岗位（用于新岗位发现时排除；真实系统应由图谱本体维护）
STANDARD_ROLES = [
    "人工智能算法工程师", "大数据开发工程师", "Java 开发工程师", "NLP 算法工程师",
    "大模型算法工程师", "CV 算法工程师", "推荐算法工程师", "知识图谱工程师",
    "物联网嵌入式工程师", "边缘计算工程师", "机器人算法工程师", "MLOps 工程师",
]


def _title_clusters(jobs: list[dict]) -> dict[str, list[dict]]:
    """按岗位标题精确分组。"""
    out: dict[str, list[dict]] = {}
    for j in jobs:
        out.setdefault(j["title"], []).append(j)
    return out


def discover_roles(
    jobs: list[dict],
    known_roles: list[str],
    config: Config,
    min_cluster_size: int = 3,
) -> list[RoleDefinition]:
    """发现候选新岗位。

    策略：标题精确分组 -> 过滤已知岗位 -> 按簇大小/跨源一致性/增长率排序。
    技能画像来自该标题簇内所有 JD 的技能并集。
    """
    title_clusters = _title_clusters(jobs)
    known_set = set(known_roles)
    candidates: list[RoleDefinition] = []

    for i, (title, members) in enumerate(title_clusters.items()):
        if title in known_set:
            continue  # 已知岗位，走「既有岗位更新」流程
        if len(members) < min_cluster_size:
            continue

        skill_counter = Counter()
        for m in members:
            for s in extract_skills_from_text(m["description"]):
                skill_counter[s] += 1
        # 至少被 60% 的成员提及才作为必备技能，其余为加分
        all_skills = [s for s, _ in skill_counter.most_common()]
        required = [s for s in all_skills if skill_counter[s] >= max(1, len(members) * 0.6)][:6]
        preferred = [s for s in all_skills if s not in required][:6]

        sources = {m.get("source", {}).get("source_type") for m in members}
        cross_source = len(sources)
        growth = round(len(members) / max(1, len(jobs) / 50), 3)
        emergence = min(1.0, 0.35 * (len(members) / min_cluster_size)
                        + 0.3 * min(1.0, cross_source / 2) + 0.35 * growth)
        emergence = min(1.0, emergence + 0.15)

        scenarios = list({m.get("industry", "人工智能") for m in members})[:3]
        evidence = [
            Evidence(
                source_id=m["job_id"],
                evidence_span=m["description"][:80],
                source_type=m.get("source", {}).get("source_type", ""),
                observed_at=m.get("source", {}).get("published_at", ""),
            )
            for m in members[:3]
        ]
        candidates.append(RoleDefinition(
            role_id=f"candidate-{i}",
            name=title,
            core_responsibilities=list({r for m in members
                                        for r in _responsibilities(m["description"])})[:5],
            required_skills=required,
            preferred_skills=preferred,
            typical_scenarios=scenarios,
            industry=scenarios[0] if scenarios else "",
            evidence=evidence,
            is_new=True,
            emergence_score=round(emergence, 3),
            lifecycle="增长" if growth >= 1.0 else "萌芽",
        ))
    candidates.sort(key=lambda r: r.emergence_score, reverse=True)
    return candidates


def _responsibilities(desc: str) -> list[str]:
    out = []
    for m in re.finditer(r"(负责|参与|主导|设计|搭建|开发|优化|构建|实现)[^。；;\n]{6,60}", desc):
        seg = m.group(0).strip()
        if seg not in out:
            out.append(seg)
    return out[:6]


def diff_role_skills(
    role_id: str,
    old_skills: list[dict],
    new_skills: list[dict],
) -> dict:
    """比较两个时间窗口的技能，输出新增/删除/修改。"""
    old_map = {s["skill"]: s for s in old_skills}
    new_map = {s["skill"]: s for s in new_skills}
    old_set, new_set = set(old_map), set(new_map)

    added = [{"skill": s, **new_map[s]} for s in sorted(new_set - old_set)]
    removed = [{"skill": s, **old_map[s]} for s in sorted(old_set - new_set)]
    modified = []
    for s in sorted(old_set & new_set):
        o, n = old_map[s], new_map[s]
        if (o.get("is_required") != n.get("is_required")
                or o.get("proficiency") != n.get("proficiency")):
            modified.append({"skill": s, "before": o, "after": n})

    return {
        "role_id": role_id,
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": (
            f"新增 {len(added)} 项能力，删除 {len(removed)} 项能力，"
            f"修改 {len(modified)} 项能力"
        ),
    }
