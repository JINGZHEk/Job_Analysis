"""领域模型：Job、Skill、Resume、Claim、Evidence、RoleDefinition 等核心数据对象。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

ISO = "%Y-%m-%dT%H:%M:%S"


def _ts(s: str) -> datetime:
    try:
        return datetime.strptime(s, ISO)
    except ValueError:
        return datetime.fromisoformat(s)


@dataclass
class SourceMeta:
    source_type: str = "招聘平台"           # 企业官网/招聘平台/技术社区/课程与认证/行业报告/简历
    url: str = ""
    publisher: str = ""
    published_at: str = ""                  # ISO 时间或空
    collected_at: str = field(default_factory=lambda: datetime.now().strftime(ISO))
    language: str = "zh"
    file_hash: str = ""


@dataclass
class Job:
    job_id: str
    title: str
    description: str
    responsibilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    experience: str = ""
    education: str = ""
    tech_stack: list[str] = field(default_factory=list)
    industry: str = "人工智能"
    level: str = "中级"                      # 初级/中级/高级/专家
    source: SourceMeta = field(default_factory=SourceMeta)
    # 治理层产生的标签
    quality_flags: list[str] = field(default_factory=list)
    duplicate_group: Optional[str] = None
    duplication_risk: float = 0.0
    skills_density: float = 0.0
    rare_skill_ratio: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Skill:
    skill_id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    category: str = ""
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SkillMention:
    """简历中技能出现的位置与证据。"""
    skill_id: str
    name: str
    location: str = ""        # 技能栏/项目/证书/教育
    evidence: str = ""
    years: float = 0.0
    level: str = ""           # 掌握程度


@dataclass
class Resume:
    resume_id: str
    raw_text: str
    name: str = ""
    skills: list[SkillMention] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    years_experience: float = 0.0
    education: str = ""
    certs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Evidence:
    source_id: str
    evidence_span: str
    source_type: str = ""
    observed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Claim:
    """一条可追溯的图谱断言。"""
    claim_id: str
    subject: str
    predicate: str
    object: str
    source_id: str = ""
    evidence_span: str = ""
    observed_at: str = ""
    valid_from: str = ""
    valid_to: Optional[str] = None
    trust_score: float = 0.0
    confidence: float = 0.0
    verification_status: str = "unverified"   # verified/unverified/conflict
    review_status: str = "pending"            # pending/approved/rejected/published
    is_required: bool = True
    proficiency: str = ""
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RoleDefinition:
    role_id: str
    name: str
    core_responsibilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    typical_scenarios: list[str] = field(default_factory=list)
    industry: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    is_new: bool = False
    emergence_score: float = 0.0
    lifecycle: str = "稳定"                 # 萌芽/增长/稳定/衰退

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchResult:
    resume_id: str
    role_name: str
    total_score: float = 0.0
    hard_gate_pass: bool = True
    dimensions: dict[str, float] = field(default_factory=dict)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    risk_items: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningPathStep:
    step: int
    skill: str
    prerequisite_of: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    completion_criteria: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrendInfo:
    skill: str
    trend_state: str = "稳定"               # 萌芽/增长/稳定/衰退
    growth_rate: float = 0.0
    emergence_score: float = 0.0
    first_seen: str = ""
    last_seen: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
