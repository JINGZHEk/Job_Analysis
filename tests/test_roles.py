"""新岗位发现与岗位更新单元测试。"""
from app.config import load_config
from app.roles import diff_role_skills, discover_roles


def _job(job_id, title, desc, src="招聘平台"):
    return {"job_id": job_id, "title": title, "description": desc,
            "industry": "人工智能", "source": {"source_type": src, "published_at": "2026-08-01"}}


def test_discover_new_role():
    jobs = [
        _job("1", "大模型应用开发工程师", "岗位职责：构建 Agent 工作流。任职要求：熟练 Python、LLM、RAG"),
        _job("2", "大模型应用开发工程师", "岗位职责：集成 RAG。任职要求：熟练 Python、LLM、RAG"),
        _job("3", "大模型应用开发工程师", "岗位职责：优化 Prompt。任职要求：熟练 Python、LLM、Agent"),
    ]
    config = load_config()
    roles = discover_roles(jobs, ["人工智能算法工程师"], config, min_cluster_size=3)
    assert len(roles) == 1
    assert roles[0].name == "大模型应用开发工程师"
    assert roles[0].is_new


def test_discover_excludes_known():
    jobs = [_job("1", "Java 开发工程师", "任职要求：熟练 Java、SQL、Linux"),
            _job("2", "Java 开发工程师", "任职要求：熟练 Java、SQL、Linux"),
            _job("3", "Java 开发工程师", "任职要求：熟练 Java、SQL、Linux")]
    config = load_config()
    roles = discover_roles(jobs, ["Java 开发工程师"], config, min_cluster_size=3)
    assert len(roles) == 0


def test_diff_role_skills():
    old = [{"skill": "Python", "is_required": True}, {"skill": "Spark", "is_required": True}]
    new = [{"skill": "Python", "is_required": True}, {"skill": "Flink", "is_required": True}]
    diff = diff_role_skills("X", old, new)
    assert diff["added"][0]["skill"] == "Flink"
    assert diff["removed"][0]["skill"] == "Spark"
