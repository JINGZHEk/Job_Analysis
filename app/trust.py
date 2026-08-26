"""可信度评分：Trust(e) = w_s*SourceAuthority + w_t*Freshness + w_c*CrossSourceAgreement
                          + w_q*ExtractionQuality - w_d*DuplicationRisk - w_h*HallucinationRisk"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from .config import Config


def _days_old(published_at: str, now: Optional[datetime] = None) -> Optional[float]:
    if not published_at:
        return None
    now = now or datetime.now()
    try:
        pub = datetime.fromisoformat(published_at)
    except ValueError:
        return None
    return max(0.0, (now - pub).total_seconds() / 86400.0)


def source_authority(source_type: str, config: Config) -> float:
    table = config.get("sources", "authority", default={})
    return float(table.get(source_type, 0.5))


def freshness(published_at: str, config: Config, now: Optional[datetime] = None) -> float:
    """时间半衰期衰减。"""
    days = _days_old(published_at, now)
    if days is None:
        return 0.5  # 未知时间，中性
    half_life = float(config.get("trust", "freshness_half_life_days", default=365))
    return 2.0 ** (-days / half_life)


def cross_source_agreement(source_count: int) -> float:
    """跨源一致性：支持来源越多越可信，饱和在 3 个来源。"""
    if source_count <= 0:
        return 0.0
    return 1.0 - 0.5 ** source_count


def extraction_quality(confidence: float) -> float:
    return max(0.0, min(1.0, float(confidence)))


def duplication_penalty(duplication_risk: float) -> float:
    return max(0.0, min(1.0, float(duplication_risk)))


def hallucination_penalty(has_evidence: bool, is_verified: bool) -> float:
    """无证据支撑且未验证的结论，幻觉风险高。"""
    if has_evidence and is_verified:
        return 0.0
    if has_evidence:
        return 0.3
    if is_verified:
        return 0.5
    return 1.0


def compute_trust_score(
    *,
    source_type: str,
    published_at: str,
    source_count: int,
    extraction_confidence: float,
    duplication_risk: float,
    has_evidence: bool,
    is_verified: bool,
    config: Config,
    now: Optional[datetime] = None,
) -> dict[str, float]:
    w = config.get("trust", "weights", default={})
    comp = {
        "source_authority": source_authority(source_type, config),
        "freshness": freshness(published_at, config, now),
        "cross_source_agreement": cross_source_agreement(source_count),
        "extraction_quality": extraction_quality(extraction_confidence),
        "duplication_risk": duplication_penalty(duplication_risk),
        "hallucination_risk": hallucination_penalty(has_evidence, is_verified),
    }
    score = (
        w.get("source_authority", 0.25) * comp["source_authority"]
        + w.get("freshness", 0.20) * comp["freshness"]
        + w.get("cross_source_agreement", 0.20) * comp["cross_source_agreement"]
        + w.get("extraction_quality", 0.20) * comp["extraction_quality"]
        - w.get("duplication_risk", 0.075) * comp["duplication_risk"]
        - w.get("hallucination_risk", 0.075) * comp["hallucination_risk"]
    )
    score = max(0.0, min(1.0, score))
    comp["trust_score"] = round(score, 4)
    return comp


def trust_verdict(trust_score: float, config: Config) -> str:
    """依据阈值给出结论：publish / review / reject。"""
    publish = config.get("trust", "thresholds", "publish", default=0.75)
    reject = config.get("trust", "thresholds", "reject", default=0.45)
    if trust_score >= publish:
        return "publish"
    if trust_score >= reject:
        return "review"
    return "reject"
