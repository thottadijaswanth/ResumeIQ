from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob


class EducationMatcher:
    DEGREE_HIERARCHY = {
        "phd": 4,
        "doctorate": 4,
        "master": 3,
        "m.s.": 3,
        "mba": 3,
        "bachelor": 2,
        "b.s.": 2,
        "b.a.": 2,
        "b.tech": 2,
        "associate": 1,
    }

    @classmethod
    def match_education(cls, resume: StructuredResume, job: StructuredJob) -> float:
        """
        Compare education degree levels.
        Returns education score (0-100).
        """
        if not job.education_requirements:
            return 95.0

        # Determine target requirement level
        target_level = 2  # Default to Bachelor
        req_text = " ".join(job.education_requirements).lower()
        for deg, lvl in cls.DEGREE_HIERARCHY.items():
            if deg in req_text:
                target_level = max(target_level, lvl)

        # Determine candidate highest level
        candidate_level = 0
        for edu in resume.education:
            deg_lower = edu.degree.lower()
            for deg, lvl in cls.DEGREE_HIERARCHY.items():
                if deg in deg_lower:
                    candidate_level = max(candidate_level, lvl)

        if candidate_level >= target_level:
            return 100.0
        elif candidate_level == target_level - 1:
            return 85.0
        elif candidate_level > 0:
            return 70.0
        else:
            # If candidate has projects and experience, don't zero them out
            return 60.0

