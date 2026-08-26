"""技能标准化单元测试。"""
from app.skills import category_of, extract_skills_from_text, normalize_skill


def test_normalize_alias():
    assert normalize_skill("python") == "Python"
    assert normalize_skill("大模型") == "LLM"
    assert normalize_skill("pytorch") == "PyTorch"


def test_normalize_unknown():
    assert normalize_skill("不存在的技能xyz") is None


def test_extract_skills():
    text = "熟练使用 Python、PyTorch 进行深度学习模型开发，熟悉大模型与 RAG"
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "PyTorch" in skills
    assert "Deep Learning" in skills
    assert "LLM" in skills
    assert "RAG" in skills


def test_category():
    assert category_of("Python") == "编程语言"
    assert category_of("PyTorch") == "深度学习框架"
