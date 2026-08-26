"""生成模拟数据：多源 JD（含抄袭/时滞/通胀特征）、简历、金标准标注。

运行：python scripts/generate_data.py
产物（写入 data/）：
- jds.json        100+ 条岗位 JD
- resumes.json    简历
- gold_jd.json    JD 技能金标准（用于评测）
- gold_resume.json 简历技能金标准
- gold_match.json 匹配金标准
- gold_duplicates.json 真实抄袭对（用于重复识别评测）
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

random.seed(42)

# ---- 岗位模板：required=核心必备（每家公司都有），skill_pool=可选技能池（各公司不同）----
ROLES = {
    "人工智能算法工程师": {
        "duties": ["负责深度学习模型的设计与训练", "参与算法落地与性能优化",
                   "搭建模型推理服务", "跟进前沿论文并复现"],
        "required": ["Python", "Deep Learning", "Machine Learning"],
        "preferred": ["PyTorch", "Linux"],
        "skill_pool": ["PyTorch", "TensorFlow", "Linux", "NLP", "Computer Vision", "Model Serving", "Distributed Training", "ONNX", "TensorRT", "MLOps", "A/B Testing", "Feature Engineering", "Docker", "强化学习"],
        "industry": "人工智能", "level": "中级",
    },
    "大数据开发工程师": {
        "duties": ["负责数据仓库建模与开发", "维护 ETL 数据管道",
                   "优化 Spark 作业性能", "建设数据质量监控体系"],
        "required": ["SQL", "Spark", "Python"],
        "preferred": ["Hadoop", "Hive"],
        "skill_pool": ["Hadoop", "Hive", "Flink", "Kafka", "Data Warehouse", "ETL", "AWS", "CI/CD", "Docker", "Kubernetes", "Go", "Data Warehouse", "OLAP", "ClickHouse"],
        "industry": "大数据", "level": "中级",
    },
    "Java 开发工程师": {
        "duties": ["负责后端服务设计开发", "参与系统架构优化",
                   "编写单元测试", "对接数据库与消息中间件"],
        "required": ["Java", "SQL", "Linux"],
        "preferred": ["Git", "Kafka"],
        "skill_pool": ["Git", "Kafka", "Docker", "CI/CD", "Kubernetes", "Go", "Data Warehouse", "Model Serving", "AWS", "Nginx", "Redis", "微服务", "Spring"],
        "industry": "智能系统", "level": "中级",
    },
    "NLP 算法工程师": {
        "duties": ["负责自然语言处理模型研发", "构建文本分类/信息抽取系统",
                   "优化大模型微调与推理", "落地 RAG 应用"],
        "required": ["Python", "NLP", "Deep Learning"],
        "preferred": ["PyTorch", "Machine Learning"],
        "skill_pool": ["PyTorch", "Machine Learning", "LLM", "RAG", "Fine-tuning", "Transformer", "Embedding", "Vector Database", "Prompt Engineering", "Agent", "多模态", "语音识别", "TensorFlow", "Linux"],
        "industry": "人工智能", "level": "高级",
    },
    "大模型算法工程师": {
        "duties": ["负责大语言模型微调与对齐", "构建 RAG 与 Agent 应用",
                   "优化推理性能与成本", "搭建评测体系"],
        "required": ["Python", "LLM", "PyTorch"],
        "preferred": ["Deep Learning", "Transformer"],
        "skill_pool": ["Deep Learning", "Transformer", "RAG", "Fine-tuning", "Agent", "Prompt Engineering", "Distributed Training", "多模态", "Embedding", "Vector Database", "Linux", "TensorRT", "MLOps", "强化学习"],
        "industry": "人工智能", "level": "高级",
    },
    "CV 算法工程师": {
        "duties": ["负责计算机视觉算法研发", "训练目标检测/图像分割模型",
                   "优化模型精度与推理速度", "部署模型到边缘设备"],
        "required": ["Python", "Computer Vision", "Deep Learning"],
        "preferred": ["PyTorch", "TensorFlow"],
        "skill_pool": ["PyTorch", "TensorFlow", "TensorRT", "ONNX", "Embedded Systems", "Model Serving", "Linux", "C++", "多模态", "Docker", "强化学习", "NLP", "Edge Computing"],
        "industry": "人工智能", "level": "中级",
    },
    "推荐算法工程师": {
        "duties": ["负责推荐系统召回与排序", "优化特征工程与模型效果",
                   "设计 A/B 实验", "建设实时推荐链路"],
        "required": ["Python", "Recommendation System", "Machine Learning"],
        "preferred": ["Spark", "SQL"],
        "skill_pool": ["Spark", "SQL", "Deep Learning", "Feature Engineering", "A/B Testing", "Flink", "Kafka", "Data Warehouse", "PyTorch", "LLM", "Embedding", "Hive"],
        "industry": "大数据", "level": "高级",
    },
    "知识图谱工程师": {
        "duties": ["负责知识图谱构建与推理", "设计本体与实体对齐",
                   "结合大模型做知识抽取", "支撑智能问答应用"],
        "required": ["Python", "Knowledge Graph", "NLP"],
        "preferred": ["SQL", "LLM"],
        "skill_pool": ["SQL", "LLM", "RAG", "Embedding", "Vector Database", "Machine Learning", "Deep Learning", "Prompt Engineering", "PyTorch", "Docker", "Java", "Neo4j"],
        "industry": "人工智能", "level": "中级",
    },
    "物联网嵌入式工程师": {
        "duties": ["负责嵌入式固件开发", "设计设备通信与数据采集",
                   "优化低功耗与实时性", "对接云平台"],
        "required": ["Embedded Systems", "C++", "Linux"],
        "preferred": ["MQTT", "IoT"],
        "skill_pool": ["MQTT", "IoT", "Edge Computing", "Python", "ROS", "TensorRT", "ONNX", "Computer Vision", "Docker", "Kubernetes", "Deep Learning", "C++"],
        "industry": "物联网", "level": "中级",
    },
    "边缘计算工程师": {
        "duties": ["负责边缘计算平台研发", "部署模型到边缘设备",
                   "优化边缘推理性能", "建设设备管理平台"],
        "required": ["Edge Computing", "IoT", "Linux"],
        "preferred": ["Python", "Docker"],
        "skill_pool": ["Python", "Docker", "TensorRT", "ONNX", "Kubernetes", "MQTT", "C++", "Embedded Systems", "ROS", "IoT", "Computer Vision", "AWS"],
        "industry": "物联网", "level": "中级",
    },
    "机器人算法工程师": {
        "duties": ["负责机器人感知与规划算法", "开发 SLAM 与导航",
                   "集成传感器与执行器", "优化实时控制性能"],
        "required": ["ROS", "C++", "Linux"],
        "preferred": ["Python", "Computer Vision"],
        "skill_pool": ["Python", "Computer Vision", "Deep Learning", "强化学习", "Embedded Systems", "PyTorch", "IoT", "Edge Computing", "TensorRT", "ONNX", "MQTT", "SLAM"],
        "industry": "智能系统", "level": "高级",
    },
    "MLOps 工程师": {
        "duties": ["负责模型训练与部署流水线", "搭建 CI/CD 与监控",
                   "优化模型服务性能", "管理实验与版本"],
        "required": ["MLOps", "Docker", "Python"],
        "preferred": ["Kubernetes", "CI/CD"],
        "skill_pool": ["Kubernetes", "CI/CD", "Model Serving", "Distributed Training", "AWS", "Linux", "ONNX", "TensorRT", "PyTorch", "Deep Learning", "Spark", "SQL", "MLOps"],
        "industry": "智能系统", "level": "高级",
    },
}

# 新兴岗位（用于新岗位发现测试）：尚未标准化
EMERGING = {
    "大模型应用开发工程师": {
        "duties": ["负责大模型应用层开发", "构建 Agent 工作流", "集成 RAG 与工具调用", "优化 Prompt 与评测"],
        "required": ["Python", "LLM", "RAG"],
        "preferred": ["Agent", "Prompt Engineering"],
        "skill_pool": ["Agent", "Prompt Engineering", "Fine-tuning", "LangChain", "Vector Database", "Embedding", "多模态", "Deep Learning", "PyTorch", "Docker", "Kubernetes", "MLOps"],
        "industry": "人工智能", "level": "中级",
    },
    "AI Agent 工程师": {
        "duties": ["负责智能体架构设计", "开发多智能体协作", "集成工具调用与记忆", "构建评测与安全机制"],
        "required": ["Python", "Agent", "LLM"],
        "preferred": ["Prompt Engineering", "RAG"],
        "skill_pool": ["Prompt Engineering", "RAG", "Fine-tuning", "多模态", "LangChain", "Vector Database", "Embedding", "Deep Learning", "PyTorch", "Docker", "Knowledge Graph", "Transformer"],
        "industry": "人工智能", "level": "中级",
    },
}

SOURCE_TYPES = ["招聘平台", "企业官网", "技术社区", "课程与认证", "行业报告"]
PUBLISHERS = ["某科技公司", "某互联网公司", "某AI实验室", "某大数据公司", "某智能制造企业", "某物联网公司"]

DUTY_PARAPHRASES = {
    "负责": ["负责", "主导", "承担"], "参与": ["参与", "协助", "配合"],
    "搭建": ["搭建", "构建", "建设"], "优化": ["优化", "改进", "提升"],
    "开发": ["开发", "研发", "实现"], "设计": ["设计", "规划", "制定"],
    "建设": ["建设", "搭建", "构建"], "维护": ["维护", "保障", "支撑"],
}
EXTRA_DUTIES = [
    "编写技术文档与设计评审", "参与需求分析与技术选型", "与产品、测试团队协作交付",
    "负责线上问题排查与修复", "沉淀技术方案与最佳实践", "指导初级工程师成长",
]
SKILL_VERBS = ["熟练使用", "精通", "掌握", "熟悉", "深入理解"]


def _vary_duties(duties: list[str], seed: int) -> list[str]:
    rng = random.Random(seed)
    out = []
    for d in duties:
        s = d
        for k, options in DUTY_PARAPHRASES.items():
            if k in s and rng.random() < 0.8:
                s = s.replace(k, rng.choice(options), 1)
        out.append(s)
    if rng.random() < 0.6:
        out.append(rng.choice(EXTRA_DUTIES))
    if rng.random() < 0.3 and len(out) > 2:
        out.pop(rng.randrange(len(out)))
    rng.shuffle(out)
    return out


def _build_jd_text(template: dict, required: list[str], preferred: list[str], seed: int) -> str:
    duties = _vary_duties(template["duties"][:], seed)
    rng = random.Random(seed + 999)
    skills = required[:]
    rng.shuffle(skills)
    line1 = "1. " + rng.choice(SKILL_VERBS) + " " + "、".join(skills)
    desc_lines = ["岗位职责："] + [f"·{d}" for d in duties]
    desc_lines.append("任职要求：")
    desc_lines.append(line1)
    if preferred:
        desc_lines.append("2. 加分项：熟悉 " + "、".join(preferred) + " 者优先")
    desc_lines.append("3. 计算机相关专业本科及以上学历，3 年以上工作经验")
    return "\n".join(desc_lines)


def _sample_skills(template: dict, seed: int) -> tuple[list[str], list[str]]:
    """从岗位技能池中为「这家公司」采样技能集（同岗位不同公司有差异）。"""
    rng = random.Random(seed + 555)
    pool = template["skill_pool"][:]
    rng.shuffle(pool)
    # 必备 = 核心 + 从池子额外抽 2 个（池子大，保证核心与可选分离）
    extra_n = 2
    required = template["required"][:] + pool[:extra_n]
    # 加分 = 模板偏好 + 池子剩余抽 1~2 个
    preferred = template["preferred"][:]
    rest = [s for s in pool[extra_n:] if s not in preferred]
    preferred += rest[:rng.randint(1, 2)]
    # 去重保序
    seen = set()
    required = [s for s in required if not (s in seen or seen.add(s))]
    seen2 = set(required)
    preferred = [s for s in preferred if s not in seen2]
    return required, preferred


def _make_job(role_key: str, template: dict, job_id: str, published_at: str,
              source_type: str, seed: int = 0) -> dict:
    required, preferred = _sample_skills(template, seed)
    description = _build_jd_text(template, required, preferred, seed)
    return {
        "job_id": job_id,
        "title": role_key,
        "description": description,
        "industry": template["industry"],
        "level": template["level"],
        "tech_stack": required[:4],
        "source": {
            "source_type": source_type,
            "url": f"https://example.com/job/{job_id}",
            "publisher": random.choice(PUBLISHERS),
            "published_at": published_at,
            "collected_at": datetime.now().isoformat(),
            "language": "zh",
        },
        "gold_required_skills": required,
        "gold_preferred_skills": preferred,
    }


def generate_jds(n: int = 110) -> tuple[list[dict], list[list[str]]]:
    jds: list[dict] = []
    duplicate_pairs: list[list[str]] = []
    now = datetime.now()
    seed_counter = 0

    # 基础岗位（每个岗位多公司、多时间、多来源）
    while len(jds) < n - 20:
        for role_key, template in ROLES.items():
            if len(jds) >= n - 20:
                break
            age_days = random.choice([15, 45, 90, 200, 400])
            published = (now - timedelta(days=age_days)).isoformat()
            src = random.choice(SOURCE_TYPES)
            jds.append(_make_job(role_key, template, f"jd-{len(jds):04d}", published, src, seed_counter))
            seed_counter += 1

    # 新兴岗位：多个公司出现（跨源一致性）
    for em_key, template in EMERGING.items():
        for k in range(4):
            published = (now - timedelta(days=random.choice([10, 20, 35]))).isoformat()
            src = SOURCE_TYPES[k % len(SOURCE_TYPES)]
            jds.append(_make_job(em_key, template, f"jd-{len(jds):04d}", published, src, seed_counter))
            seed_counter += 1

    # 注入抄袭：取前 12 条做近重复变体（几乎完全复制，仅改来源与个别措辞）
    for base in jds[:12]:
        clone = json.loads(json.dumps(base))
        clone["job_id"] = f"jd-{len(jds):04d}"
        # 抄袭特征：仅替换个别词，文本几乎不变
        clone["description"] = (clone["description"]
                                .replace("岗位职责", "工作内容", 1)
                                .replace("任职要求", "职位要求", 1))
        clone["source"] = dict(clone["source"])
        clone["source"]["source_type"] = "招聘平台"
        clone["source"]["publisher"] = "某外包公司"
        clone["source"]["url"] = f"https://example.com/job/{clone['job_id']}"
        duplicate_pairs.append([base["job_id"], clone["job_id"]])
        jds.append(clone)

    # 注入通胀：某些 JD 堆砌大量技能
    for base in jds[20:30]:
        base["description"] += "\n4. 熟悉 Kubernetes、Docker、AWS、MLOps、Data Warehouse、TensorRT、ONNX 者优先"
        for s in ["Kubernetes", "Docker", "AWS", "MLOps"]:
            if s not in base["gold_preferred_skills"]:
                base["gold_preferred_skills"].append(s)

    return jds, duplicate_pairs


def generate_resumes(n: int = 20) -> list[dict]:
    profiles = [
        {"skills": ["Python", "PyTorch", "Deep Learning", "Machine Learning", "NLP", "LLM", "RAG"],
         "years": 4, "text": "3 年 AI 算法经验，负责大模型微调与 RAG 应用，参与 NLP 项目，熟练 PyTorch"},
        {"skills": ["Java", "SQL", "Linux", "Git", "Kafka", "Docker"],
         "years": 3, "text": "Java 后端开发 3 年，负责分布式系统，熟悉 Kafka 与 Docker"},
        {"skills": ["Python", "SQL", "Spark", "Hadoop", "Hive"],
         "years": 2, "text": "大数据开发 2 年，负责 Spark 离线数仓，熟练 Hive SQL"},
        {"skills": ["Python", "PyTorch", "Computer Vision", "Deep Learning"],
         "years": 2, "text": "CV 算法工程师，负责目标检测，熟练 PyTorch"},
        {"skills": ["C++", "Linux", "Embedded Systems", "MQTT"],
         "years": 3, "text": "嵌入式开发 3 年，负责 STM32 固件与 MQTT 通信"},
        {"skills": ["Python", "Machine Learning", "Recommendation System", "SQL", "Spark"],
         "years": 5, "text": "推荐系统 5 年，负责召回排序，熟悉 Spark"},
        {"skills": ["Python", "LLM", "Agent", "Prompt Engineering", "RAG"],
         "years": 2, "text": "大模型应用开发，构建 Agent 工作流与 RAG"},
        {"skills": ["Python", "Deep Learning", "NLP", "Fine-tuning", "Transformer"],
         "years": 4, "text": "NLP 算法 4 年，负责大模型微调"},
        {"skills": ["Java", "Go", "SQL", "Linux", "Kubernetes", "CI/CD"],
         "years": 4, "text": "后端与云原生开发，熟悉 Kubernetes"},
        {"skills": ["Python", "Computer Vision", "Deep Learning", "TensorRT", "ONNX"],
         "years": 3, "text": "CV 模型部署，TensorRT 优化"},
        {"skills": ["Python", "Knowledge Graph", "NLP", "SQL", "LLM"],
         "years": 3, "text": "知识图谱工程师，结合 LLM 做知识抽取"},
        {"skills": ["Python", "Spark", "Flink", "Kafka", "Data Warehouse"],
         "years": 4, "text": "实时数仓开发，Flink 流计算"},
        {"skills": ["ROS", "C++", "Python", "Linux", "Computer Vision"],
         "years": 3, "text": "机器人算法，SLAM 导航"},
        {"skills": ["Python", "MLOps", "Docker", "Kubernetes", "CI/CD", "Model Serving"],
         "years": 4, "text": "MLOps 平台建设，模型服务部署"},
        {"skills": ["Python", "Machine Learning", "Feature Engineering", "A/B Testing", "Spark"],
         "years": 5, "text": "推荐算法，特征工程与 A/B 实验"},
        {"skills": ["Python", "LLM", "Fine-tuning", "PyTorch", "Distributed Training"],
         "years": 3, "text": "大模型分布式训练"},
        {"skills": ["C++", "Linux", "Embedded Systems", "IoT", "Edge Computing"],
         "years": 2, "text": "物联网设备开发"},
        {"skills": ["Python", "Deep Learning", "PyTorch", "强化学习", "ROS"],
         "years": 3, "text": "机器人强化学习"},
        {"skills": ["Python", "NLP", "Deep Learning", "Machine Learning", "Embedding", "Vector Database"],
         "years": 4, "text": "NLP 与向量检索"},
        {"skills": ["Java", "SQL", "Linux", "Git"],
         "years": 1, "text": "初级 Java 开发"},
    ]
    resumes = []
    for i, p in enumerate(profiles):
        text = (f"姓名：候选人{i+1}\n工作年限：{p['years']} 年\n技能：{'、'.join(p['skills'])}\n"
                f"项目经验：{p['text']}\n证书：无\n学历：本科\n")
        resumes.append({"resume_id": f"resume-{i+1:02d}", "text": text,
                        "gold_skills": p["skills"], "years": p["years"]})
    return resumes


def generate_gold_match(jds: list[dict], resumes: list[dict]) -> list[dict]:
    """生成匹配金标准：基于频率聚合的岗位画像（核心必备技能）。"""
    from collections import Counter
    # 按岗位聚合核心必备技能（>=60% JD 要求）
    role_req: dict[str, set] = {}
    for title in {j["title"] for j in jds}:
        n = sum(1 for j in jds if j["title"] == title) or 1
        c = Counter()
        for j in jds:
            if j["title"] == title:
                for s in j["gold_required_skills"]:
                    c[s] += 1
        role_req[title] = {s for s, cnt in c.items() if cnt / n >= 0.6}

    gold = []
    for r in resumes:
        have = set(r["gold_skills"])
        for title, req in role_req.items():
            cover = len(req & have) / len(req) if req else 0
            gold.append({
                "resume_id": r["resume_id"],
                "role": title,
                "match": 1 if cover >= 0.6 else 0,
                "coverage": round(cover, 3),
            })
    return gold


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    jds, duplicate_pairs = generate_jds(110)
    resumes = generate_resumes(20)
    gold_match = generate_gold_match(jds, resumes)

    (DATA_DIR / "jds.json").write_text(json.dumps(jds, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "resumes.json").write_text(json.dumps(resumes, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_jd = [{"job_id": j["job_id"], "title": j["title"],
                "required_skills": j["gold_required_skills"],
                "preferred_skills": j["gold_preferred_skills"]} for j in jds]
    (DATA_DIR / "gold_jd.json").write_text(json.dumps(gold_jd, ensure_ascii=False, indent=2), encoding="utf-8")

    gold_resume = [{"resume_id": r["resume_id"], "skills": r["gold_skills"]} for r in resumes]
    (DATA_DIR / "gold_resume.json").write_text(json.dumps(gold_resume, ensure_ascii=False, indent=2), encoding="utf-8")

    (DATA_DIR / "gold_match.json").write_text(json.dumps(gold_match, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "gold_duplicates.json").write_text(json.dumps(duplicate_pairs, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"生成完成：{len(jds)} 条 JD，{len(resumes)} 份简历，{len(gold_match)} 条匹配金标准，{len(duplicate_pairs)} 对抄袭")
    print(f"  新兴岗位 JD 数：{sum(1 for j in jds if j['title'] in EMERGING)}")


if __name__ == "__main__":
    main()
