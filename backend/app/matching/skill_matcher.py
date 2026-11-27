import re
from typing import List, Dict, Any, Tuple
from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.analysis import SkillMatchItem, MissingSkillItem
from backend.app.matching.normalizer import SkillNormalizer


class SkillMatcher:
    @staticmethod
    def _find_evidence(skill_canonical: str, resume: StructuredResume) -> str:
        """Find where in the resume the skill is demonstrated."""
        skill_lower = skill_canonical.lower()

        # Check in experience responsibilities
        for exp in resume.experience:
            for resp in exp.responsibilities + exp.achievements:
                if re.search(rf"\b{re.escape(skill_lower)}\b", resp.lower()):
                    return f"{exp.role} at {exp.company}: \"{resp}\""

        # Check in projects
        for proj in resume.projects:
            if any(re.search(rf"\b{re.escape(skill_lower)}\b", t.lower()) for t in proj.technologies):
                return f"Project '{proj.name}': {proj.description}"
            for ach in proj.achievements:
                if re.search(rf"\b{re.escape(skill_lower)}\b", ach.lower()):
                    return f"Project '{proj.name}': \"{ach}\""

        # Check in skills list
        return f"Listed in candidate's Technical Skills section."

    @classmethod
    def match_skills(
        cls,
        resume: StructuredResume,
        job: StructuredJob,
    ) -> Tuple[float, List[SkillMatchItem], List[MissingSkillItem], List[MissingSkillItem]]:
        """
        Compare resume skills with job required and preferred skills.
        Returns:
            (score: 0-100, matching_skills, missing_required_skills, missing_preferred_skills)
        """
        # Normalize all candidate skills
        candidate_normalized = {}
        for skill in (
            resume.skills
            + resume.technical_skills
            + resume.programming_languages
            + resume.frameworks
            + resume.databases
            + resume.cloud
            + resume.tools
        ):
            can_name, category = SkillNormalizer.normalize_skill(skill)
            candidate_normalized[can_name.lower()] = (can_name, category)

        # Normalize required job skills
        required_job_skills = {}
        for s in job.required_skills:
            can_name, cat = SkillNormalizer.normalize_skill(s)
            required_job_skills[can_name.lower()] = (can_name, cat)

        # Normalize preferred job skills
        preferred_job_skills = {}
        for s in job.preferred_skills:
            can_name, cat = SkillNormalizer.normalize_skill(s)
            if can_name.lower() not in required_job_skills:
                preferred_job_skills[can_name.lower()] = (can_name, cat)

        # Compute matches
        matching_skills: List[SkillMatchItem] = []
        missing_required: List[MissingSkillItem] = []
        missing_preferred: List[MissingSkillItem] = []

        req_matched_count = 0
        pref_matched_count = 0

        # Check required skills
        for key, (can_name, cat) in required_job_skills.items():
            if key in candidate_normalized:
                req_matched_count += 1
                evidence = cls._find_evidence(can_name, resume)
                matching_skills.append(
                    SkillMatchItem(
                        skill=can_name,
                        category=cat,
                        match_type="normalized_match",
                        evidence=evidence,
                    )
                )
            else:
                missing_required.append(
                    MissingSkillItem(
                        skill=can_name,
                        importance="required",
                        category=cat,
                        suggestion=f"Highlight '{can_name}' in projects or experience if you have relevant proficiency.",
                    )
                )

        # Check preferred skills
        for key, (can_name, cat) in preferred_job_skills.items():
            if key in candidate_normalized:
                pref_matched_count += 1
                evidence = cls._find_evidence(can_name, resume)
                matching_skills.append(
                    SkillMatchItem(
                        skill=can_name,
                        category=cat,
                        match_type="normalized_match",
                        evidence=evidence,
                    )
                )
            else:
                missing_preferred.append(
                    MissingSkillItem(
                        skill=can_name,
                        importance="preferred",
                        category=cat,
                        suggestion=f"Consider mentioning '{can_name}' to gain an advantage over standard candidates.",
                    )
                )

        # Deterministic scoring:
        # If required skills exist: 75% required coverage + 25% preferred coverage
        # If no preferred skills: 100% required coverage
        total_req = len(required_job_skills)
        total_pref = len(preferred_job_skills)

        if total_req > 0 and total_pref > 0:
            req_ratio = req_matched_count / total_req
            pref_ratio = pref_matched_count / total_pref
            skill_score = (req_ratio * 0.75 + pref_ratio * 0.25) * 100.0
        elif total_req > 0:
            skill_score = (req_matched_count / total_req) * 100.0
        elif total_pref > 0:
            skill_score = (pref_matched_count / total_pref) * 100.0
        else:
            skill_score = 80.0  # Baseline when job has no explicit skills listed

        return round(skill_score, 2), matching_skills, missing_required, missing_preferred

