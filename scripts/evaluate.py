"""一键评测：JD 解析、简历提取、匹配、重复识别、证据覆盖、幻觉率。

运行：python scripts/evaluate.py
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

from app.config import load_config
from app.evaluation import (
    evaluate_duplication,
    evaluate_jd_parsing,
    evaluate_matching,
    evaluate_resume_extraction,
    evidence_coverage,
    hallucination_rate,
)
from app.ingest import IngestionPipeline
from app.llm import build_extractor
from app.resume_match import build_learning_path, diagnose_match, parse_resume

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> None:
    config = load_config()
    jds = json.loads((DATA / "jds.json").read_text(encoding="utf-8"))
    resumes = json.loads((DATA / "resumes.json").read_text(encoding="utf-8"))
    gold_jd = json.loads((DATA / "gold_jd.json").read_text(encoding="utf-8"))
    gold_resume = json.loads((DATA / "gold_resume.json").read_text(encoding="utf-8"))
    gold_match = json.loads((DATA / "gold_match.json").read_text(encoding="utf-8"))

    extractor = build_extractor(config)

    # ---- JD 解析 ----
    pred_jd, gold_skills = [], []
    for g in gold_jd:
        raw = next(j for j in jds if j["job_id"] == g["job_id"])
        ex = extractor.extract_job(raw)
        pred_jd.append({"title": g["title"], "required_skills": ex["required_skills"]})
        gold_skills.append({"title": g["title"], "required_skills": g["required_skills"]})
    jd_metrics = evaluate_jd_parsing(pred_jd, gold_skills)

    # ---- 简历提取 ----
    pred_res, gold_res = [], []
    for r in resumes:
        ex = extractor.extract_resume(r["text"])
        pred_res.append([m["skill"] for m in ex["skills"]])
        gold_res.append(r["gold_skills"])
    resume_metrics = evaluate_resume_extraction(pred_res, gold_res)

    # ---- 人岗匹配（频率聚合岗位画像，与金标准口径一致）----
    from collections import Counter
    pred_scores, gold_labels = [], []
    role_req_map = {}
    for title in {g["title"] for g in gold_jd}:
        n = sum(1 for g in gold_jd if g["title"] == title) or 1
        c = Counter()
        for g in gold_jd:
            if g["title"] == title:
                for s in g["required_skills"]:
                    c[s] += 1
        role_req_map[title] = [{"skill": s, "is_required": True}
                               for s, cnt in c.items() if cnt / n >= 0.6]
    for gm in gold_match:
        r = next(x for x in resumes if x["resume_id"] == gm["resume_id"])
        resume = parse_resume(r["text"], r["resume_id"])
        req = role_req_map.get(gm["role"], [])
        match = diagnose_match(resume, req, [], gm["role"], config)
        pred_scores.append(match.total_score)
        gold_labels.append(gm["match"])
    match_metrics = evaluate_matching(pred_scores, gold_labels)

    # ---- 重复识别（MinHash 两两 Jaccard >= 阈值判定）----
    from app.dedup import MinHash, char_shingles
    gold_dup_file = DATA / "gold_duplicates.json"
    gold_pairs = ([tuple(p) for p in json.loads(gold_dup_file.read_text(encoding="utf-8"))]
                  if gold_dup_file.exists() else [])
    mh = MinHash(128)
    sigs = {j["job_id"]: mh.signature(char_shingles(j["title"] + "\n" + j["description"], 3)) for j in jds}
    ids = list(sigs.keys())
    pred_pairs = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            if mh.jaccard_estimate(sigs[ids[a]], sigs[ids[b]]) >= 0.82:
                pred_pairs.append((ids[a], ids[b]))
    dup_metrics = evaluate_duplication(pred_pairs, gold_pairs)

    # ---- 证据覆盖 / 幻觉率 ----
    claims = []
    for g in gold_jd:
        raw = next(j for j in jds if j["job_id"] == g["job_id"])
        ex = extractor.extract_job(raw)
        for s in ex["required_skills"]:
            span = next((e["span"] for e in ex.get("evidence", [])
                         if e.get("field") == "required_skills" and s in e.get("span", "")), "")
            claims.append({
                "evidence_span": span,
                "review_status": "published",
            })
    ev_coverage = evidence_coverage(claims)
    hallu_rate = hallucination_rate(claims)

    print("=" * 60)
    print("岗位能力图谱系统 —— 评测报告")
    print("=" * 60)
    print(f"测试规模：{len(jds)} 条 JD，{len(resumes)} 份简历，{len(gold_match)} 条匹配样本")
    print()
    print(f"[JD 解析]   Precision={jd_metrics['precision']:.3f}  "
          f"Recall={jd_metrics['recall']:.3f}  F1={jd_metrics['f1']:.3f}")
    print(f"[简历提取]   Precision={resume_metrics['precision']:.3f}  "
          f"Recall={resume_metrics['recall']:.3f}  F1={resume_metrics['f1']:.3f}")
    print(f"[人岗匹配]   准确率={match_metrics['accuracy']:.3f}")
    print(f"[重复识别]   Precision={dup_metrics['precision']:.3f}  "
          f"Recall={dup_metrics['recall']:.3f}  F1={dup_metrics['f1']:.3f}")
    print(f"[证据覆盖]   {ev_coverage:.3f}")
    print(f"[幻觉率]     {hallu_rate:.3f}")
    print()

    report = {
        "jd_parsing": jd_metrics,
        "resume_extraction": resume_metrics,
        "matching": match_metrics,
        "duplication": dup_metrics,
        "evidence_coverage": ev_coverage,
        "hallucination_rate": hallu_rate,
    }
    out = DATA / "evaluation_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已保存到 {out}")


if __name__ == "__main__":
    main()
