from backend.app.matching.normalizer import SkillNormalizer
from backend.app.matching.skill_matcher import SkillMatcher
from backend.app.schemas.resume import StructuredResume, ExperienceItem
from backend.app.schemas.job import StructuredJob


def test_skill_normalization():
    canonical, cat = SkillNormalizer.normalize_skill("Postgres")
    assert canonical == "PostgreSQL"
    assert cat == "Databases"

    canonical, cat = SkillNormalizer.normalize_skill("postgresql db")
    assert canonical == "PostgreSQL"

    canonical, cat = SkillNormalizer.normalize_skill("k8s")
    assert canonical == "Kubernetes"
    assert cat == "DevOps"

    canonical, cat = SkillNormalizer.normalize_skill("fast-api")
    assert canonical == "FastAPI"
    assert cat == "Frameworks"


def test_skill_matcher_scoring():
    resume = StructuredResume(
        name="Alex Dev",
        skills=["Python", "FastAPI", "Postgres", "Docker"],
        experience=[
            ExperienceItem(
                company="TechCorp",
                role="Backend Engineer",
                responsibilities=["Developed microservices with FastAPI and PostgreSQL."],
                technologies=["FastAPI", "Python", "PostgreSQL"],
            )
        ],
    )
    job = StructuredJob(
        job_title="Backend Developer",
        required_skills=["Python", "PostgreSQL", "Docker"],
        preferred_skills=["AWS", "Redis"],
    )

    score, matching, missing_req, missing_pref = SkillMatcher.match_skills(resume, job)

    # All 3 required skills matched!
    assert len(matching) >= 3
    matched_names = [m.skill for m in matching]
    assert "Python" in matched_names
    assert "PostgreSQL" in matched_names
    assert "Docker" in matched_names

    # Missing required should be empty
    assert len(missing_req) == 0

    # Missing preferred should contain AWS and Redis
    pref_missing_names = [m.skill for m in missing_pref]
    assert "AWS" in pref_missing_names
    assert "Redis" in pref_missing_names

    # Score should reflect 100% of required (0.75 * 100 = 75.0)
    assert score == 75.0

