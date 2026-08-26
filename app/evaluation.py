"""评测体系与指标计算（FR-11 / 测试方案）。

指标：JD 字段准确率、简历技能 F1、匹配准确率、证据覆盖率、
幻觉率、重复识别 F1、新岗位发现 Precision@K。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


@dataclass
class EvaluationReport:
    metrics: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    error_samples: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"metrics": self.metrics, "details": self.details,
                "error_samples": self.error_samples}


def evaluate_jd_parsing(predictions: list[dict], gold: list[dict]) -> dict:
    """JD 字段级准确率：以技能字段为主（Precision/Recall/F1）。"""
    tp = fp = fn = 0
    errors = []
    for pred, gt in zip(predictions, gold):
        p_skills = set(pred.get("required_skills", []))
        g_skills = set(gt.get("required_skills", []))
        tp += len(p_skills & g_skills)
        fp += len(p_skills - g_skills)
        fn += len(g_skills - p_skills)
        if p_skills != g_skills:
            errors.append({
                "job": gt.get("title", ""),
                "pred": sorted(p_skills),
                "gold": sorted(g_skills),
            })
    return {**_prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn, "errors": errors[:10]}


def evaluate_resume_extraction(predictions: list[list[str]], gold: list[list[str]]) -> dict:
    tp = fp = fn = 0
    errors = []
    for i, (p, g) in enumerate(zip(predictions, gold)):
        ps, gs = set(p), set(g)
        tp += len(ps & gs)
        fp += len(ps - gs)
        fn += len(gs - ps)
        if ps != gs:
            errors.append({"resume": i, "pred": sorted(ps), "gold": sorted(gs)})
    return {**_prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn, "errors": errors[:10]}


def evaluate_matching(pred_scores: list[float], gold_labels: list[float], threshold: float = 0.5) -> dict:
    """匹配准确率：与专家金标准分档一致（>=threshold 视为匹配）。"""
    correct = 0
    errors = []
    for i, (p, g) in enumerate(zip(pred_scores, gold_labels)):
        pred_label = 1 if p >= threshold else 0
        gold_label = 1 if g >= threshold else 0
        if pred_label == gold_label:
            correct += 1
        else:
            errors.append({"sample": i, "pred": p, "gold": g})
    acc = correct / len(pred_scores) if pred_scores else 0.0
    return {"accuracy": round(acc, 4), "errors": errors[:10]}


def evaluate_duplication(pred_pairs: list[tuple[str, str]], gold_pairs: list[tuple[str, str]]) -> dict:
    """重复识别：以文档对为单位。pred_pairs 为预测重复对，gold_pairs 为真实重复对。"""
    pred_set = {tuple(sorted(p)) for p in pred_pairs}
    gold_set = {tuple(sorted(p)) for p in gold_pairs}
    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    return {**_prf(tp, fp, fn)}


def evidence_coverage(claims: list[dict]) -> float:
    """有证据 span 的关键结论占比。"""
    if not claims:
        return 0.0
    with_ev = sum(1 for c in claims if c.get("evidence_span"))
    return round(with_ev / len(claims), 4)


def hallucination_rate(claims: list[dict]) -> float:
    """无证据支撑却发布的结论占比。"""
    if not claims:
        return 0.0
    hallu = sum(1 for c in claims
                if not c.get("evidence_span") and c.get("review_status") == "published")
    return round(hallu / len(claims), 4)
