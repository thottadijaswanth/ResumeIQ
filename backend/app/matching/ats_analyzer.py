import re
from typing import Dict, List, Tuple
from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.analysis import ATSAnalysis

# Recognized strong action verbs for tech resumes
STRONG_ACTION_VERBS = [
    "accelerated", "achieved", "administered", "architected", "automated", "built", "centralized",
    "collaborated", "configured", "consolidated", "converted", "created", "decreased", "delivered",
    "deployed", "designed", "developed", "devised", "eliminated", "enabled", "engineered", "enhanced",
    "established", "executed", "expanded", "expedited", "fabricated", "facilitated", "formulated",
    "generated", "guided", "implemented", "improved", "increased", "initiated", "integrated", "invented",
    "launched", "led", "managed", "maximized", "mentored", "migrated", "minimized", "modernized",
    "monitored", "negotiated", "optimized", "orchestrated", "overhauled", "pioneered", "planned",
    "reduced", "refactored", "resolved", "restructured", "scaled", "simplified", "spearheaded",
    "standardized", "streamlined", "strengthened", "transformed", "upgraded", "validated",
]


class ATSAnalyzer:
    @classmethod
    def analyze_ats(
        cls,
        resume: StructuredResume,
        job: StructuredJob,
        raw_resume_text: str = "",
    ) -> Tuple[float, ATSAnalysis]:
        """
        Calculates ATS compatibility heuristics.
        Returns (keyword_score: 0-100, ats_analysis: ATSAnalysis).
        """
        all_resume_text = (
            raw_resume_text
            + " "
            + resume.summary
            + " "
            + " ".join(resume.skills)
            + " "
            + " ".join(
                " ".join(e.responsibilities + e.achievements + e.technologies)
                for e in resume.experience
            )
            + " ".join(" ".join(p.technologies + p.achievements) for p in resume.projects)
        ).lower()

        # 1. Keyword coverage
        target_keywords = list(set([k.lower() for k in (job.keywords + job.required_skills + job.preferred_skills) if k]))
        matched_keywords = [k for k in target_keywords if re.search(rf"\b{re.escape(k)}\b", all_resume_text)]

        keyword_coverage = (
            round((len(matched_keywords) / len(target_keywords)) * 100.0, 1)
            if target_keywords
            else 85.0
        )

        # 2. Section completeness
        section_completeness = {
            "Contact Information": bool(resume.name and (resume.email or resume.phone)),
            "Professional Summary": bool(resume.summary and len(resume.summary) > 20),
            "Work Experience": bool(resume.experience and len(resume.experience) > 0),
            "Skills Inventory": bool(resume.skills and len(resume.skills) >= 3),
            "Education": bool(resume.education and len(resume.education) > 0),
            "Projects": bool(resume.projects and len(resume.projects) > 0),
        }

        # 3. Quantifiable achievements (numbers, %, $, x times)
        metric_matches = re.findall(
            r"(\b\d+(?:\.\d+)?%|\$\d+(?:,\d{3})*(?:\.\d+)?|\b\d+x\b|\b\d+\+?\s*(?:users|clients|ms|seconds|minutes|hours|req/s|rps|million|thousand|k\b))",
            all_resume_text,
            re.IGNORECASE,
        )
        quantifiable_count = len(metric_matches)

        # 4. Action verbs count
        action_verb_count = sum(1 for verb in STRONG_ACTION_VERBS if re.search(rf"\b{verb}\b", all_resume_text))

        # 5. Formatting risks & Keyword stuffing
        formatting_risks: List[str] = []
        if not resume.email:
            formatting_risks.append("Missing or unparseable email address.")
        if not resume.phone:
            formatting_risks.append("Missing phone number.")
        if len(resume.experience) == 0:
            formatting_risks.append("No work experience sections detected.")
        if quantifiable_count < 2:
            formatting_risks.append("Low frequency of quantifiable metrics and numerical impact.")

        # Check keyword stuffing (repeating same keyword > 12 times)
        keyword_stuffing = False
        for kw in target_keywords:
            if len(kw) > 3 and len(re.findall(rf"\b{re.escape(kw)}\b", all_resume_text)) > 12:
                keyword_stuffing = True
                formatting_risks.append(f"Excessive repetition of keyword '{kw}' detected (risk of spam penalty).")

        # 6. Strengths
        strengths: List[str] = []
        if keyword_coverage >= 70:
            strengths.append(f"Strong keyword alignment ({keyword_coverage}% coverage of target requirements).")
        if quantifiable_count >= 3:
            strengths.append(f"Effective use of quantifiable metrics ({quantifiable_count} metrics found).")
        if action_verb_count >= 5:
            strengths.append(f"Dynamic language with {action_verb_count} distinct action verbs.")
        if all(section_completeness.values()):
            strengths.append("Complete standard section structure (Contact, Summary, Experience, Skills, Education).")

        # Estimated ATS compatibility score:
        # 40% keyword coverage + 25% section completeness + 20% metrics + 15% action verbs
        complete_sections_ratio = sum(1 for v in section_completeness.values() if v) / len(section_completeness)
        metrics_score = min(100.0, quantifiable_count * 20.0)
        action_verb_score = min(100.0, action_verb_count * 15.0)

        estimated_ats = (
            keyword_coverage * 0.40
            + complete_sections_ratio * 100.0 * 0.25
            + metrics_score * 0.20
            + action_verb_score * 0.15
        )

        if keyword_stuffing:
            estimated_ats = max(20.0, estimated_ats - 15.0)

        estimated_ats_score = round(max(10.0, min(100.0, estimated_ats)), 1)
        summary = (
            f"Estimated ATS Compatibility: {estimated_ats_score}%. "
            f"The resume matches {len(matched_keywords)} of {len(target_keywords)} key terms "
            f"with {quantifiable_count} quantifiable metrics."
        )

        return (
            keyword_coverage,
            ATSAnalysis(
                estimated_ats_score=estimated_ats_score,
                keyword_coverage_percent=keyword_coverage,
                quantifiable_achievements_count=quantifiable_count,
                action_verbs_count=action_verb_count,
                section_completeness=section_completeness,
                formatting_risks=formatting_risks,
                keyword_stuffing_detected=keyword_stuffing,
                strengths=strengths,
                summary=summary,
            ),
        )

