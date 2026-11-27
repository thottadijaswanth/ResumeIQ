from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class SkillMatchItem(BaseModel):
    skill: str
    category: str = "General"
    match_type: str = "exact"  # exact, normalized, semantic
    evidence: str = ""  # Where in resume this skill was found


class MissingSkillItem(BaseModel):
    skill: str
    importance: str = "required"  # required, preferred, nice-to-have
    category: str = "General"
    suggestion: str = ""


class ExperienceGap(BaseModel):
    required_years: Optional[float] = None
    candidate_years: Optional[float] = None
    role_level_match: str = "Match"  # Entry, Mid, Senior, Lead
    details: str = ""
    gaps: List[str] = Field(default_factory=list)


class ATSAnalysis(BaseModel):
    estimated_ats_score: float
    keyword_coverage_percent: float
    quantifiable_achievements_count: int
    action_verbs_count: int
    section_completeness: Dict[str, bool] = Field(default_factory=dict)
    formatting_risks: List[str] = Field(default_factory=list)
    keyword_stuffing_detected: bool = False
    strengths: List[str] = Field(default_factory=list)
    summary: str = ""


class RecommendationItem(BaseModel):
    id: str
    category: str  # Skills, Experience, Formatting, Keywords, ATS
    severity: str  # Critical, High, Medium, Low
    issue: str
    explanation: str
    suggested_action: str
    related_requirement: str


class RequirementEvidence(BaseModel):
    requirement: str
    match_status: str  # Strong match, Partial match, Not found
    evidence: str
    confidence: float


class SkillEvidenceAssessment(BaseModel):
    skill: str
    status: str = "not_found"  # strong, partial, not_found
    evidence: str = ""
    confidence: float = 0.0


class ExperienceAssessmentSummary(BaseModel):
    relevant_years: Optional[float] = None
    required_years: Optional[float] = None
    summary: str = ""
    evidence: List[str] = Field(default_factory=list)
    status: str = "not_found"


class ResponsibilityMatchSummary(BaseModel):
    matched_responsibilities: List[str] = Field(default_factory=list)
    missing_responsibilities: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    status: str = "not_found"


class SeniorityMatchSummary(BaseModel):
    target_level: str = ""
    candidate_level: str = ""
    status: str = "not_found"
    evidence: str = ""


class CandidateMatchAssessment(BaseModel):
    candidate_id: str = ""
    required_skill_assessment: List[SkillEvidenceAssessment] = Field(default_factory=list)
    preferred_skill_assessment: List[SkillEvidenceAssessment] = Field(default_factory=list)
    experience_assessment: ExperienceAssessmentSummary = Field(default_factory=ExperienceAssessmentSummary)
    responsibility_match: ResponsibilityMatchSummary = Field(default_factory=ResponsibilityMatchSummary)
    seniority_match: SeniorityMatchSummary = Field(default_factory=SeniorityMatchSummary)
    missing_requirements: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    recommendation: str = "moderate_match"
    confidence: float = 0.0
    provider: str = ""
    model: str = ""


class CandidateRerankResult(BaseModel):
    classification: str = "PARTIAL_MATCH"  # STRONG_MATCH, GOOD_MATCH, PARTIAL_MATCH, WEAK_MATCH
    confidence: float = 0.0
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class AIHealthResponse(BaseModel):
    provider: str
    configured_provider: Optional[str] = None
    status: str
    available: bool = False
    model: str
    mode: str
    embedding_provider: str
    fallback_enabled: bool = False
    fallback_provider: Optional[str] = None
    message: Optional[str] = None


class AIModeUpdateRequest(BaseModel):
    provider: str  # "auto" | "ollama" | "openai" | "mock"


class ScreeningRunRequest(BaseModel):
    resume_ids: Optional[List[str]] = None
    use_ai_rerank: bool = True
    rerank_top_k: Optional[int] = Field(default=None, ge=1, le=100)


class ScreeningFailureItem(BaseModel):
    filename: str
    reason: str
    resume_id: Optional[str] = None


class CandidateRankItem(BaseModel):
    analysis_id: str
    resume_id: str
    job_id: str
    rank: int
    candidate_name: str
    original_filename: str
    email: str = ""
    location: str = "Unknown"
    experience_years: Optional[float] = None
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    semantic_score: float
    match_classification: str
    ai_reranked: bool = False
    hard_filter_passed: bool = True
    hard_filter_notes: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    created_at: datetime


class CandidateDetailResponse(BaseModel):
    analysis_id: str
    resume_id: str
    job_id: str
    candidate_name: str
    original_filename: str
    email: str = ""
    phone: str = ""
    location: str = "Unknown"
    experience_years: Optional[float] = None
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    semantic_score: float
    match_classification: str
    ai_reranked: bool = False
    hard_filter_passed: bool = True
    hard_filter_notes: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    analysis_result: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    structured_resume: Optional[Dict[str, Any]] = None
    created_at: datetime


class ScreeningRunResponse(BaseModel):
    id: str
    job_id: str
    status: str
    stage: str
    total_resumes: int
    processed_resumes: int
    matched_resumes: int
    failed_resumes: int
    shortlisted_count: int
    reranked_count: int
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_rerank_used: bool = False
    ai_error: Optional[str] = None
    failed_files: List[ScreeningFailureItem] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    top_candidates: List[CandidateRankItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AnalysisResultData(BaseModel):
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    semantic_score: float
    matching_skills: List[SkillMatchItem] = Field(default_factory=list)
    missing_required_skills: List[MissingSkillItem] = Field(default_factory=list)
    missing_preferred_skills: List[MissingSkillItem] = Field(default_factory=list)
    experience_gap_analysis: ExperienceGap
    ats_analysis: ATSAnalysis
    requirements_evidence: List[RequirementEvidence] = Field(default_factory=list)
    scoring_weights: Dict[str, float] = Field(default_factory=dict)
    ai_matching_assessment: Optional[CandidateMatchAssessment] = None
    ai_rerank: Optional[CandidateRerankResult] = None


class AnalysisCreate(BaseModel):
    resume_id: str
    job_id: str


class AnalysisResponse(BaseModel):
    id: str
    user_id: str
    resume_id: str
    job_id: str
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    semantic_score: float
    analysis_result: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TailorResumeRequest(BaseModel):
    target_job_id: Optional[str] = None


class TailoredBulletPoint(BaseModel):
    original: str
    tailored: str
    reason: str
    requires_user_confirmation: bool = False


class TailorResumeResponse(BaseModel):
    job_title: str
    company: str
    tailored_summary: str
    suggested_reordered_skills: List[str]
    tailored_experience: List[Dict[str, Any]]
    suggested_keywords_to_include: List[str]
    notes: List[str]


class CoverLetterRequest(BaseModel):
    tone: Optional[str] = "Professional"  # Professional, Enthusiastic, Confident
    custom_notes: Optional[str] = None


class CoverLetterResponse(BaseModel):
    job_title: str
    company: str
    cover_letter_text: str
    key_points_highlighted: List[str]
