"""可信度评分单元测试。"""
from app.config import load_config
from app.trust import (
    compute_trust_score,
    cross_source_agreement,
    freshness,
    hallucination_penalty,
    source_authority,
    trust_verdict,
)


def test_source_authority():
    config = load_config()
    assert source_authority("企业官网", config) > source_authority("简历", config)


def test_cross_source_agreement():
    assert cross_source_agreement(0) == 0.0
    assert cross_source_agreement(3) > cross_source_agreement(1)


def test_freshness_decays():
    config = load_config()
    recent = freshness("2026-08-01", config)
    old = freshness("2020-01-01", config)
    assert recent > old


def test_hallucination_penalty():
    assert hallucination_penalty(False, False) == 1.0
    assert hallucination_penalty(True, True) == 0.0


def test_trust_score_range():
    config = load_config()
    comp = compute_trust_score(
        source_type="企业官网", published_at="2026-08-01", source_count=3,
        extraction_confidence=0.9, duplication_risk=0.0,
        has_evidence=True, is_verified=True, config=config,
    )
    assert 0.0 <= comp["trust_score"] <= 1.0


def test_trust_verdict():
    config = load_config()
    assert trust_verdict(0.9, config) == "publish"
    assert trust_verdict(0.5, config) == "review"
    assert trust_verdict(0.1, config) == "reject"
