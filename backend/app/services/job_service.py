import re
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.ai import LocalDeterministicEmbeddingProvider, get_embedding_provider, run_with_ai_fallback
from backend.app.config import settings
from backend.app.matching.normalizer import SKILL_ALIASES, SkillNormalizer
from backend.app.matching.semantic_matcher import SemanticMatcher
from backend.app.models.job import Job, JobEmbedding
from backend.app.repositories.job_repository import job_repository
from backend.app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobUpdate,
    StructuredJob,
)
from backend.app.utils.logger import logger


def _extract_skills_from_text(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    seen = set()
    for alias, (canonical, _) in SKILL_ALIASES.items():
        pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
        if re.search(pattern, text_lower) and canonical.lower() not in seen:
            seen.add(canonical.lower())
            found.append(canonical)
    return found


def _normalize_skill_list(skills: List[str]) -> List[str]:
    normalized = []
    seen = set()
    for raw in skills:
        clean = raw.strip()
        if not clean:
            continue
        canonical, _ = SkillNormalizer.normalize_skill(clean)
        key = canonical.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(canonical)
    return normalized


class JobService:
    @staticmethod
    def create_job(db: Session, user_id: str, job_in: JobCreate) -> JobResponse:
        structured_data = job_in.structured_data

        # Extract deterministically first if structured fields provided by recruiter,
        # or run AI extraction only when structured fields are absent.
        has_explicit_skills = bool(job_in.required_skills or job_in.preferred_skills)
        if not structured_data:
            if has_explicit_skills:
                req_skills = _normalize_skill_list(job_in.required_skills)
                pref_skills = _normalize_skill_list(job_in.preferred_skills)
                structured_data = StructuredJob(
                    job_title=job_in.title.strip(),
                    company=job_in.company.strip(),
                    location=(job_in.location or "").strip(),
                    work_mode=job_in.work_mode,
                    min_experience=job_in.min_experience,
                    max_experience=job_in.max_experience,
                    employment_type=job_in.employment_type,
                    notice_period=job_in.notice_period,
                    required_skills=req_skills,
                    preferred_skills=pref_skills,
                    years_of_experience=job_in.min_experience,
                    education_requirements=[e.strip() for e in job_in.education_requirements if e.strip()],
                    responsibilities=[r.strip() for r in job_in.responsibilities if r.strip()],
                    qualifications=[q.strip() for q in job_in.qualifications if q.strip()],
                    keywords=list(dict.fromkeys(req_skills + pref_skills)),
                )
            else:
                try:
                    structured_data, _ = run_with_ai_fallback(
                        "extract_structured_job",
                        lambda provider: provider.extract_structured_job(job_in.description),
                    )
                except Exception as exc:
                    logger.warning(
                        f"AI job extraction skipped ({type(exc).__name__}); using deterministic extractor."
                    )
                    inferred_skills = _extract_skills_from_text(job_in.description)
                    exp_match = re.search(
                        r"(\d+(?:\.\d+)?)\+?\s*(?:-\s*(\d+(?:\.\d+)?))?\s*years?(?:\s*of)?\s*experience",
                        job_in.description,
                        re.IGNORECASE,
                    )
                    min_exp = float(exp_match.group(1)) if exp_match else None
                    max_exp = float(exp_match.group(2)) if (exp_match and exp_match.group(2)) else None
                    structured_data = StructuredJob(
                        job_title=job_in.title.strip(),
                        company=job_in.company.strip(),
                        location=(job_in.location or "").strip(),
                        work_mode=job_in.work_mode,
                        min_experience=min_exp,
                        max_experience=max_exp,
                        years_of_experience=min_exp,
                        required_skills=inferred_skills,
                        keywords=inferred_skills,
                    )

        # Recruiter-entered fields always take precedence
        structured_data.job_title = job_in.title.strip() or structured_data.job_title
        structured_data.company = job_in.company.strip() or structured_data.company
        if job_in.location is not None:
            structured_data.location = job_in.location.strip()
        structured_data.work_mode = job_in.work_mode or structured_data.work_mode or "Hybrid"

        if job_in.min_experience is not None:
            structured_data.min_experience = job_in.min_experience
            structured_data.years_of_experience = job_in.min_experience
        elif structured_data.min_experience is None:
            structured_data.min_experience = structured_data.years_of_experience

        if job_in.max_experience is not None:
            structured_data.max_experience = job_in.max_experience
        if job_in.employment_type:
            structured_data.employment_type = job_in.employment_type.strip()
        if job_in.notice_period:
            structured_data.notice_period = job_in.notice_period.strip()
        if job_in.required_skills:
            structured_data.required_skills = _normalize_skill_list(job_in.required_skills)
        if job_in.preferred_skills:
            structured_data.preferred_skills = _normalize_skill_list(job_in.preferred_skills)
        if job_in.education_requirements:
            structured_data.education_requirements = [
                e.strip() for e in job_in.education_requirements if e.strip()
            ]
        if job_in.responsibilities:
            structured_data.responsibilities = [
                r.strip() for r in job_in.responsibilities if r.strip()
            ]
        if job_in.qualifications:
            structured_data.qualifications = [
                q.strip() for q in job_in.qualifications if q.strip()
            ]
        if not structured_data.keywords:
            structured_data.keywords = list(
                dict.fromkeys(structured_data.required_skills + structured_data.preferred_skills)
            )

        db_job = Job(
            user_id=user_id,
            title=structured_data.job_title,
            company=structured_data.company,
            location=structured_data.location or job_in.location,
            work_mode=structured_data.work_mode,
            min_experience=structured_data.min_experience,
            max_experience=structured_data.max_experience,
            required_skills=structured_data.required_skills,
            preferred_skills=structured_data.preferred_skills,
            education_requirements=structured_data.education_requirements,
            employment_type=structured_data.employment_type,
            notice_period=structured_data.notice_period,
            location_required=job_in.location_required,
            description=job_in.description.strip(),
            structured_data=structured_data.model_dump(),
        )
        created_job = job_repository.create(db, db_job)

        # Generate and store chunk + combined vector embeddings once per job
        try:
            embedder = get_embedding_provider()
            chunks = SemanticMatcher.chunk_job(structured_data)
            combined_text = (
                f"{structured_data.job_title} {structured_data.work_mode} {structured_data.location}. "
                f"Required: {', '.join(structured_data.required_skills)}. "
                f"Preferred: {', '.join(structured_data.preferred_skills)}. "
                f"{job_in.description[:1500]}"
            )
            chunks.append(("combined", combined_text))
            chunk_texts = [c[1] for c in chunks]
            try:
                embedder = get_embedding_provider()
                embeddings_vectors = embedder.get_embeddings(chunk_texts)
            except Exception as emb_exc:
                logger.warning(
                    f"Job embedding API unavailable ({type(emb_exc).__name__}); using local embeddings."
                )
                embeddings_vectors = LocalDeterministicEmbeddingProvider(
                    dim=settings.EMBEDDING_DIMENSIONS
                ).get_embeddings(chunk_texts)
            db_embeddings = [
                JobEmbedding(
                    job_id=created_job.id,
                    chunk_type=chunks[i][0],
                    chunk_text=chunks[i][1],
                    embedding=embeddings_vectors[i],
                    embedding_metadata={"chunk_index": i},
                )
                for i in range(len(chunks))
            ]
            job_repository.add_embeddings(db, db_embeddings)
        except Exception as e:
            logger.warning(f"Error generating embeddings for job {created_job.id}: {e}")

        return JobResponse.model_validate(created_job)

    @staticmethod
    def get_user_jobs(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[JobListResponse]:
        jobs = job_repository.get_user_jobs(db, user_id, skip=skip, limit=limit)
        return [JobListResponse.model_validate(j) for j in jobs]

    @staticmethod
    def get_job_by_id(db: Session, user_id: str, job_id: str) -> JobResponse:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
        return JobResponse.model_validate(job)

    @staticmethod
    def update_job(db: Session, user_id: str, job_id: str, update_data: JobUpdate) -> JobResponse:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        if update_data.title:
            job.title = update_data.title.strip()
        if update_data.company:
            job.company = update_data.company.strip()
        if update_data.location is not None:
            job.location = update_data.location.strip()
        if update_data.work_mode is not None:
            job.work_mode = update_data.work_mode
        if update_data.min_experience is not None:
            job.min_experience = update_data.min_experience
        if update_data.max_experience is not None:
            job.max_experience = update_data.max_experience
        if update_data.required_skills is not None:
            job.required_skills = _normalize_skill_list(update_data.required_skills)
        if update_data.preferred_skills is not None:
            job.preferred_skills = _normalize_skill_list(update_data.preferred_skills)
        if update_data.education_requirements is not None:
            job.education_requirements = update_data.education_requirements
        if update_data.employment_type is not None:
            job.employment_type = update_data.employment_type
        if update_data.notice_period is not None:
            job.notice_period = update_data.notice_period
        if update_data.location_required is not None:
            job.location_required = update_data.location_required
        if update_data.description:
            job.description = update_data.description.strip()
        if update_data.structured_data:
            job.structured_data = update_data.structured_data.model_dump()

        updated = job_repository.update(db, job)
        return JobResponse.model_validate(updated)

    @staticmethod
    def delete_job(db: Session, user_id: str, job_id: str) -> bool:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
        return job_repository.delete(db, job_id)


job_service = JobService()
