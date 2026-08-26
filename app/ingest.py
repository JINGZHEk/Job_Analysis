"""数据接入与可信治理管线（FR-01 / FR-02）。

输入：原始 job 记录（title/description/source 等）。
输出：清洗后的 Job + quality_flags + duplication_risk + trust 相关字段。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from .config import Config
from .dedup import NearDuplicateDetector
from .models import Job, SourceMeta
from .skills import extract_skills_from_text
from .trust import compute_trust_score, trust_verdict


def _parse_source(raw: dict) -> SourceMeta:
    src = raw.get("source", {})
    return SourceMeta(
        source_type=src.get("source_type", "招聘平台"),
        url=src.get("url", ""),
        publisher=src.get("publisher", ""),
        published_at=src.get("published_at", ""),
        collected_at=src.get("collected_at", datetime.now().isoformat()),
        language=src.get("language", "zh"),
        file_hash=src.get("file_hash", ""),
    )


def detect_quality_flags(job: Job, skills_count: int, rare_count: int) -> list[str]:
    """识别空字段、异常字符、过期内容、模板复制、技能通胀。"""
    flags: list[str] = []
    desc = job.description
    if not job.title:
        flags.append("empty_title")
    if len(desc) < 30:
        flags.append("empty_description")
    if re.search(r"[�]{2,}|�", desc):
        flags.append("garbled_chars")
    if skills_count == 0:
        flags.append("no_skill")
    if rare_count / max(1, skills_count) > 0.5 and skills_count >= 6:
        flags.append("skill_inflation")
    if job.duplication_risk >= 0.8:
        flags.append("template_copy")
    return flags


class IngestionPipeline:
    def __init__(self, config: Config):
        self.config = config
        hamming = config.get("dedup", "simhash", "hamming_threshold", default=3)
        jaccard = config.get("dedup", "minhash", "jaccard_threshold", default=0.82)
        num_perm = config.get("dedup", "minhash", "num_perm", default=128)
        self.detector = NearDuplicateDetector(hamming, jaccard, num_perm)

    def run(self, raw_jobs: list[dict]) -> list[Job]:
        """批量治理：先建 Job 对象，再做近重复检测，最后打分打标签。"""
        jobs: list[Job] = []
        for raw in raw_jobs:
            jobs.append(Job(
                job_id=raw["job_id"],
                title=raw.get("title", ""),
                description=raw.get("description", ""),
                industry=raw.get("industry", "人工智能"),
                level=raw.get("level", "中级"),
                tech_stack=raw.get("tech_stack", []),
                source=_parse_source(raw),
            ))

        # 近重复检测
        docs = {j.job_id: j.title + "\n" + j.description for j in jobs}
        dup = self.detector.detect(docs)

        for j in jobs:
            d = dup[j.job_id]
            j.duplicate_group = d["duplicate_group"]
            j.duplication_risk = d["duplication_risk"]

            skills = extract_skills_from_text(j.description)
            j.skills_density = round(len(skills) / max(1, len(j.description) / 100), 3)
            # 稀有技能：出现频率低于全库均值，这里用占位——后续在全库统计
            j.quality_flags = detect_quality_flags(j, len(skills), 0)

        # 技能通胀：全库技能频率
        from collections import Counter
        freq = Counter()
        for j in jobs:
            for s in extract_skills_from_text(j.description):
                freq[s] += 1
        total = max(1, sum(freq.values()))
        avg = total / max(1, len(freq))
        for j in jobs:
            skills = extract_skills_from_text(j.description)
            rare = sum(1 for s in skills if freq[s] <= max(1, avg * 0.3))
            j.rare_skill_ratio = round(rare / max(1, len(skills)), 3)
            j.quality_flags = detect_quality_flags(j, len(skills), rare)

        return jobs

    def score_job(self, job: Job, source_count: int, extraction_confidence: float = 0.85) -> dict:
        """对单条 Job 计算可信度分项。"""
        comp = compute_trust_score(
            source_type=job.source.source_type,
            published_at=job.source.published_at,
            source_count=source_count,
            extraction_confidence=extraction_confidence,
            duplication_risk=job.duplication_risk,
            has_evidence=bool(job.description),
            is_verified=False,
            config=self.config,
        )
        comp["verdict"] = trust_verdict(comp["trust_score"], self.config)
        return comp
