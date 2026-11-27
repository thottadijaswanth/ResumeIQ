from backend.app.matching.scoring_engine import ScoringEngine
from backend.app.schemas.resume import (
    StructuredResume,
    ExperienceItem,
    EducationItem,
    ProjectItem,
)
from backend.app.schemas.job import StructuredJob


def test_scoring_engine_deterministic_calculation():
    resume = StructuredResume(
        name="Jordan Lee",
        email="jordan@example.com",
        phone="555-0199",
        summary="Senior Backend Engineer with 5+ years experience building cloud services.",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        experience=[
            ExperienceItem(
                company="InnoTech",
                role="Senior Backend Engineer",
                start_date="2020",
                end_date="Present",
                duration="4 years",
                responsibilities=[
                    "Engineered distributed REST APIs with FastAPI, handling 15,000 req/s.",
                    "Optimized PostgreSQL queries, decreasing p99 latency by 40%.",
                ],
                achievements=["Increased system uptime to 99.99%."],
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker"],
            )
        ],
        education=[
            EducationItem(
                institution="State University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
            )
        ],
        projects=[
            ProjectItem(
                name="API Gateway",
                description="High throughput gateway service.",
                technologies=["Python", "Docker"],
            )
        ],
    )

    job = StructuredJob(
        job_title="Senior Python Backend Engineer",
        company="Global SaaS Inc",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker", "AWS"],
        years_of_experience=4.0,
        responsibilities=[
            "Architect and maintain scalable backend microservices.",
            "Optimize database queries and schema designs.",
        ],
        qualifications=["4+ years building Python web applications."],
        keywords=["Python", "FastAPI", "PostgreSQL", "Microservices", "REST"],
    )

    analysis, recommendations = ScoringEngine.analyze_resume_against_job(
        resume=resume,
        job=job,
        raw_resume_text="Senior Backend Engineer Jordan Lee Python FastAPI PostgreSQL Docker",
    )

    # Deterministic checks
    assert 0.0 <= analysis.overall_score <= 100.0
    assert analysis.skill_score >= 80.0
    assert analysis.experience_score >= 80.0
    assert analysis.education_score >= 90.0
    assert analysis.ats_analysis.estimated_ats_score >= 60.0
    assert len(recommendations) > 0
    assert len(analysis.requirements_evidence) > 0
