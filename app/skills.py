"""技能标准化：词典 + 别名表 + 规则归一。"""
from __future__ import annotations

import re
from collections import Counter

# 技能本体（含别名）。category 用于全景图谱分组。
SKILL_DICT: dict[str, dict] = {
    "Python": {"aliases": ["python", "python3"], "category": "编程语言"},
    "Java": {"aliases": ["java", "j2ee"], "category": "编程语言"},
    "C++": {"aliases": ["c++", "cpp", "cplusplus"], "category": "编程语言"},
    "Go": {"aliases": ["golang", "go语言"], "category": "编程语言"},
    "JavaScript": {"aliases": ["js", "javascript", "es6"], "category": "编程语言"},
    "TypeScript": {"aliases": ["ts", "typescript"], "category": "编程语言"},
    "SQL": {"aliases": ["mysql", "sql语言"], "category": "数据库"},
    "Spark": {"aliases": ["apache spark"], "category": "大数据"},
    "Flink": {"aliases": ["apache flink"], "category": "大数据"},
    "Hadoop": {"aliases": ["hdfs", "mapreduce"], "category": "大数据"},
    "Hive": {"aliases": ["hive sql"], "category": "大数据"},
    "Kafka": {"aliases": ["消息队列", "kafka集群"], "category": "大数据"},
    "PyTorch": {"aliases": ["pytorch", "torch"], "category": "深度学习框架"},
    "TensorFlow": {"aliases": ["tensorflow", "tf"], "category": "深度学习框架"},
    "Transformer": {"aliases": ["transformer模型", "transformer"], "category": "模型架构"},
    "LLM": {"aliases": ["大语言模型", "大模型", "llm"], "category": "模型架构"},
    "RAG": {"aliases": ["检索增强生成", "rag"], "category": "模型架构"},
    "Prompt Engineering": {"aliases": ["提示工程", "prompt"], "category": "模型架构"},
    "Fine-tuning": {"aliases": ["微调", "sft", "lora"], "category": "模型架构"},
    "Embedding": {"aliases": ["向量化", "词嵌入", "embedding"], "category": "模型架构"},
    "Machine Learning": {"aliases": ["机器学习", "ml"], "category": "算法"},
    "Deep Learning": {"aliases": ["深度学习", "dl"], "category": "算法"},
    "NLP": {"aliases": ["自然语言处理", "nlp"], "category": "算法"},
    "Computer Vision": {"aliases": ["计算机视觉", "cv", "图像识别"], "category": "算法"},
    "Recommendation System": {"aliases": ["推荐系统", "推荐算法"], "category": "算法"},
    "Knowledge Graph": {"aliases": ["知识图谱", "kg"], "category": "算法"},
    "Docker": {"aliases": ["容器", "docker容器"], "category": "工程化"},
    "Kubernetes": {"aliases": ["k8s", "容器编排"], "category": "工程化"},
    "Linux": {"aliases": ["linux系统"], "category": "工程化"},
    "Git": {"aliases": ["版本控制", "git"], "category": "工程化"},
    "CI/CD": {"aliases": ["cicd", "持续集成", "持续部署"], "category": "工程化"},
    "LangChain": {"aliases": ["langchain"], "category": "工具"},
    "Vector Database": {"aliases": ["向量数据库", "milvus", "faiss"], "category": "工具"},
    "AWS": {"aliases": ["亚马逊云", "aws"], "category": "云平台"},
    "阿里云": {"aliases": ["aliyun", "alibaba cloud"], "category": "云平台"},
    "TensorRT": {"aliases": ["tensorrt"], "category": "工程化"},
    "ONNX": {"aliases": ["onnx"], "category": "工程化"},
    "Distributed Training": {"aliases": ["分布式训练", "deepspeed", "多卡训练"], "category": "工程化"},
    "Data Warehouse": {"aliases": ["数据仓库", "数仓"], "category": "大数据"},
    "ETL": {"aliases": ["数据清洗", "数据管道", "etl"], "category": "大数据"},
    "Feature Engineering": {"aliases": ["特征工程"], "category": "算法"},
    "A/B Testing": {"aliases": ["ab测试", "abtest"], "category": "算法"},
    "Model Serving": {"aliases": ["模型部署", "模型服务"], "category": "工程化"},
    "MLOps": {"aliases": ["mlops", "模型运维"], "category": "工程化"},
    "Hugging Face": {"aliases": ["huggingface", "hf"], "category": "工具"},
    "Web Crawler": {"aliases": ["爬虫", "scrapy", "数据采集"], "category": "工程化"},
    "IoT": {"aliases": ["物联网", "iot"], "category": "物联网"},
    "Edge Computing": {"aliases": ["边缘计算"], "category": "物联网"},
    "MQTT": {"aliases": ["mqtt协议"], "category": "物联网"},
    "Embedded Systems": {"aliases": ["嵌入式", "单片机", "stm32"], "category": "物联网"},
    "ROS": {"aliases": ["ros系统", "机器人操作系统"], "category": "智能系统"},
    "强化学习": {"aliases": ["rl", "reinforcement learning"], "category": "算法"},
    "迁移学习": {"aliases": ["transfer learning"], "category": "算法"},
    "多模态": {"aliases": ["multimodal", "多模态模型", "文生图"], "category": "模型架构"},
    "Agent": {"aliases": ["智能体", "ai agent", "agent开发"], "category": "模型架构"},
    "语音识别": {"aliases": ["asr", "speech recognition"], "category": "算法"},
}

# 别名 -> 规范名 反查表
_ALIAS_TO_CANON: dict[str, str] = {}
for _canon, _meta in SKILL_DICT.items():
    _ALIAS_TO_CANON[_canon.lower()] = _canon
    for _alias in _meta["aliases"]:
        _ALIAS_TO_CANON[_alias.lower()] = _canon


def normalize_skill(raw: str) -> str | None:
    """返回规范技能名，未命中返回 None。"""
    key = raw.strip().lower()
    key = re.sub(r"[\s]+", " ", key)
    if key in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[key]
    # 中英文混合：若 raw 直接匹配别名
    return None


def extract_skills_from_text(text: str) -> list[str]:
    """在文本中扫描已知技能/别名，返回规范技能名列表（去重保持顺序）。"""
    lowered = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    # 按别名长度降序匹配，避免 'go' 之类短词误伤
    candidates = sorted(_ALIAS_TO_CANON.keys(), key=len, reverse=True)
    for alias in candidates:
        # 用词边界避免子串误匹配（中文无边界，英文用 \b）
        if len(alias) <= 2:
            pattern = r"(?<![a-zA-Z])" + re.escape(alias) + r"(?![a-zA-Z])"
        else:
            pattern = re.escape(alias)
        if re.search(pattern, lowered):
            canon = _ALIAS_TO_CANON[alias]
            if canon not in seen:
                seen.add(canon)
                found.append(canon)
    return found


def category_of(skill: str) -> str:
    return SKILL_DICT.get(skill, {}).get("category", "其他")
