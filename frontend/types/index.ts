export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ExperienceItem {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  duration: string;
  responsibilities: string[];
  achievements: string[];
  technologies: string[];
}

export interface EducationItem {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  gpa?: string;
}

export interface ProjectItem {
  name: string;
  description: string;
  technologies: string[];
  achievements: string[];
  links: string[];
}

export interface StructuredResume {
  name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  skills: string[];
  technical_skills: string[];
  soft_skills: string[];
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  cloud: string[];
  tools: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
  projects: ProjectItem[];
  certifications: string[];
  achievements: string[];
  languages: string[];
}

export interface Resume {
  id: string;
  user_id: string;
  name: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  file_hash?: string;
  raw_text: string;
  structured_data?: StructuredResume;
  candidate_years?: number;
  candidate_location?: string;
  processing_status?: string;
  created_at: string;
  updated_at: string;
}

export interface ResumeSummary {
  id: string;
  name: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  file_hash?: string;
  candidate_years?: number;
  candidate_location?: string;
  processing_status?: string;
  skills?: string[];
  created_at: string;
  updated_at: string;
}

export interface BulkResumeFailureItem {
  filename: string;
  reason: string;
}

export interface BulkResumeUploadItem {
  id: string;
  name: string;
  original_filename: string;
  cached: boolean;
  candidate_years?: number;
  candidate_location?: string;
  skills_count: number;
}

export interface BulkResumeUploadResponse {
  total_received: number;
  processed_count: number;
  cached_count: number;
  failed_count: number;
  resumes: BulkResumeUploadItem[];
  failed_files: BulkResumeFailureItem[];
}

export interface StructuredJob {
  job_title: string;
  company: string;
  location: string;
  work_mode?: "Remote" | "Hybrid" | "On-site" | string;
  min_experience?: number;
  max_experience?: number;
  employment_type?: string;
  notice_period?: string;
  required_skills: string[];
  preferred_skills: string[];
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  cloud: string[];
  tools: string[];
  years_of_experience?: number;
  education_requirements: string[];
  responsibilities: string[];
  qualifications: string[];
  keywords: string[];
}

export interface Job {
  id: string;
  user_id: string;
  title: string;
  company: string;
  location?: string;
  work_mode?: "Remote" | "Hybrid" | "On-site" | string;
  min_experience?: number;
  max_experience?: number;
  required_skills?: string[];
  preferred_skills?: string[];
  education_requirements?: string[];
  employment_type?: string;
  notice_period?: string;
  location_required?: boolean;
  description: string;
  structured_data?: StructuredJob;
  created_at: string;
  updated_at: string;
}

export interface JobSummary {
  id: string;
  title: string;
  company: string;
  location?: string;
  work_mode?: "Remote" | "Hybrid" | "On-site" | string;
  min_experience?: number;
  max_experience?: number;
  required_skills?: string[];
  employment_type?: string;
  created_at: string;
  updated_at: string;
}

export interface SkillMatchItem {
  skill: string;
  category: string;
  match_type: string;
  evidence: string;
}

export interface MissingSkillItem {
  skill: string;
  importance: "required" | "preferred" | "nice-to-have";
  category: string;
  suggestion: string;
}

export interface ExperienceGap {
  required_years?: number;
  candidate_years?: number;
  role_level_match: string;
  details: string;
  gaps: string[];
}

export interface ATSAnalysis {
  estimated_ats_score: number;
  keyword_coverage_percent: number;
  quantifiable_achievements_count: number;
  action_verbs_count: number;
  section_completeness: Record<string, boolean>;
  formatting_risks: string[];
  keyword_stuffing_detected: boolean;
  strengths: string[];
  summary: string;
}

export interface RecommendationItem {
  id: string;
  category: "Skills" | "Experience" | "Formatting" | "Keywords" | "ATS";
  severity: "Critical" | "High" | "Medium" | "Low";
  issue: string;
  explanation: string;
  suggested_action: string;
  related_requirement: string;
}

export interface RequirementEvidence {
  requirement: string;
  match_status: "Strong match" | "Partial match" | "Not found";
  evidence: string;
  confidence: number;
}

export interface AnalysisResultData {
  overall_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  semantic_score: number;
  matching_skills: SkillMatchItem[];
  missing_required_skills: MissingSkillItem[];
  missing_preferred_skills: MissingSkillItem[];
  experience_gap_analysis: ExperienceGap;
  ats_analysis: ATSAnalysis;
  requirements_evidence: RequirementEvidence[];
  scoring_weights: Record<string, number>;
  ai_matching_assessment?: Record<string, any> | null;
}

export interface AIHealthStatus {
  provider: string;
  configured_provider?: string;
  status: string;
  available?: boolean;
  model: string;
  mode: "local" | "cloud" | "mock" | string;
  embedding_provider: string;
  fallback_enabled: boolean;
  fallback_provider?: string | null;
  message?: string | null;
}

export interface CandidateRankItem {
  analysis_id: string;
  resume_id: string;
  job_id: string;
  rank: number;
  candidate_name: string;
  original_filename: string;
  email: string;
  location: string;
  experience_years?: number | null;
  overall_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  semantic_score: number;
  match_classification: string;
  ai_reranked: boolean;
  hard_filter_passed: boolean;
  hard_filter_notes: string[];
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  gaps: string[];
  created_at: string;
}

export interface CandidateDetailResponse {
  analysis_id: string;
  resume_id: string;
  job_id: string;
  candidate_name: string;
  original_filename: string;
  email: string;
  phone: string;
  location: string;
  experience_years?: number | null;
  overall_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  semantic_score: number;
  match_classification: string;
  ai_reranked: boolean;
  hard_filter_passed: boolean;
  hard_filter_notes: string[];
  skills: string[];
  analysis_result: AnalysisResultData & { ai_rerank?: Record<string, any> };
  recommendations: RecommendationItem[];
  structured_resume?: StructuredResume;
  created_at: string;
}

export interface ScreeningRunResponse {
  id: string;
  job_id: string;
  status: string;
  stage: string;
  total_resumes: number;
  processed_resumes: number;
  matched_resumes: number;
  failed_resumes: number;
  shortlisted_count: number;
  reranked_count: number;
  ai_provider?: string | null;
  ai_model?: string | null;
  ai_rerank_used: boolean;
  ai_error?: string | null;
  failed_files: Array<{ filename: string; reason: string; resume_id?: string }>;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  top_candidates: CandidateRankItem[];
}

export interface Analysis {
  id: string;
  user_id: string;
  resume_id: string;
  job_id: string;
  overall_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  semantic_score: number;
  analysis_result: AnalysisResultData;
  recommendations: RecommendationItem[];
  created_at: string;
}

export interface TailorResumeResponse {
  job_title: string;
  company: string;
  tailored_summary: string;
  suggested_reordered_skills: string[];
  tailored_experience: Array<{
    company: string;
    role: string;
    start_date: string;
    end_date: string;
    duration: string;
    responsibilities: string[];
    achievements: string[];
    technologies: string[];
  }>;
  suggested_keywords_to_include: string[];
  notes: string[];
}

export interface CoverLetterResponse {
  job_title: string;
  company: string;
  cover_letter_text: string;
  key_points_highlighted: string[];
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  resume_id?: string;
  status: "Saved" | "Applied" | "Interview" | "Offer" | "Rejected";
  notes?: string;
  applied_at?: string;
  created_at: string;
  updated_at: string;
  job?: JobSummary;
  resume?: ResumeSummary;
}

