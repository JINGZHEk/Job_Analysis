"""数据治理单元测试。"""
from app.config import load_config
from app.ingest import IngestionPipeline


def test_ingestion_detects_duplicates():
    config = load_config()
    pipe = IngestionPipeline(config)
    raw = [
        {"job_id": "1", "title": "人工智能算法工程师",
         "description": "岗位职责：负责深度学习。任职要求：熟练 Python、PyTorch",
         "industry": "人工智能", "level": "中级",
         "source": {"source_type": "招聘平台", "published_at": "2026-08-01"}},
        {"job_id": "2", "title": "人工智能算法工程师",
         "description": "岗位职责：负责深度学习。任职要求：熟练 Python、PyTorch",
         "industry": "人工智能", "level": "中级",
         "source": {"source_type": "招聘平台", "published_at": "2026-08-01"}},
    ]
    jobs = pipe.run(raw)
    assert jobs[0].duplication_risk > 0.8


def test_ingestion_quality_flags():
    config = load_config()
    pipe = IngestionPipeline(config)
    raw = [{"job_id": "1", "title": "", "description": "短",
            "industry": "人工智能", "level": "中级",
            "source": {"source_type": "招聘平台", "published_at": "2026-08-01"}}]
    jobs = pipe.run(raw)
    assert "empty_title" in jobs[0].quality_flags
