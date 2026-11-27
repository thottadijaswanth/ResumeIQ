"""
Synthetic Demo Data Seeder for ResumeIQ.
Creates a demo user, 1 synthetic senior candidate resume, 2 realistic job postings,
runs an initial analysis, and creates tracked applications.

All data is strictly synthetic and generated for demonstration purposes.
"""

import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from backend.app.database.init_db import init_db
from backend.app.models import User, Resume, Job, Analysis, Application
from backend.app.utils.security import hash_password
from backend.app.matching.scoring_engine import ScoringEngine
from backend.app.schemas.resume import (
    StructuredResume,
    ExperienceItem,
    EducationItem,
    ProjectItem,
)
from backend.app.schemas.job import StructuredJob


def seed_data():
    db = SessionLocal()
    try:
        print("[1/5] Initializing database schema...")
        init_db()

        # 1. Create or retrieve demo user
        demo_email = "demo@resumeiq.io"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            print("[2/5] Creating demo user account...")
            user = User(
                email=demo_email,
                password_hash=hash_password("DemoPassword123!"),
                full_name="Jordan Lee (Synthetic Profile)",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"[2/5] Demo user already exists: {user.email}")

        # 2. Seed synthetic candidate resume
        resume_name = "Jordan Lee - Senior Backend Engineer"
        existing_resume = db.query(Resume).filter(Resume.user_id == user.id, Resume.name == resume_name).first()
        if not existing_resume:
            print("[3/5] Seeding synthetic candidate resume...")
            structured_resume = StructuredResume(
                name="Jordan Lee",
                email="jordan.lee.synthetic@example.com",
                phone="+1 (555) 019-2834",
                location="San Francisco, CA (Remote)",
                summary=(
                    "Senior Software Engineer with 5+ years of experience designing and scaling distributed "
                    "backend microservices, high-throughput REST APIs, and event-driven architectures. "
                    "Proficient in Python, FastAPI, PostgreSQL, Docker, and Kubernetes with a focus on p99 latency optimization."
                ),
                skills=[
                    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis",
                    "Git", "Linux", "CI/CD", "TypeScript", "REST APIs", "Microservices"
                ],
                technical_skills=[
                    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "TypeScript"
                ],
                programming_languages=["Python", "TypeScript", "SQL"],
                frameworks=["FastAPI", "React", "Next.js"],
                databases=["PostgreSQL", "Redis"],
                cloud=["AWS", "Docker", "Kubernetes"],
                tools=["Git", "GitHub Actions", "Linux"],
                experience=[
                    ExperienceItem(
                        company="HyperScale Cloud Systems",
                        role="Senior Backend Engineer",
                        start_date="2022",
                        end_date="Present",
                        duration="2.5 years",
                        responsibilities=[
                            "Architected resilient asynchronous microservices using Python and FastAPI, handling 18,000 requests/sec.",
                            "Optimized database access patterns in PostgreSQL, decreasing p99 read latencies by 42%.",
                            "Implemented Redis caching layer reducing database connection pool exhaustion by 60%.",
                        ],
                        achievements=[
                            "Maintained 99.99% system availability throughout Q3 traffic spikes.",
                            "Mentored 4 software engineers on code review best practices and test automation.",
                        ],
                        technologies=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
                    ),
                    ExperienceItem(
                        company="DataFlow Infrastructure",
                        role="Software Engineer",
                        start_date="2019",
                        end_date="2022",
                        duration="3 years",
                        responsibilities=[
                            "Developed RESTful backend API integrations serving 250,000 monthly active users.",
                            "Containerized legacy monolith services into Docker containers and automated CI/CD pipelines.",
                        ],
                        achievements=[
                            "Reduced deployment cycle duration from 45 minutes to 6 minutes using GitHub Actions.",
                        ],
                        technologies=["Python", "PostgreSQL", "Docker", "Git", "Linux"],
                    ),
                ],
                education=[
                    EducationItem(
                        institution="University of California, Berkeley",
                        degree="Bachelor of Science",
                        field_of_study="Computer Science",
                        start_date="2015",
                        end_date="2019",
                        gpa="3.85",
                    )
                ],
                projects=[
                    ProjectItem(
                        name="Distributed Rate Limiter Service",
                        description="Token bucket algorithm implementation backed by Redis clusters with sub-millisecond evaluation times.",
                        technologies=["Python", "FastAPI", "Redis", "Docker"],
                        achievements=["Benchmarked to handle 40,000 evaluations per second per node."],
                        links=["https://github.com/example/rate-limiter"],
                    )
                ],
                certifications=["AWS Certified Solutions Architect - Associate"],
                achievements=["Published open-source library with 1,200+ GitHub stars."],
                languages=["English"],
            )

            existing_resume = Resume(
                user_id=user.id,
                name=resume_name,
                original_filename="jordan_lee_senior_engineer.pdf",
                file_type="pdf",
                file_size=42800,
                raw_text=structured_resume.summary + "\n" + " ".join(structured_resume.skills),
                structured_data=structured_resume.model_dump(),
            )
            db.add(existing_resume)
            db.commit()
            db.refresh(existing_resume)

        # 3. Seed realistic job postings
        print("[4/5] Seeding target job descriptions...")
        job_1_title = "Senior Python Backend Engineer"
        job_1 = db.query(Job).filter(Job.user_id == user.id, Job.title == job_1_title).first()
        if not job_1:
            job_1_struct = StructuredJob(
                job_title=job_1_title,
                company="NextStream Technologies",
                location="Remote (US / Canada)",
                required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                preferred_skills=["Kubernetes", "Redis", "AWS", "Kafka"],
                programming_languages=["Python", "SQL"],
                frameworks=["FastAPI"],
                databases=["PostgreSQL", "Redis"],
                cloud=["AWS", "Docker", "Kubernetes"],
                tools=["Git", "Linux"],
                years_of_experience=4.0,
                education_requirements=["Bachelor's degree in Computer Science or equivalent practical experience"],
                responsibilities=[
                    "Design, implement, and maintain high-throughput backend services and RESTful APIs.",
                    "Collaborate with front-end engineers, data engineers, and product teams on architecture.",
                    "Champion high test coverage, code quality, automated CI/CD, and system observability.",
                ],
                qualifications=[
                    "4+ years of professional experience building web backends in Python.",
                    "Strong background in relational database modeling (PostgreSQL) and caching strategies.",
                    "Familiarity with containerized workflows using Docker and Kubernetes.",
                ],
                keywords=["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Microservices", "REST"],
            )
            job_1 = Job(
                user_id=user.id,
                title=job_1_title,
                company="NextStream Technologies",
                location="Remote (US / Canada)",
                description=(
                    "NextStream is hiring a Senior Python Backend Engineer to scale our core data APIs.\n\n"
                    "Requirements:\n"
                    "- 4+ years software engineering experience with Python\n"
                    "- Deep proficiency in FastAPI, PostgreSQL, and Docker\n"
                    "- Preferred: Redis caching, Kubernetes, AWS infrastructure\n"
                ),
                structured_data=job_1_struct.model_dump(),
            )
            db.add(job_1)
            db.commit()
            db.refresh(job_1)

        job_2_title = "Full-Stack AI Platform Engineer"
        job_2 = db.query(Job).filter(Job.user_id == user.id, Job.title == job_2_title).first()
        if not job_2:
            job_2_struct = StructuredJob(
                job_title=job_2_title,
                company="Nexus AI Labs",
                location="San Francisco, CA / Hybrid",
                required_skills=["Python", "TypeScript", "React", "Docker"],
                preferred_skills=["FastAPI", "Next.js", "PyTorch", "PostgreSQL"],
                programming_languages=["Python", "TypeScript"],
                frameworks=["React", "FastAPI", "Next.js"],
                databases=["PostgreSQL"],
                cloud=["AWS", "Docker"],
                tools=["Git"],
                years_of_experience=3.0,
                education_requirements=["Bachelor's degree in Computer Science or related STEM field"],
                responsibilities=[
                    "Build responsive user interfaces in Next.js paired with Python backend services.",
                    "Integrate LLM API workflows and vector search pipelines into interactive customer applications.",
                ],
                qualifications=[
                    "3+ years building full-stack applications with TypeScript and Python.",
                    "Proven track record delivering reliable frontend and backend features.",
                ],
                keywords=["Python", "TypeScript", "React", "Next.js", "Docker", "Vector Search"],
            )
            job_2 = Job(
                user_id=user.id,
                title=job_2_title,
                company="Nexus AI Labs",
                location="San Francisco, CA / Hybrid",
                description=(
                    "Nexus AI Labs is looking for a Full-Stack AI Platform Engineer.\n\n"
                    "Requirements:\n"
                    "- 3+ years experience with Python and TypeScript\n"
                    "- Experience building modern React/Next.js interfaces\n"
                    "- Solid backend API experience\n"
                ),
                structured_data=job_2_struct.model_dump(),
            )
            db.add(job_2)
            db.commit()
            db.refresh(job_2)

        # 4. Generate match analysis between candidate resume and Job 1
        print("[5/5] Generating initial match analysis and applications...")
        analysis = db.query(Analysis).filter(Analysis.user_id == user.id, Analysis.job_id == job_1.id).first()
        if not analysis:
            struct_resume = StructuredResume.model_validate(existing_resume.structured_data)
            struct_job = StructuredJob.model_validate(job_1.structured_data)

            analysis_result, recommendations = ScoringEngine.analyze_resume_against_job(
                resume=struct_resume,
                job=struct_job,
                raw_resume_text=existing_resume.raw_text,
            )

            analysis = Analysis(
                user_id=user.id,
                resume_id=existing_resume.id,
                job_id=job_1.id,
                overall_score=analysis_result.overall_score,
                skill_score=analysis_result.skill_score,
                experience_score=analysis_result.experience_score,
                education_score=analysis_result.education_score,
                keyword_score=analysis_result.keyword_score,
                semantic_score=analysis_result.semantic_score,
                analysis_result=analysis_result.model_dump(),
                recommendations=[r.model_dump() for r in recommendations],
            )
            db.add(analysis)
            db.commit()

        # 5. Seed sample tracked applications
        app_1 = db.query(Application).filter(Application.user_id == user.id, Application.job_id == job_1.id).first()
        if not app_1:
            app_1 = Application(
                user_id=user.id,
                job_id=job_1.id,
                resume_id=existing_resume.id,
                status="Interview",
                notes="Technical interview completed with VP of Engineering. System design screen next.",
            )
            db.add(app_1)

        app_2 = db.query(Application).filter(Application.user_id == user.id, Application.job_id == job_2.id).first()
        if not app_2:
            app_2 = Application(
                user_id=user.id,
                job_id=job_2.id,
                resume_id=existing_resume.id,
                status="Applied",
                notes="Tailored resume and cover letter submitted via career portal.",
            )
            db.add(app_2)

        db.commit()
        print("\n✨ Synthetic Demo Data successfully seeded!")
        print(f"   Demo Credentials -> Email: {demo_email} | Password: DemoPassword123!")
        print(f"   Seeded Resume    -> {existing_resume.name}")
        print(f"   Seeded Jobs      -> '{job_1.title}' & '{job_2.title}'")
        print(f"   Sample Match     -> {analysis.overall_score}% match score\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
