from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.passwords import MIN_LENGTH as PASSWORD_MIN_LENGTH
from app.services.passwords import validate_password


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
    full_name: str
    accept_terms: bool = False

    _check_password = field_validator("password")(validate_password)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    _check_password = field_validator("password")(validate_password)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EducationItem(BaseModel):
    degree: str = ""
    institution: str = ""
    major: str = ""
    start_date: str = ""
    graduation_date: str = ""
    gpa: str = ""
    coursework: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    industry: str = ""


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    role: str = ""
    results: str = ""
    github: str = ""
    demo: str = ""


class SkillsBlock(BaseModel):
    model_config = {"extra": "allow"}
    craft: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    programming: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    technical: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class CareerGoals(BaseModel):
    desired_career: str = ""
    desired_role: str = ""
    desired_industry: str = ""
    experience_level: str = "entry"
    short_term_goal: str = ""
    long_term_goal: str = ""


class ProfileIn(BaseModel):
    full_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    professional_status: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    education: Optional[list[EducationItem]] = None
    experience: Optional[list[ExperienceItem]] = None
    skills: Optional[SkillsBlock] = None
    projects: Optional[list[ProjectItem]] = None
    career_goals: Optional[CareerGoals] = None
    linkedin_url: Optional[str] = None
    github_username: Optional[str] = None


class ProfileOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    country: str
    city: str
    professional_status: str
    headline: str
    summary: str
    education: list[Any]
    experience: list[Any]
    skills: dict[str, Any]
    projects: list[Any]
    career_goals: dict[str, Any]
    linkedin_url: str = ""
    github_username: str = ""
    readiness_score: float
    resume_health: float
    interview_performance: float
    plan: str
    updated_at: Optional[datetime] = None


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[int] = None


class SuggestedMemory(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    category: str = "direction"


class MemoryConfirmIn(BaseModel):
    memories: list[SuggestedMemory] = Field(default_factory=list, max_length=20)


class SkillGapIn(BaseModel):
    target_role: str = Field(min_length=1, max_length=120)
    compare_role: Optional[str] = Field(default=None, max_length=120)


class RoadmapIn(BaseModel):
    target_role: str = ""
    focus_skill: str = ""
    duration_months: int = 3
    duration_unit: str = "months"
    duration_value: Optional[int] = None


class RoadmapTaskPatch(BaseModel):
    milestone_index: int
    task_id: str = ""
    completed: Optional[bool] = None
    deadline: Optional[str] = None
    custom_text: Optional[str] = None
    action: Optional[str] = None  # complete | reorder | add | remove | deadline


class ResumeGenerateIn(BaseModel):
    template: str = "ats_classic"
    version_type: str = "master"
    target_role: str = ""
    title: Optional[str] = None


class ResumeUpdateIn(BaseModel):
    title: Optional[str] = None
    template: Optional[str] = None
    content: Optional[dict[str, Any]] = None
    version_type: Optional[str] = None
    target_role: Optional[str] = None


class TailorIn(BaseModel):
    resume_id: int
    job_description: str
    target_role: str = ""


class ATSIn(BaseModel):
    resume_id: int
    job_description: str = Field(min_length=20, max_length=20000)


class CoverLetterIn(BaseModel):
    resume_id: int
    job_description: str
    style: str = "professional"


class InterviewStartIn(BaseModel):
    target_role: str
    interview_type: str = "mixed"
    job_description: str = ""
    question_count: int = 6
    mode: str = "text"


class InterviewAnswerIn(BaseModel):
    answer: str = Field(min_length=1)
    duration_ms: int = Field(default=0, ge=0, le=4 * 60 * 60 * 1000)

    @field_validator("answer")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Answer cannot be empty. Say what you would say in the room.")
        return value


class AccountDeleteIn(BaseModel):
    password: str


class PlanUpdateIn(BaseModel):
    plan: str


class PlanCheckoutIn(BaseModel):
    plan: str
    password: str = ""
    card_name: str = ""
    card_number: str = ""
    exp_month: int = 0
    exp_year: int = 0
    exp: str = ""
    cvc: str = ""


class PlanConfirmIn(BaseModel):
    intent_token: str
    password: str
    confirmation: str = ""


class AdminPlanIn(BaseModel):
    plan: str
    password: str


class MemoryIn(BaseModel):
    category: str = Field(max_length=64)
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    enabled: bool = True


class MemoryUpdateIn(BaseModel):
    value: Optional[str] = Field(default=None, max_length=2000)
    enabled: Optional[bool] = None
