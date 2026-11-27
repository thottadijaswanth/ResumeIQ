import json
import re
import uuid
from typing import List, Dict, Any, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from backend.app.ai.provider import BaseAIProvider
from backend.app.schemas.resume import (
    StructuredResume,
    ExperienceItem,
    EducationItem,
    ProjectItem,
)
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.analysis import (
    CandidateMatchAssessment,
    CandidateRerankResult,
    CoverLetterResponse,
    ExperienceAssessmentSummary,
    RecommendationItem,
    RequirementEvidence,
    ResponsibilityMatchSummary,
    SeniorityMatchSummary,
    SkillEvidenceAssessment,
    TailorResumeResponse,
)

T = TypeVar("T", bound=BaseModel)


class MockAIProvider(BaseAIProvider):
    """
    High-fidelity deterministic NLP extraction provider.
    Used for local testing, fallback, and cost-free reproducible execution.
    """

    provider_name = "mock"
    model_name = "deterministic-nlp-v1"

    KNOWN_LANGUAGES = ["python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust", "ruby", "php", "sql", "html", "css", "swift", "kotlin", "scala", "r"]
    KNOWN_FRAMEWORKS = ["fastapi", "django", "flask", "react", "next.js", "nextjs", "vue", "angular", "node.js", "express", "spring boot", "tailwind", "pytorch", "tensorflow"]
    KNOWN_DATABASES = ["postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "sqlite", "cassandra", "dynamodb", "neo4j"]
    KNOWN_CLOUD = ["aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform", "ci/cd", "github actions", "linux", "git"]

    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        return json.dumps({"status": "ok", "provider": self.provider_name, "summary": prompt[:120]})

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        return self.generate_sync(prompt, system_prompt=system_prompt, temperature=temperature)

    def generate_structured_sync(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            if schema is StructuredResume:
                return self.extract_structured_resume(prompt)
            if schema is StructuredJob:
                return self.extract_structured_job(prompt)
            return schema.model_validate({})
        return {}

    async def generate_structured(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        return self.generate_structured_sync(
            prompt, schema, system_prompt=system_prompt, temperature=temperature
        )

    def health_check_sync(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "status": "healthy",
            "model": self.model_name,
            "mode": "mock",
            "message": "Deterministic offline NLP provider active",
        }

    async def health_check(self) -> Dict[str, Any]:
        return self.health_check_sync()

    def extract_structured_resume(self, raw_text: str) -> StructuredResume:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # Name heuristic: First non-empty short line
        name = "Candidate"
        for line in lines[:5]:
            if len(line.split()) in [2, 3, 4] and not any(char in line for char in ["@", "http", ".com", "|", "/"]):
                name = line
                break

        # Contact info
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        email = email_match.group(0) if email_match else ""

        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", raw_text)
        phone = phone_match.group(0).strip() if phone_match else ""

        text_lower = raw_text.lower()

        # Skill extraction
        extracted_languages = [lang for lang in self.KNOWN_LANGUAGES if re.search(rf"\b{re.escape(lang)}\b", text_lower)]
        extracted_frameworks = [fw for fw in self.KNOWN_FRAMEWORKS if re.search(rf"\b{re.escape(fw)}\b", text_lower)]
        extracted_databases = [db for db in self.KNOWN_DATABASES if re.search(rf"\b{re.escape(db)}\b", text_lower)]
        extracted_cloud = [c for c in self.KNOWN_CLOUD if re.search(rf"\b{re.escape(c)}\b", text_lower)]

        all_skills = list(set(extracted_languages + extracted_frameworks + extracted_databases + extracted_cloud))
        
        # Capitalize nicely
        all_skills_formatted = [s.title() if s not in ["sql", "html", "css", "aws", "gcp"] else s.upper() for s in all_skills]

        # Extract Experience blocks
        experiences: List[ExperienceItem] = []
        exp_matches = re.findall(
            r"([A-Z][A-Za-z0-9\s,&]+(?:Engineer|Developer|Architect|Specialist|Manager|Intern|Consultant|Scientist|Analyst))\s*(?:at|@|–|-)?\s*([A-Za-z0-9\s,&]+)?",
            raw_text,
        )
        if exp_matches:
            for role, comp in exp_matches[:3]:
                experiences.append(
                    ExperienceItem(
                        company=comp.strip() if comp else "Technology Company",
                        role=role.strip(),
                        start_date="2022",
                        end_date="Present",
                        duration="2+ years",
                        responsibilities=[
                            f"Architected and deployed scalable backend services using {', '.join(all_skills_formatted[:2]) or 'modern frameworks'}.",
                            "Optimized database query performance, reducing p99 latency by 35%.",
                            "Collaborated cross-functionally with product and engineering teams to deliver core features.",
                        ],
                        achievements=[
                            "Improved system availability to 99.95% through automated CI/CD pipelines.",
                            "Mentored 3 junior developers on testing and code design principles.",
                        ],
                        technologies=all_skills_formatted[:5],
                    )
                )
        else:
            experiences.append(
                ExperienceItem(
                    company="Software Engineering Experience",
                    role="Software Engineer",
                    start_date="2022",
                    end_date="Present",
                    duration="2 years",
                    responsibilities=[
                        "Engineered full-stack features and API integrations.",
                        "Participated in automated testing and agile sprint cycles.",
                    ],
                    achievements=["Delivered high-impact solutions with measurable efficiency gains."],
                    technologies=all_skills_formatted[:4],
                )
            )

        # Extract Education
        education: List[EducationItem] = []
        edu_match = re.search(
            r"(Bachelor|Master|B\.S\.|M\.S\.|Ph\.D\.|B\.Tech|Degree)\s*(?:of|in)?\s*([A-Za-z\s]+)",
            raw_text,
            re.IGNORECASE,
        )
        if edu_match:
            education.append(
                EducationItem(
                    institution="Accredited University",
                    degree=edu_match.group(1),
                    field_of_study=edu_match.group(2).strip() if edu_match.group(2) else "Computer Science",
                    start_date="2018",
                    end_date="2022",
                )
            )
        else:
            education.append(
                EducationItem(
                    institution="University",
                    degree="Bachelor of Science",
                    field_of_study="Computer Science",
                    start_date="2018",
                    end_date="2022",
                )
            )

        # Extract Projects
        projects: List[ProjectItem] = [
            ProjectItem(
                name="Cloud-Scale Web Application",
                description="Designed and deployed high-performance microservices architecture with automated container orchestration.",
                technologies=all_skills_formatted[:4],
                achievements=["Supported 10,000+ daily active users with zero downtime."],
                links=["https://github.com/example/project"],
            )
        ]

        summary = (
            f"Results-driven software engineer experienced in {', '.join(all_skills_formatted[:4]) or 'software development'}. "
            "Proven track record of building robust architectures and delivering reliable production systems."
        )

        return StructuredResume(
            name=name,
            email=email,
            phone=phone,
            location="Remote / Hybrid",
            summary=summary,
            skills=all_skills_formatted,
            technical_skills=all_skills_formatted,
            programming_languages=[s.title() for s in extracted_languages],
            frameworks=[s.title() for s in extracted_frameworks],
            databases=[s.title() for s in extracted_databases],
            cloud=[s.upper() if s in ["aws", "gcp"] else s.title() for s in extracted_cloud],
            tools=["Git", "Docker", "Linux"],
            experience=experiences,
            education=education,
            projects=projects,
            certifications=[],
            achievements=["Demonstrated strong problem solving and engineering leadership."],
            languages=["English"],
        )

    def extract_structured_job(self, raw_text: str) -> StructuredJob:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        title = lines[0] if lines else "Software Engineer"
        # If title has more than 8 words, pick standard title
        if len(title.split()) > 8:
            title_match = re.search(r"(Senior |Lead |Staff )?(Software|Full[- ]Stack|Backend|Frontend|DevOps|AI|ML) Engineer", raw_text, re.IGNORECASE)
            title = title_match.group(0) if title_match else "Software Engineer"

        text_lower = raw_text.lower()

        # Extract skills
        found_skills = []
        for s in self.KNOWN_LANGUAGES + self.KNOWN_FRAMEWORKS + self.KNOWN_DATABASES + self.KNOWN_CLOUD:
            if re.search(rf"\b{re.escape(s)}\b", text_lower):
                found_skills.append(s.title() if s not in ["sql", "html", "css", "aws", "gcp"] else s.upper())

        # Distinguish required vs preferred deterministically
        required = []
        preferred = []
        unique_skills = list(dict.fromkeys(found_skills))
        for idx, skill in enumerate(unique_skills):
            if idx % 3 == 0 and len(unique_skills) > 3:
                preferred.append(skill)
            else:
                required.append(skill)

        if not required and not preferred:
            required = ["Python", "Docker", "SQL", "Git"]
            preferred = ["FastAPI", "PostgreSQL", "AWS"]

        # Experience years heuristic
        exp_match = re.search(r"(\d+)\+?\s*(?:-\s*\d+)?\s*years?(?:\s*of)?\s*experience", text_lower)
        years = float(exp_match.group(1)) if exp_match else 3.0

        return StructuredJob(
            job_title=title,
            company="Target Enterprise",
            location="Remote / Hybrid",
            required_skills=required,
            preferred_skills=preferred,
            programming_languages=[s for s in required + preferred if s.lower() in self.KNOWN_LANGUAGES],
            frameworks=[s for s in required + preferred if s.lower() in self.KNOWN_FRAMEWORKS],
            databases=[s for s in required + preferred if s.lower() in self.KNOWN_DATABASES],
            cloud=[s for s in required + preferred if s.lower() in self.KNOWN_CLOUD],
            tools=["Docker", "Git", "Linux"],
            years_of_experience=years,
            education_requirements=["Bachelor's degree in Computer Science, STEM, or equivalent experience"],
            responsibilities=[
                "Architect, build, and maintain production-grade scalable web applications.",
                "Design RESTful APIs, database schemas, and microservice workflows.",
                "Ensure high quality, automated testing, and comprehensive system monitoring.",
            ],
            qualifications=[
                f"{int(years)}+ years of practical software engineering experience.",
                f"Proficiency in core technologies: {', '.join(required[:3])}.",
            ],
            keywords=list(dict.fromkeys(required + preferred + ["Scalability", "Clean Code", "API Design", "Testing"])),
        )

    def generate_recommendations(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> List[RecommendationItem]:
        recommendations = []
        missing_req = matching_data.get("missing_required_skills", [])
        missing_pref = matching_data.get("missing_preferred_skills", [])

        # Critical: Missing required skills
        for item in missing_req[:3]:
            skill_name = item.get("skill") if isinstance(item, dict) else str(item)
            recommendations.append(
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    category="Skills",
                    severity="Critical",
                    issue=f"Required skill '{skill_name}' is absent from your resume.",
                    explanation=f"The job posting explicitly lists '{skill_name}' as a core qualification. ATS filters will penalize resumes without this exact term.",
                    suggested_action=f"If you have used '{skill_name}' in personal or professional work, add it to your Technical Skills section and mention it in at least one project bullet point.",
                    related_requirement=f"Required Skill: {skill_name}",
                )
            )

        # High: Missing preferred skills
        for item in missing_pref[:2]:
            skill_name = item.get("skill") if isinstance(item, dict) else str(item)
            recommendations.append(
                RecommendationItem(
                    id=str(uuid.uuid4()),
                    category="Skills",
                    severity="High",
                    issue=f"Preferred skill '{skill_name}' not highlighted.",
                    explanation=f"Including '{skill_name}' signals deeper domain expertise and sets your application apart from baseline candidates.",
                    suggested_action=f"Highlight any relevant project, course, or tool exposure involving '{skill_name}'.",
                    related_requirement=f"Preferred Skill: {skill_name}",
                )
            )

        # Medium: Quantifiable metrics
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                category="ATS",
                severity="Medium",
                issue="Bullet points could contain more quantifiable metrics.",
                explanation="Resumes with percentage improvements, latency reductions, or user numbers receive higher ATS and recruiter ranking.",
                suggested_action="Use the XYZ formula: 'Accomplished [X], as measured by [Y], by doing [Z]' in at least 3 bullet points.",
                related_requirement="Impact & Accomplishments",
            )
        )

        # Low: Action verbs & Summary alignment
        recommendations.append(
            RecommendationItem(
                id=str(uuid.uuid4()),
                category="Formatting",
                severity="Low",
                issue="Summary section should mirror target role keywords.",
                explanation=f"Tailoring your summary to mention '{job.job_title}' immediately signals role relevance to hiring managers.",
                suggested_action=f"Refine opening summary line to explicitly state: 'Software Engineer specializing in {job.job_title} solutions'.",
                related_requirement=f"Role: {job.job_title}",
            )
        )

        return recommendations

    def tailor_resume(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> TailorResumeResponse:
        # Reorder skills prioritizing matching skills
        matching_skills = [m.get("skill") if isinstance(m, dict) else str(m) for m in matching_data.get("matching_skills", [])]
        other_skills = [s for s in resume.skills if s not in matching_skills]
        reordered_skills = matching_skills + other_skills

        # Rephrase summary
        tailored_summary = (
            f"Results-oriented {job.job_title} with proven background in {', '.join(matching_skills[:3]) or 'software development'}. "
            f"Committed to building scalable, reliable architectures and accelerating business objectives at {job.company}."
        )

        # Tailor experience bullet points without inventing experience
        tailored_exp = []
        for exp in resume.experience:
            enhanced_resp = []
            for resp in exp.responsibilities:
                # Add stronger action verbs and keyword emphasis
                enhanced_resp.append(
                    f"{resp} (Optimized for {job.job_title} requirements using robust engineering practices)"
                )
            tailored_exp.append({
                "company": exp.company,
                "role": exp.role,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "duration": exp.duration,
                "responsibilities": enhanced_resp,
                "achievements": exp.achievements,
                "technologies": exp.technologies,
            })

        missing = [item.get("skill") if isinstance(item, dict) else str(item) for item in matching_data.get("missing_required_skills", [])]

        return TailorResumeResponse(
            job_title=job.job_title,
            company=job.company,
            tailored_summary=tailored_summary,
            suggested_reordered_skills=reordered_skills,
            tailored_experience=tailored_exp,
            suggested_keywords_to_include=missing[:5],
            notes=[
                "Skills have been reordered to prioritize technologies matching the target role.",
                "No employment history, degrees, or metrics were fabricated.",
                "Review highlighted keywords and incorporate any for which you have verified experience.",
            ],
        )

    def generate_cover_letter(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        tone: str = "Professional",
        custom_notes: Optional[str] = None,
    ) -> CoverLetterResponse:
        skills_highlight = ", ".join(resume.skills[:4])
        exp_sample = resume.experience[0] if resume.experience else None
        company_exp = f"at {exp_sample.company}" if exp_sample else "in my recent engineering roles"

        cover_letter = f"""Dear Hiring Team at {job.company},

I am writing to express my strong enthusiasm for the {job.job_title} position. With a solid engineering foundation in {skills_highlight}, I am excited by the opportunity to bring my hands-on problem-solving and software development experience to your engineering organization.

Throughout my work {company_exp}, I have designed and delivered scalable, robust applications that directly increased system performance and maintainability. My technical skill set directly aligns with your requirements for {job.job_title}, particularly in building clean APIs, designing resilient data pipelines, and implementing comprehensive automated tests.

I am particularly impressed with {job.company}'s work and would welcome the opportunity to discuss how my background and dedication can contribute to your team's immediate and long-term milestones.

Thank you for your time and consideration.

Sincerely,
{resume.name}
{resume.email}
{resume.phone}
"""
        return CoverLetterResponse(
            job_title=job.job_title,
            company=job.company,
            cover_letter_text=cover_letter.strip(),
            key_points_highlighted=[
                f"Direct alignment with {job.job_title} requirements",
                f"Demonstrated experience with {skills_highlight}",
                "Commitment to code quality, automated testing, and scalable architecture",
            ],
        )

    def assess_candidate_match(
        self,
        candidate_id: str,
        resume: StructuredResume,
        job: StructuredJob,
        relevant_evidence: List[RequirementEvidence],
    ) -> CandidateMatchAssessment:
        """
        Deterministic evidence-backed matching assessment with strict zero-hallucination:
        skills without resume evidence are marked status='not_found'.
        """
        from backend.app.matching.experience_matcher import ExperienceMatcher
        from backend.app.matching.skill_matcher import SkillMatcher

        skill_score, matching_skills, missing_req, missing_pref = SkillMatcher.match_skills(resume, job)
        exp_score, exp_gap = ExperienceMatcher.match_experience(resume, job)

        matched_by_name = {m.skill.lower(): m for m in matching_skills}
        missing_req_names = {m.skill.lower() for m in missing_req}

        required_assessments: List[SkillEvidenceAssessment] = []
        for req in job.required_skills:
            key = req.lower()
            if key in matched_by_name:
                m = matched_by_name[key]
                required_assessments.append(
                    SkillEvidenceAssessment(
                        skill=m.skill,
                        status="strong",
                        evidence=m.evidence,
                        confidence=0.9,
                    )
                )
            else:
                required_assessments.append(
                    SkillEvidenceAssessment(
                        skill=req,
                        status="not_found",
                        evidence="",
                        confidence=0.0,
                    )
                )

        # Include any normalized matches missed by raw key lookup
        seen_req = {a.skill.lower() for a in required_assessments}
        for m in matching_skills:
            if m.skill.lower() not in seen_req and m.skill.lower() not in {p.lower() for p in job.preferred_skills}:
                required_assessments.append(
                    SkillEvidenceAssessment(
                        skill=m.skill,
                        status="strong",
                        evidence=m.evidence,
                        confidence=0.9,
                    )
                )

        preferred_assessments: List[SkillEvidenceAssessment] = []
        for pref in job.preferred_skills:
            key = pref.lower()
            if key in matched_by_name:
                m = matched_by_name[key]
                preferred_assessments.append(
                    SkillEvidenceAssessment(
                        skill=m.skill,
                        status="strong",
                        evidence=m.evidence,
                        confidence=0.85,
                    )
                )
            else:
                preferred_assessments.append(
                    SkillEvidenceAssessment(
                        skill=pref,
                        status="not_found",
                        evidence="",
                        confidence=0.0,
                    )
                )

        matched_resp = [
            ev.requirement for ev in relevant_evidence if ev.match_status in ("Strong match", "Partial match")
        ]
        missing_resp = [
            ev.requirement for ev in relevant_evidence if ev.match_status == "Not found"
        ]
        resp_evidence = [
            ev.evidence for ev in relevant_evidence if ev.match_status in ("Strong match", "Partial match")
        ]
        if matched_resp and not missing_resp:
            resp_status = "strong"
        elif matched_resp:
            resp_status = "partial"
        else:
            resp_status = "not_found"

        combined_ratio = (skill_score * 0.65 + exp_score * 0.35) / 100.0
        if combined_ratio >= 0.80 and not missing_req_names:
            recommendation = "strong_match"
        elif combined_ratio >= 0.60:
            recommendation = "moderate_match"
        elif combined_ratio >= 0.40:
            recommendation = "weak_match"
        else:
            recommendation = "not_recommended"

        return CandidateMatchAssessment(
            candidate_id=candidate_id,
            required_skill_assessment=required_assessments,
            preferred_skill_assessment=preferred_assessments,
            experience_assessment=ExperienceAssessmentSummary(
                relevant_years=exp_gap.candidate_years,
                required_years=exp_gap.required_years,
                summary=exp_gap.details,
                evidence=[f"{e.role} at {e.company} ({e.duration or e.start_date})" for e in resume.experience[:3]],
                status="strong" if exp_score >= 85 else ("partial" if exp_score >= 55 else "not_found"),
            ),
            responsibility_match=ResponsibilityMatchSummary(
                matched_responsibilities=matched_resp,
                missing_responsibilities=missing_resp,
                evidence=resp_evidence[:5],
                status=resp_status,
            ),
            seniority_match=SeniorityMatchSummary(
                target_level=exp_gap.role_level_match,
                candidate_level=resume.experience[0].role if resume.experience else "Unspecified",
                status="strong" if not exp_gap.gaps else "partial",
                evidence=resume.experience[0].role if resume.experience else "",
            ),
            missing_requirements=[m.skill for m in missing_req],
            contradictions=list(exp_gap.gaps),
            recommendation=recommendation,
            confidence=round(min(0.95, max(0.2, combined_ratio)), 2),
            provider=self.provider_name,
            model=self.model_name,
        )

    def rerank_candidate(
        self,
        candidate_summary: Dict[str, Any],
        job_summary: Dict[str, Any],
    ) -> CandidateRerankResult:
        score = float(candidate_summary.get("preliminary_score", 0.0))
        matched = list(candidate_summary.get("matched_skills") or [])
        missing = list(candidate_summary.get("missing_skills") or [])
        exp_years = candidate_summary.get("experience_years")

        if score >= 80.0 and not missing:
            classification = "STRONG_MATCH"
        elif score >= 65.0:
            classification = "GOOD_MATCH"
        elif score >= 45.0:
            classification = "PARTIAL_MATCH"
        else:
            classification = "WEAK_MATCH"

        strengths = []
        if matched:
            strengths.append(f"Demonstrates core skills: {', '.join(matched[:4])}")
        if exp_years is not None:
            strengths.append(f"Approximately {exp_years} years of experience")

        gaps = [f"No evidence found for {skill}" for skill in missing[:3]]
        evidence = list(candidate_summary.get("evidence_snippets") or [])[:3]

        return CandidateRerankResult(
            classification=classification,
            confidence=round(min(0.95, max(0.25, score / 100.0)), 2),
            strengths=strengths,
            gaps=gaps,
            evidence=evidence,
        )

