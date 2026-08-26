"""端到端管线集成测试。"""
import json
from pathlib import Path

from app.pipeline import bootstrap


def test_bootstrap_end_to_end(tmp_path: Path):
    # 构造最小数据
    data = tmp_path / "data"
    data.mkdir()
    jds = [
        {"job_id": "1", "title": "人工智能算法工程师",
         "description": "岗位职责：负责深度学习。任职要求：熟练 Python、PyTorch、Deep Learning",
         "industry": "人工智能", "level": "中级",
         "source": {"source_type": "招聘平台", "published_at": "2026-08-01"},
         "gold_required_skills": ["Python", "PyTorch", "Deep Learning"],
         "gold_preferred_skills": []},
        {"job_id": "2", "title": "人工智能算法工程师",
         "description": "岗位职责：负责深度学习。任职要求：熟练 Python、PyTorch、Deep Learning",
         "industry": "人工智能", "level": "中级",
         "source": {"source_type": "企业官网", "published_at": "2026-08-01"},
         "gold_required_skills": ["Python", "PyTorch", "Deep Learning"],
         "gold_preferred_skills": []},
        {"job_id": "3", "title": "人工智能算法工程师",
         "description": "岗位职责：负责深度学习。任职要求：熟练 Python、PyTorch、Deep Learning",
         "industry": "人工智能", "level": "中级",
         "source": {"source_type": "技术社区", "published_at": "2026-08-01"},
         "gold_required_skills": ["Python", "PyTorch", "Deep Learning"],
         "gold_preferred_skills": []},
    ]
    (data / "jds.json").write_text(json.dumps(jds, ensure_ascii=False), encoding="utf-8")

    p = bootstrap(data)
    assert len(p._jobs) == 3
    assert p.graph.G.number_of_nodes() > 0
    pano = p.panorama()
    assert len(pano["nodes"]) > 0

    # 匹配
    res = p.parse_and_match("技能：Python、PyTorch、Deep Learning", "人工智能算法工程师")
    assert res["match"]["total_score"] > 0.6
