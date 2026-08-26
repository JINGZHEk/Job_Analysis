"""评测指标单元测试。"""
from app.evaluation import (
    evaluate_duplication,
    evaluate_jd_parsing,
    evaluate_matching,
    evaluate_resume_extraction,
    hallucination_rate,
)


def test_jd_parsing_perfect():
    pred = [{"required_skills": ["Python", "PyTorch"]}]
    gold = [{"required_skills": ["Python", "PyTorch"]}]
    m = evaluate_jd_parsing(pred, gold)
    assert m["f1"] == 1.0


def test_jd_parsing_imperfect():
    pred = [{"required_skills": ["Python", "Java"]}]
    gold = [{"required_skills": ["Python", "PyTorch"]}]
    m = evaluate_jd_parsing(pred, gold)
    assert m["precision"] == 0.5


def test_resume_extraction():
    pred = [["Python", "SQL"], ["Java"]]
    gold = [["Python", "SQL"], ["Java"]]
    m = evaluate_resume_extraction(pred, gold)
    assert m["f1"] == 1.0


def test_matching_accuracy():
    m = evaluate_matching([0.8, 0.3], [1, 0])
    assert m["accuracy"] == 1.0


def test_duplication():
    m = evaluate_duplication([("a", "b")], [("a", "b")])
    assert m["f1"] == 1.0


def test_hallucination():
    claims = [{"evidence_span": "", "review_status": "published"},
              {"evidence_span": "有证据", "review_status": "published"}]
    assert hallucination_rate(claims) == 0.5
