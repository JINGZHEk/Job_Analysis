"""简历解析、人岗匹配诊断、学习路径规划（FR-07/08/09）。"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from .config import Config
from .models import LearningPathStep, MatchResult, Resume, SkillMention
from .skills import category_of, extract_skills_from_text

# 技能先修 DAG：key 为技能，value 为前置技能
PREREQUISITES: dict[str, list[str]] = {
    "Deep Learning": ["Machine Learning", "Python"],
    "Machine Learning": ["Python"],
    "NLP": ["Machine Learning", "Python"],
    "Computer Vision": ["Deep Learning", "Python"],
    "LLM": ["NLP", "Deep Learning", "Python"],
    "RAG": ["LLM", "Embedding", "Python"],
    "Fine-tuning": ["LLM", "PyTorch"],
    "Transformer": ["Deep Learning"],
    "PyTorch": ["Python"],
    "TensorFlow": ["Python"],
    "Spark": ["SQL", "Python"],
    "Flink": ["SQL", "Java"],
    "Knowledge Graph": ["NLP", "Python"],
    "Recommendation System": ["Machine Learning", "Python"],
    "Distributed Training": ["PyTorch", "Linux"],
    "MLOps": ["Docker", "CI/CD", "Python"],
    "Vector Database": ["Embedding"],
    "Embedding": ["Machine Learning", "Python"],
    "Model Serving": ["Docker", "Python"],
    "Data Warehouse": ["SQL"],
    "ETL": ["SQL"],
    "强化学习": ["Deep Learning", "Python"],
    "多模态": ["Deep Learning", "Transformer"],
    "Agent": ["LLM", "Prompt Engineering"],
    "TensorRT": ["PyTorch", "Linux"],
}

# 技能 -> 推荐课程/认证资源
RESOURCES: dict[str, list[str]] = {
    "Python": ["Python 官方教程", "Coursera: Python for Everybody"],
    "Machine Learning": ["吴恩达《Machine Learning》", "西瓜书"],
    "Deep Learning": ["DeepLearning.AI 专项课程", "花书"],
    "NLP": ["Stanford CS224N", "Speech and Language Processing"],
    "LLM": ["Hugging Face NLP Course", "动手学大模型"],
    "RAG": ["LangChain 官方文档 RAG 教程"],
    "Fine-tuning": ["Hugging Face PEFT/LoRA 文档"],
    "PyTorch": ["PyTorch 官方教程", "动手学深度学习"],
    "Spark": ["Spark 官方文档", "Databricks 认证"],
    "Docker": ["Docker 官方入门", "KodeKloud Docker 课程"],
    "Knowledge Graph": ["Neo4j 图数据建模", "知识图谱导论"],
    "MLOps": ["MLOps Zoomcamp", "AWS MLOps 白皮书"],
}

# 每个技能估算学习时长（小时）
EFFORT: dict[str, float] = {
    "Python": 80, "Machine Learning": 120, "Deep Learning": 150, "NLP": 120,
    "LLM": 80, "RAG": 40, "Fine-tuning": 60, "PyTorch": 100, "Spark": 80,
    "Docker": 40, "Knowledge Graph": 60, "MLOps": 60, "SQL": 40,
}


def parse_resume(text: str, resume_id: str = "", name: str = "") -> Resume:
    """从简历文本提取技能证据、年限、教育、证书。"""
    skills = extract_skills_from_text(text)
    mentions: list[SkillMention] = []
    for s in skills:
        loc = "技能栏"
        evidence = ""
        # 定位技能出现的上下文作为证据
        idx = text.lower().find(s.lower())
        if idx >= 0:
            evidence = text[max(0, idx - 20):idx + len(s) + 30].strip()
            # 判断在项目/证书段落
            if any(k in evidence for k in ("项目", "负责", "开发", "搭建")):
                loc = "项目"
            elif any(k in evidence for k in ("证书", "认证")):
                loc = "证书"
        mentions.append(SkillMention(
            skill_id=f"skill:{s}", name=s, location=loc, evidence=evidence
        ))

    years = 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:相关)?(?:工作)?经验", text)
    if m:
        years = float(m.group(1))

    education = "不限"
    for lvl in ["博士", "硕士", "本科", "大专"]:
        if lvl in text:
            education = lvl
            break

    certs = re.findall(r"(?:证书|认证)[：:、]?([^。；;\n]{2,20})", text)

    projects = re.findall(r"项目[：:、]?([^。；;\n]{4,50})", text)

    return Resume(
        resume_id=resume_id or "resume-1",
        raw_text=text,
        name=name,
        skills=mentions,
        projects=projects,
        years_experience=years,
        education=education,
        certs=certs,
    )


def _skill_level(mention: SkillMention) -> float:
    return 1.0


def diagnose_match(
    resume: Resume,
    required: list[dict],
    preferred: list[dict],
    target_role: str,
    config: Config,
) -> MatchResult:
    """多维人岗匹配：硬门槛 -> 技能/经验/项目证据/新鲜度/迁移能力。"""
    w = config.get("matching", "weights", default={})
    have = {m.name for m in resume.skills}
    req_names = {s["skill"] for s in required}
    pref_names = {s["skill"] for s in preferred}

    # 硬门槛：学历/年限可配置（此处以技能覆盖为准，示例：必备技能覆盖 >= 60% 视为过）
    covered = have & req_names
    hard_pass = len(covered) >= max(1, int(len(req_names) * 0.6)) if req_names else True

    # 技能匹配：核心信号 = 必备技能覆盖率
    coverage = len(covered) / len(req_names) if req_names else 1.0
    preferred_bonus = (len(have & pref_names) / len(pref_names)) if pref_names else 0.0
    skill_score = min(1.0, 0.85 * coverage + 0.15 * preferred_bonus)

    # 经验
    exp_score = min(1.0, resume.years_experience / 5.0) if resume.years_experience else 0.3

    # 项目证据
    proj_score = min(1.0, len(resume.projects) / 3.0) if resume.projects else 0.2

    # 技能新鲜度：简历中出现的前沿技能比例
    frontier = {"LLM", "RAG", "Fine-tuning", "Agent", "多模态", "Distributed Training", "MLOps"}
    freshness = len(have & frontier) / max(1, len(frontier))

    # 迁移能力：非目标岗位技能中可迁移的通用技能
    transferable = {"Python", "SQL", "Linux", "Git", "Docker", "Machine Learning"}
    transfer = len(have & transferable) / max(1, len(transferable))

    # 总分以「必备技能覆盖率」为主导，经验/项目/新鲜度/迁移能力作为校准项。
    # 校准目标：覆盖率 0.6（金标准匹配线）附近，总分跨越 0.5 决策阈值。
    aux = (exp_score + proj_score + freshness + transfer) / 4
    total = 0.70 * coverage + 0.15 * preferred_bonus + 0.15 * aux
    total = round(min(1.0, total), 4)

    missing = sorted(req_names - have)
    matched = sorted(covered)

    risk_items = []
    if not hard_pass:
        risk_items.append("必备技能覆盖不足 60%")
    if resume.years_experience < 2:
        risk_items.append("工作年限偏短")

    explanations = [
        f"必备技能 {len(covered)}/{len(req_names)} 项命中",
        f"加分技能 {len(have & pref_names)}/{len(pref_names)} 项命中",
        f"项目证据 {len(resume.projects)} 项",
        f"前沿技能覆盖 {freshness*100:.0f}%",
        f"可迁移通用技能 {len(have & transferable)}/{len(transferable)} 项",
    ]

    return MatchResult(
        resume_id=resume.resume_id,
        role_name=target_role,
        total_score=total,
        hard_gate_pass=hard_pass,
        dimensions={
            "skill_match": round(skill_score, 3),
            "experience": round(exp_score, 3),
            "project_evidence": round(proj_score, 3),
            "skill_freshness": round(freshness, 3),
            "transfer_ability": round(transfer, 3),
        },
        matched_skills=matched,
        missing_skills=missing,
        risk_items=risk_items,
        explanations=explanations,
    )


def build_learning_path(missing_skills: list[str], known_skills: set[str]) -> list[LearningPathStep]:
    """基于技能先修 DAG 生成带优先级的学习路径。"""
    # 计算每个缺失技能还需补的前置
    to_learn: set[str] = set(missing_skills)
    for s in missing_skills:
        for pre in PREREQUISITES.get(s, []):
            if pre not in known_skills:
                to_learn.add(pre)

    # 拓扑排序（DAG）
    indeg = {s: 0 for s in to_learn}
    adj = defaultdict(list)
    for s in to_learn:
        for pre in PREREQUISITES.get(s, []):
            if pre in to_learn and pre != s:
                adj[pre].append(s)
                indeg[s] += 1

    order: list[str] = []
    queue = [s for s in sorted(to_learn) if indeg[s] == 0]
    while queue:
        s = queue.pop(0)
        order.append(s)
        for nxt in adj[s]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    # 兜底：环或遗漏
    order += [s for s in sorted(to_learn) if s not in order]

    steps: list[LearningPathStep] = []
    for i, s in enumerate(order):
        prereq_of = adj[s]
        hours = EFFORT.get(s, 60.0)
        steps.append(LearningPathStep(
            step=i + 1,
            skill=s,
            prerequisite_of=prereq_of,
            resources=RESOURCES.get(s, ["官方文档/在线课程"]),
            estimated_hours=hours,
            completion_criteria=f"能独立完成 {s} 相关项目并写入简历",
        ))
    return steps
