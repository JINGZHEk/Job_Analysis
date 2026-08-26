"""简历解析与匹配单元测试。"""
from app.config import load_config
from app.resume_match import build_learning_path, diagnose_match, parse_resume


def test_parse_resume_skills():
    resume = parse_resume("技能：Python、PyTorch、SQL\n工作年限：3 年\n项目经验：负责 Spark 数据处理")
    names = {m.name for m in resume.skills}
    assert "Python" in names
    assert "SQL" in names


def test_parse_resume_years():
    resume = parse_resume("工作年限：5 年经验")
    assert resume.years_experience == 5.0


def test_diagnose_match_full():
    config = load_config()
    resume = parse_resume("技能：Python、PyTorch、Deep Learning、Machine Learning、Linux")
    req = [{"skill": "Python", "is_required": True}, {"skill": "PyTorch", "is_required": True},
           {"skill": "Deep Learning", "is_required": True}]
    match = diagnose_match(resume, req, [], "人工智能算法工程师", config)
    assert match.hard_gate_pass
    assert match.total_score > 0.6


def test_diagnose_match_gap():
    config = load_config()
    resume = parse_resume("技能：Java、SQL")
    req = [{"skill": "Python", "is_required": True}, {"skill": "PyTorch", "is_required": True},
           {"skill": "Deep Learning", "is_required": True}]
    match = diagnose_match(resume, req, [], "人工智能算法工程师", config)
    assert not match.hard_gate_pass
    assert "Python" in match.missing_skills


def test_learning_path_order():
    path = build_learning_path(["LLM"], set())
    skills = [s.skill for s in path]
    # Python 应排在 LLM 之前（先修关系）
    assert skills.index("Python") < skills.index("LLM")
