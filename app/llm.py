"""LLM 抽象层：可插拔抽取器。

- MockExtractor：规则 + 词典 + 模板，无外部依赖即可跑通全流程；
- SparkExtractor：讯飞星火适配器（骨架，需 SPARK_API_KEY 与真实网络）。
抽取统一输出符合 JSON Schema 的结构化结果，并携带证据 span。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from . import skills as sk
from .config import Config

# 抽取结果 JSON Schema（对齐 FR-03）
SCHEMA = {
    "type": "object",
    "required": ["job_title", "responsibilities", "required_skills", "preferred_skills",
                 "experience", "education", "tech_stack", "industry", "evidence"],
    "properties": {
        "job_title": {"type": "string"},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "preferred_skills": {"type": "array", "items": {"type": "string"}},
        "experience": {"type": "string"},
        "education": {"type": "string"},
        "tech_stack": {"type": "array", "items": {"type": "string"}},
        "industry": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "span": {"type": "string"}},
            },
        },
    },
}


class LLMExtractor(Protocol):
    def extract_job(self, job: dict) -> dict:
        """输入原始 job 记录，输出结构化抽取结果。"""
        ...

    def extract_resume(self, text: str) -> dict:
        ...


def _pick_span(text: str, skill: str, aliases: list[str]) -> str:
    """在文本中定位技能出现位置的证据片段。"""
    candidates = [skill, *aliases]
    lowered = text.lower()
    best = None
    for c in candidates:
        idx = lowered.find(c.lower())
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + len(c) + 30)
            best = text[start:end].strip()
            break
    return best or ""


class MockExtractor:
    """规则化抽取器：技能用词典抽取，职责/经验/学历用正则+模板。"""

    def __init__(self, config: Config):
        self.config = config

    def extract_job(self, job: dict) -> dict:
        title = job.get("title", "")
        desc = job.get("description", "")
        # 区分「必备技能」与「加分技能」两段，避免把加分项误判为必备（技能通胀治理）
        required_part, preferred_part = self._split_required_preferred(desc)
        required = sk.extract_skills_from_text(required_part)
        preferred = sk.extract_skills_from_text(preferred_part)
        # 追加"优先/加分/者优先"句式中的偏好技能
        for m in re.finditer(r"(?:优先|加分|精通|了解)[：:、]?([^。；;\n]{0,30})", desc):
            for s in sk.extract_skills_from_text(m.group(1)):
                if s not in required and s not in preferred:
                    preferred.append(s)

        responsibilities = self._extract_responsibilities(desc)
        experience = self._extract_experience(desc)
        education = self._extract_education(desc)
        tech_stack = required[:6]
        industry = job.get("industry", "人工智能")

        evidence = []
        for s in required:
            span = _pick_span(desc, s, sk.SKILL_DICT.get(s, {}).get("aliases", []))
            evidence.append({"field": "required_skills", "span": span})
        for r in responsibilities[:2]:
            evidence.append({"field": "responsibilities", "span": r})

        return {
            "job_title": title,
            "responsibilities": responsibilities,
            "required_skills": required,
            "preferred_skills": preferred,
            "experience": experience,
            "education": education,
            "tech_stack": tech_stack,
            "industry": industry,
            "evidence": evidence,
        }

    @staticmethod
    def _split_required_preferred(desc: str) -> tuple[str, str]:
        """将 JD 文本切分为「必备」与「加分」两段。

        关键：必备技能只从「任职要求/岗位要求」段抽取，避免把
        「岗位职责」里顺带提到的技能误判为必备（这正是能力通胀来源之一）。
        """
        # 1) 定位要求段起点
        req_start = -1
        for m in ["任职要求", "岗位要求", "任职资格", "职位要求", "requirements"]:
            i = desc.lower().find(m.lower())
            if i >= 0 and (req_start < 0 or i < req_start):
                req_start = i
        # 2) 在要求段内定位加分项起点
        pref_mark = -1
        for m in ["加分项", "优先", "者优先", "bonus", "nice to have"]:
            i = desc.find(m)
            if i >= 0 and (pref_mark < 0 or i < pref_mark):
                pref_mark = i

        if req_start < 0:
            # 没有明确要求段：加分项之前均为必备
            if pref_mark < 0:
                return desc, ""
            line_start = desc.rfind("\n", 0, pref_mark) + 1
            return desc[:line_start], desc[line_start:]

        if pref_mark < 0 or pref_mark < req_start:
            return desc[req_start:], ""

        line_start = desc.rfind("\n", 0, pref_mark) + 1
        return desc[req_start:line_start], desc[line_start:]

    def _extract_responsibilities(self, desc: str) -> list[str]:
        duties: list[str] = []
        # 匹配 "负责..." "参与..." "主导..." 等句式
        for m in re.finditer(r"(负责|参与|主导|设计|搭建|开发|优化|构建|实现)[^。；;\n]{6,60}", desc):
            seg = m.group(0).strip()
            if seg not in duties:
                duties.append(seg)
        if not duties:
            for line in desc.split("\n"):
                line = line.strip()
                if line and len(line) > 6:
                    duties.append(line[:60])
        return duties[:8]

    def _extract_experience(self, desc: str) -> str:
        m = re.search(r"(\d+(?:-\d+)?)\s*年(?:以上)?(?:相关)?(?:工作)?经验", desc)
        return m.group(0) if m else "不限"

    def _extract_education(self, desc: str) -> str:
        for lvl in ["博士", "硕士", "本科", "大专", "研究生"]:
            if lvl in desc:
                return lvl + "及以上"
        return "不限"

    def extract_resume(self, text: str) -> dict:
        skills_found = sk.extract_skills_from_text(text)
        mentions = []
        for s in skills_found:
            span = _pick_span(text, s, sk.SKILL_DICT.get(s, {}).get("aliases", []))
            mentions.append({
                "skill": s,
                "location": "项目" if span else "技能栏",
                "evidence": span,
            })
        years = 0.0
        m = re.search(r"(\d+(?:\.\d+)?)\s*年(?:工作)?经验", text)
        if m:
            years = float(m.group(1))
        return {"skills": mentions, "years_experience": years, "raw": text}


class SparkExtractor:
    """讯飞星火适配器骨架：实现 extract_job 走真实 API。

    需要环境变量 SPARK_API_KEY 与可达网络。若调用失败，抛 RuntimeError，
    上层应降级为 MockExtractor。
    """

    def __init__(self, config: Config):
        self.config = config
        self.api_url = config.get("llm", "spark", "api_url")
        self.api_key = os.environ.get(config.get("llm", "spark", "api_key_env", "SPARK_API_KEY"), "")
        self.model = config.get("llm", "spark", "model")

    def extract_job(self, job: dict) -> dict:
        if not self.api_key:
            raise RuntimeError("SPARK_API_KEY not set")
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed")
        prompt = self._build_prompt(job)
        resp = httpx.post(
            self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.config.get("llm", "spark", "temperature"),
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(self._strip_code_fence(content))

    def extract_resume(self, text: str) -> dict:
        raise NotImplementedError("Spark resume extraction not implemented in skeleton")

    def _build_prompt(self, job: dict) -> str:
        return (
            "你是岗位能力图谱构建助手。请从下面的招聘 JD 中抽取结构化信息，"
            "严格按 JSON Schema 输出，不得编造 JD 中不存在的内容；"
            "无法确认的字段填 'unknown'。每个技能必须给出原文证据 span。\n"
            f"JSON Schema: {json.dumps(SCHEMA, ensure_ascii=False)}\n"
            f"JD 内容:\n{job.get('title','')}\n{job.get('description','')}"
        )

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text


def build_extractor(config: Config) -> LLMExtractor:
    provider = config.get("llm", "provider", default="mock")
    if provider == "spark":
        return SparkExtractor(config)
    return MockExtractor(config)
