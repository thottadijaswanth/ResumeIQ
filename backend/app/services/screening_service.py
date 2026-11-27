import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.ai import (
    LocalDeterministicEmbeddingProvider,
    cosine_similarity,
    get_ai_provider,
    get_embedding_provider,
    get_fallback_ai_provider,
)
from backend.app.config import settings
from backend.app.database.session import SessionLocal
from backend.app.matching.ats_analyzer import ATSAnalyzer
from backend.app.matching.education_matcher import EducationMatcher
from backend.app.matching.experience_matcher import ExperienceMatcher
from backend.app.matching.fast_extractor import classify_match
from backend.app.matching.skill_matcher import SkillMatcher
from backend.app.models.analysis import Analysis
from backend.app.models.job import Job, JobEmbedding
from backend.app.models.resume import Resume
from backend.app.models.screening import ScreeningRun
from backend.app.repositories.analysis_repository import analysis_repository
from backend.app.repositories.job_repository import job_repository
from backend.app.repositories.resume_repository import resume_repository
from backend.app.repositories.screening_repository import screening_repository
from backend.app.schemas.analysis import (
    AnalysisResultData,
    CandidateDetailResponse,
    CandidateRankItem,
    CandidateRerankResult,
    RecommendationItem,
    RequirementEvidence,
    ScreeningRunRequest,
    ScreeningRunResponse,
)
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.resume import StructuredResume
from backend.app.utils.logger import logger

_CLASSIFICATION_PRIORITY = {
    "STRONG_MATCH": 4,
    "GOOD_MATCH": 3,
    "PARTIAL_MATCH": 2,
    "WEAK_MATCH": 1,
}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _evaluate_hard_filters(
    resume: Resume,
    structured_resume: StructuredResume,
    candidate_years: float,
    job: Job,
    structured_job: StructuredJob,
) -> Tuple[bool, List[str]]:
    """
    Fast deterministic filtering:
    - Experience range check against min_experience / max_experience.
    - Work mode & location alignment (missing candidate location -> 'Unknown', not rejected unless required).
    """
    notes: List[str] = []
    passed = True

    min_exp = job.min_experience if job.min_experience is not None else structured_job.min_experience
    max_exp = job.max_experience if job.max_experience is not None else structured_job.max_experience

    if min_exp is not None and min_exp > 0 and candidate_years < min_exp:
        passed = False
        if candidate_years <= 0.0:
            notes.append(
                f"No verified work or internship experience timeline found (minimum {min_exp} yrs required)"
            )
        else:
            notes.append(
                f"Verified experience timeline ({candidate_years} yrs) is below {min_exp} yr minimum"
            )
    elif max_exp is not None and candidate_years > (max_exp + 4.0):
        notes.append(f"Experience {candidate_years} yrs exceeds {max_exp} yr target range")

    work_mode = (job.work_mode or structured_job.work_mode or "Hybrid").lower()
    job_loc = (job.location or structured_job.location or "").strip().lower()
    cand_loc = (resume.candidate_location or structured_resume.location or "Unknown").strip()
    cand_loc_lower = cand_loc.lower()

    if work_mode != "remote" and job_loc and job_loc not in ("anywhere", "remote"):
        if cand_loc_lower in ("", "unknown", "remote / hybrid"):
            if job.location_required:
                passed = False
                notes.append(f"Location is Unknown (hard requirement: {job.location})")
            else:
                notes.append("Candidate location: Unknown")
        else:
            job_city = job_loc.split(",")[0].strip()
            if job_city and job_city not in cand_loc_lower and "remote" not in cand_loc_lower:
                if job.location_required:
                    passed = False
                notes.append(f"Location '{cand_loc}' differs from '{job.location or structured_job.location}' ({job.work_mode})")

    return passed, notes


def _get_or_create_job_embedding(db: Session, job: Job, structured_job: StructuredJob) -> List[float]:
    embeddings = job_repository.get_embeddings(db, job.id)
    for emb in embeddings:
        if emb.chunk_type == "combined" and emb.embedding:
            return emb.embedding
    if embeddings and embeddings[0].embedding:
        return embeddings[0].embedding

    combined_text = (
        f"{structured_job.job_title} {structured_job.work_mode} {structured_job.location}. "
        f"Required: {', '.join(structured_job.required_skills)}. {job.description[:1500]}"
    )
    try:
        embedder = get_embedding_provider()
        vec = embedder.get_embedding(combined_text)
    except Exception:
        vec = LocalDeterministicEmbeddingProvider(dim=settings.EMBEDDING_DIMENSIONS).get_embedding(
            combined_text
        )
    job_repository.add_embeddings(
        db,
        [
            JobEmbedding(
                job_id=job.id,
                chunk_type="combined",
                chunk_text=combined_text,
                embedding=vec,
                embedding_metadata={"chunk_index": 0},
            )
        ],
    )
    return vec


def _get_or_compute_resume_embedding(db: Session, resume: Resume, structured_resume: StructuredResume) -> List[float]:
    if resume.combined_embedding:
        return resume.combined_embedding
    summary = (
        f"{structured_resume.summary} Skills: {', '.join(structured_resume.skills)}. "
        f"{resume.raw_text[:1200]}"
    )
    try:
        embedder = get_embedding_provider()
        vec = embedder.get_embedding(summary)
    except Exception:
        vec = LocalDeterministicEmbeddingProvider(dim=settings.EMBEDDING_DIMENSIONS).get_embedding(
            summary
        )
    resume.combined_embedding = vec
    db.add(resume)
    return vec


def _build_deterministic_recommendations(
    missing_req_skills: List[str],
    missing_pref_skills: List[str],
    exp_gaps: List[str],
) -> List[Dict[str, Any]]:
    recs: List[RecommendationItem] = []
    for skill in missing_req_skills[:3]:
        recs.append(
            RecommendationItem(
                id=f"req-{skill.lower().replace(' ', '-')}",
                category="Skills",
                severity="Critical",
                issue=f"Required skill '{skill}' not detected in resume.",
                explanation=f"The role lists '{skill}' as a core requirement.",
                suggested_action=f"Verify '{skill}' proficiency during technical screening.",
                related_requirement=f"Required Skill: {skill}",
            )
        )
    for gap in exp_gaps[:2]:
        recs.append(
            RecommendationItem(
                id=f"exp-{len(recs)}",
                category="Experience",
                severity="High",
                issue="Experience / seniority gap noted.",
                explanation=gap,
                suggested_action="Probe depth of hands-on production ownership in interview.",
                related_requirement="Experience Alignment",
            )
        )
    for skill in missing_pref_skills[:2]:
        recs.append(
            RecommendationItem(
                id=f"pref-{skill.lower().replace(' ', '-')}",
                category="Skills",
                severity="Medium",
                issue=f"Preferred skill '{skill}' not explicitly present.",
                explanation=f"'{skill}' is listed as a preferred qualification.",
                suggested_action=f"Check adjacent tooling familiarity related to '{skill}'.",
                related_requirement=f"Preferred Skill: {skill}",
            )
        )
    return [r.model_dump() for r in recs]


def _analysis_to_rank_item(analysis: Analysis, resume: Resume, default_rank: int) -> CandidateRankItem:
    sd = resume.structured_data if isinstance(resume.structured_data, dict) else {}
    res_data = analysis.analysis_result if isinstance(analysis.analysis_result, dict) else {}
    matched = [
        m.get("skill", "") for m in res_data.get("matching_skills", []) if isinstance(m, dict) and m.get("skill")
    ]
    missing = [
        m.get("skill", "")
        for m in res_data.get("missing_required_skills", [])
        if isinstance(m, dict) and m.get("skill")
    ]
    rerank = res_data.get("ai_rerank") or {}
    strengths = list(rerank.get("strengths") or [])
    gaps = list(rerank.get("gaps") or [])

    if not strengths and matched:
        strengths = [f"Matched skills: {', '.join(matched[:4])}"]
    if not gaps and missing:
        gaps = [f"Missing required: {', '.join(missing[:3])}"]

    classification = (
        analysis.match_classification
        or rerank.get("classification")
        or classify_match(analysis.overall_score, len(missing), analysis.hard_filter_passed)
    )

    return CandidateRankItem(
        analysis_id=analysis.id,
        resume_id=resume.id,
        job_id=analysis.job_id,
        rank=analysis.rank_position or default_rank,
        candidate_name=sd.get("name") or resume.name,
        original_filename=resume.original_filename,
        email=sd.get("email") or "",
        location=resume.candidate_location or sd.get("location") or "Unknown",
        experience_years=resume.candidate_years,
        overall_score=analysis.overall_score,
        skill_score=analysis.skill_score,
        experience_score=analysis.experience_score,
        education_score=analysis.education_score,
        keyword_score=analysis.keyword_score,
        semantic_score=analysis.semantic_score,
        match_classification=classification,
        ai_reranked=bool(analysis.ai_reranked),
        hard_filter_passed=bool(analysis.hard_filter_passed),
        hard_filter_notes=list(analysis.hard_filter_notes or []),
        matched_skills=matched,
        missing_skills=missing,
        strengths=strengths,
        gaps=gaps,
        created_at=analysis.created_at,
    )


class ScreeningService:
    @staticmethod
    def _build_structured_job(job: Job) -> StructuredJob:
        data = dict(job.structured_data or {})
        structured_job = StructuredJob.model_validate(data)
        structured_job.job_title = job.title
        structured_job.company = job.company
        structured_job.location = job.location or structured_job.location
        structured_job.work_mode = job.work_mode or structured_job.work_mode or "Hybrid"
        if job.min_experience is not None:
            structured_job.min_experience = job.min_experience
            structured_job.years_of_experience = job.min_experience
        if job.max_experience is not None:
            structured_job.max_experience = job.max_experience
        if job.required_skills:
            structured_job.required_skills = list(job.required_skills)
        if job.preferred_skills:
            structured_job.preferred_skills = list(job.preferred_skills)
        if job.education_requirements:
            structured_job.education_requirements = list(job.education_requirements)
        return structured_job

    @classmethod
    def create_screening_run(
        cls,
        db: Session,
        user_id: str,
        job_id: str,
        request: ScreeningRunRequest,
    ) -> ScreeningRun:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        resumes = resume_repository.get_ready_resumes(db, user_id, resume_ids=request.resume_ids)
        if not resumes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ready resumes found to screen for this job.",
            )

        provider_name = (settings.AI_PROVIDER or "mock").strip().lower()
        model_name = (
            settings.OLLAMA_MODEL
            if provider_name == "ollama"
            else (settings.get_openai_model() if provider_name == "openai" else "deterministic-nlp-v1")
        )

        run = ScreeningRun(
            user_id=user_id,
            job_id=job.id,
            status="queued",
            stage="queued",
            total_resumes=len(resumes),
            processed_resumes=0,
            matched_resumes=0,
            failed_resumes=0,
            shortlisted_count=0,
            reranked_count=0,
            ai_provider=provider_name,
            ai_model=model_name,
            ai_rerank_used=False,
            failed_files=[],
            resume_ids=[r.id for r in resumes],
        )
        return screening_repository.create(db, run)

    @classmethod
    def run_screening_pipeline(
        cls,
        screening_run_id: str,
        *,
        use_ai_rerank: bool = True,
        rerank_top_k: Optional[int] = None,
    ) -> None:
        """
        Executes multi-stage screening in the background:
        1. Cached embeddings + fast deterministic hard filters & 5-pillar base scoring (chunked commits for live progress).
        2. Shortlist top MATCHING_TOP_K candidates -> select top AI_RERANK_TOP_K.
        3. Concise Qwen3 1.7B / OpenAI reranking ONLY on shortlisted candidates (never silent MockAI fallback unless enabled).
        4. Persist final reproducible ranks.
        """
        start_time = time.perf_counter()
        db = SessionLocal()
        try:
            run = db.query(ScreeningRun).filter(ScreeningRun.id == screening_run_id).first()
            if not run:
                return

            run.status = "processing"
            run.stage = "filtering"
            run.started_at = _utc_now_naive()
            db.commit()

            job = job_repository.get_by_user_and_id(db, run.user_id, run.job_id)
            if not job:
                run.status = "failed"
                run.ai_error = "Target job no longer exists."
                db.commit()
                return

            structured_job = cls._build_structured_job(job)
            job_vec = _get_or_create_job_embedding(db, job, structured_job)
            resumes = resume_repository.get_ready_resumes(db, run.user_id, resume_ids=run.resume_ids)

            scored_entries: List[Tuple[Analysis, Resume, StructuredResume]] = []
            failed_files = list(run.failed_files or [])
            chunk_size = 25

            run.stage = "embedding"
            db.commit()

            for idx, resume in enumerate(resumes):
                try:
                    structured_resume = StructuredResume.model_validate(resume.structured_data or {})
                    skill_score, matching_skills, missing_req, missing_pref = SkillMatcher.match_skills(
                        structured_resume, structured_job
                    )
                    exp_score, exp_gap = ExperienceMatcher.match_experience(structured_resume, structured_job)
                    keyword_score, ats_analysis = ATSAnalyzer.analyze_ats(
                        structured_resume, structured_job, resume.raw_text
                    )
                    education_score = EducationMatcher.match_education(structured_resume, structured_job)

                    cand_years = ExperienceMatcher.estimate_candidate_years(structured_resume)
                    if resume.candidate_years != cand_years:
                        resume.candidate_years = cand_years
                        db.add(resume)
                    hard_passed, hard_notes = _evaluate_hard_filters(
                        resume, structured_resume, cand_years, job, structured_job
                    )

                    # Fast vector comparison using cached combined embedding
                    resume_vec = _get_or_compute_resume_embedding(db, resume, structured_resume)
                    sim = cosine_similarity(job_vec, resume_vec)
                    semantic_score = round(min(100.0, max(0.0, sim * 100.0)), 2)

                    evidence_items: List[RequirementEvidence] = [
                        RequirementEvidence(
                            requirement=f"Required skill: {m.skill}",
                            match_status="Strong match",
                            evidence=m.evidence,
                            confidence=0.9,
                        )
                        for m in matching_skills[:8]
                    ]

                    overall = (
                        skill_score * settings.WEIGHT_SKILLS
                        + exp_score * settings.WEIGHT_EXPERIENCE
                        + semantic_score * settings.WEIGHT_SEMANTIC
                        + keyword_score * settings.WEIGHT_KEYWORDS
                        + education_score * settings.WEIGHT_EDUCATION
                    )
                    if not hard_passed:
                        overall = max(5.0, overall * 0.78)
                    overall_score = round(max(0.0, min(100.0, overall)), 2)

                    scoring_weights = {
                        "skills": settings.WEIGHT_SKILLS,
                        "experience": settings.WEIGHT_EXPERIENCE,
                        "semantic": settings.WEIGHT_SEMANTIC,
                        "keywords": settings.WEIGHT_KEYWORDS,
                        "education": settings.WEIGHT_EDUCATION,
                    }

                    analysis_data = AnalysisResultData(
                        overall_score=overall_score,
                        skill_score=skill_score,
                        experience_score=exp_score,
                        education_score=education_score,
                        keyword_score=keyword_score,
                        semantic_score=semantic_score,
                        matching_skills=matching_skills,
                        missing_required_skills=missing_req,
                        missing_preferred_skills=missing_pref,
                        experience_gap_analysis=exp_gap,
                        ats_analysis=ats_analysis,
                        requirements_evidence=evidence_items,
                        scoring_weights=scoring_weights,
                    )

                    recommendations = _build_deterministic_recommendations(
                        [m.skill for m in missing_req],
                        [m.skill for m in missing_pref],
                        exp_gap.gaps,
                    )
                    classification = classify_match(overall_score, len(missing_req), hard_passed)

                    existing_analysis = analysis_repository.get_by_resume_and_job(
                        db, run.user_id, resume.id, job.id
                    )
                    if existing_analysis:
                        existing_analysis.screening_run_id = run.id
                        existing_analysis.overall_score = overall_score
                        existing_analysis.skill_score = skill_score
                        existing_analysis.experience_score = exp_score
                        existing_analysis.education_score = education_score
                        existing_analysis.keyword_score = keyword_score
                        existing_analysis.semantic_score = semantic_score
                        existing_analysis.match_classification = classification
                        existing_analysis.ai_reranked = False
                        existing_analysis.hard_filter_passed = hard_passed
                        existing_analysis.hard_filter_notes = hard_notes
                        existing_analysis.analysis_result = analysis_data.model_dump()
                        existing_analysis.recommendations = recommendations
                        analysis_obj = existing_analysis
                    else:
                        analysis_obj = Analysis(
                            user_id=run.user_id,
                            resume_id=resume.id,
                            job_id=job.id,
                            screening_run_id=run.id,
                            overall_score=overall_score,
                            skill_score=skill_score,
                            experience_score=exp_score,
                            education_score=education_score,
                            keyword_score=keyword_score,
                            semantic_score=semantic_score,
                            match_classification=classification,
                            ai_reranked=False,
                            hard_filter_passed=hard_passed,
                            hard_filter_notes=hard_notes,
                            analysis_result=analysis_data.model_dump(),
                            recommendations=recommendations,
                        )
                        db.add(analysis_obj)

                    scored_entries.append((analysis_obj, resume, structured_resume))
                    run.matched_resumes += 1
                except Exception as exc:
                    run.failed_resumes += 1
                    failed_files.append(
                        {
                            "filename": resume.original_filename,
                            "resume_id": resume.id,
                            "reason": str(exc) or "Error during matching",
                        }
                    )

                run.processed_resumes += 1
                if (idx + 1) % chunk_size == 0 or (idx + 1) == len(resumes):
                    run.failed_files = failed_files
                    db.commit()

            # Stage 2: Shortlist top candidates
            scored_entries.sort(
                key=lambda item: (
                    1 if item[0].hard_filter_passed else 0,
                    item[0].overall_score,
                    item[0].semantic_score,
                ),
                reverse=True,
            )
            shortlist = scored_entries[: settings.MATCHING_TOP_K]
            run.shortlisted_count = len(shortlist)

            rerank_limit = rerank_top_k or settings.AI_RERANK_TOP_K
            rerank_targets = shortlist[:rerank_limit]

            # Stage 3: Concise AI Reranking ONLY on top shortlisted candidates
            if use_ai_rerank and rerank_targets:
                run.stage = "reranking"
                db.commit()

                try:
                    ai_provider = get_ai_provider()
                    run.ai_provider = ai_provider.provider_name
                    run.ai_model = ai_provider.model_name
                except Exception as cfg_exc:
                    ai_provider = None
                    run.ai_error = f"Local AI unavailable: {cfg_exc}"
                    db.commit()

                if ai_provider is not None:
                    job_summary = {
                        "role": structured_job.job_title,
                        "work_mode": structured_job.work_mode,
                        "location": structured_job.location or "Any",
                        "min_experience": structured_job.min_experience,
                        "max_experience": structured_job.max_experience,
                        "required_skills": structured_job.required_skills[:12],
                        "preferred_skills": structured_job.preferred_skills[:8],
                    }

                    for analysis_obj, resume, structured_resume in rerank_targets:
                        res_data = analysis_obj.analysis_result or {}
                        matched_skills = [m.get("skill", "") for m in res_data.get("matching_skills", [])]
                        missing_skills = [m.get("skill", "") for m in res_data.get("missing_required_skills", [])]
                        evidence_snippets = [
                            m.get("evidence", "")[:140]
                            for m in res_data.get("matching_skills", [])[:5]
                            if m.get("evidence")
                        ]
                        candidate_summary = {
                            "name": structured_resume.name or resume.name,
                            "experience_years": resume.candidate_years,
                            "location": resume.candidate_location or "Unknown",
                            "preliminary_score": analysis_obj.overall_score,
                            "matched_skills": matched_skills[:12],
                            "missing_skills": missing_skills[:10],
                            "skills": structured_resume.skills[:15],
                            "roles": [
                                f"{e.role} at {e.company}" for e in structured_resume.experience[:3]
                            ],
                            "evidence_snippets": evidence_snippets,
                        }

                        rerank_result: Optional[CandidateRerankResult] = None
                        try:
                            rerank_result = ai_provider.rerank_candidate(candidate_summary, job_summary)
                        except Exception as ai_exc:
                            # Strictly honor AI_FALLBACK_ENABLED=false (no silent MockAI swap!)
                            fallback = get_fallback_ai_provider(ai_provider.provider_name)
                            if fallback is not None:
                                rerank_result = fallback.rerank_candidate(candidate_summary, job_summary)
                            else:
                                provider_label = "Local AI" if ai_provider.provider_name == "ollama" else "Cloud AI"
                                run.ai_error = f"{provider_label} unavailable: {ai_exc}"
                                db.commit()
                                break

                        if rerank_result is not None:
                            updated_result = dict(analysis_obj.analysis_result or {})
                            updated_result["ai_rerank"] = rerank_result.model_dump()
                            analysis_obj.analysis_result = updated_result
                            analysis_obj.match_classification = rerank_result.classification
                            analysis_obj.ai_reranked = True
                            run.ai_rerank_used = True
                            run.reranked_count += 1
                            db.commit()

            # Stage 4: Final deterministic ranking positions
            run.stage = "scoring"
            all_job_analyses = analysis_repository.get_for_job(db, run.user_id, job.id)
            all_job_analyses.sort(
                key=lambda a: (
                    1 if a.hard_filter_passed else 0,
                    a.overall_score,
                    _CLASSIFICATION_PRIORITY.get(a.match_classification or "", 0) if a.ai_reranked else 0,
                    a.semantic_score,
                ),
                reverse=True,
            )
            for rank_idx, item in enumerate(all_job_analyses, start=1):
                item.rank_position = rank_idx

            run.stage = "done"
            run.status = "completed_with_errors" if run.failed_resumes > 0 else "completed"
            run.completed_at = _utc_now_naive()
            db.commit()

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"ScreeningRun {run.id} completed status={run.status} total={run.total_resumes} "
                f"matched={run.matched_resumes} reranked={run.reranked_count} duration_ms={duration_ms:.1f}"
            )
        except Exception as exc:
            logger.error(f"ScreeningRun {screening_run_id} failed: {exc}")
            try:
                run = db.query(ScreeningRun).filter(ScreeningRun.id == screening_run_id).first()
                if run:
                    run.status = "failed"
                    run.ai_error = str(exc)
                    run.completed_at = _utc_now_naive()
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    @classmethod
    def get_screening_status(
        cls,
        db: Session,
        user_id: str,
        job_id: str,
        run_id: Optional[str] = None,
    ) -> ScreeningRunResponse:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        run = (
            screening_repository.get_by_user_and_id(db, user_id, run_id)
            if run_id
            else screening_repository.get_latest_for_job(db, user_id, job_id)
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No screening runs found for this job.",
            )

        top_candidates = cls.get_ranked_candidates(db, user_id, job_id, limit=10)
        resp = ScreeningRunResponse.model_validate(run)
        resp.top_candidates = top_candidates
        return resp

    @staticmethod
    def get_ranked_candidates(
        db: Session,
        user_id: str,
        job_id: str,
        *,
        min_score: Optional[float] = None,
        min_experience: Optional[float] = None,
        location: Optional[str] = None,
        required_skill: Optional[str] = None,
        classification: Optional[str] = None,
        sort_by: str = "score_desc",
        limit: int = 200,
    ) -> List[CandidateRankItem]:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        analyses = analysis_repository.get_for_job(db, user_id, job_id)
        if not analyses:
            return []

        resume_ids = [a.resume_id for a in analyses]
        resumes_by_id = {
            r.id: r for r in db.query(Resume).filter(Resume.id.in_(resume_ids)).all()
        }

        items: List[CandidateRankItem] = []
        for idx, analysis in enumerate(analyses, start=1):
            resume = resumes_by_id.get(analysis.resume_id)
            if not resume:
                continue
            item = _analysis_to_rank_item(analysis, resume, default_rank=idx)

            if min_score is not None and item.overall_score < min_score:
                continue
            if min_experience is not None and (item.experience_years or 0.0) < min_experience:
                continue
            if location and location.strip().lower() not in item.location.lower():
                continue
            if classification and item.match_classification.upper() != classification.strip().upper():
                continue
            if required_skill:
                skill_q = required_skill.strip().lower()
                if not any(skill_q in s.lower() for s in item.matched_skills):
                    continue

            items.append(item)

        if sort_by == "score_asc":
            items.sort(key=lambda x: x.overall_score)
        elif sort_by == "experience_desc":
            items.sort(key=lambda x: (x.experience_years or 0.0, x.overall_score), reverse=True)
        elif sort_by == "semantic_desc":
            items.sort(key=lambda x: (x.semantic_score, x.overall_score), reverse=True)
        else:
            items.sort(
                key=lambda x: (
                    1 if x.hard_filter_passed else 0,
                    x.overall_score,
                    x.semantic_score,
                ),
                reverse=True,
            )

        for rank_idx, item in enumerate(items, start=1):
            item.rank = rank_idx

        return items[:limit]

    @staticmethod
    def get_candidate_detail(
        db: Session,
        user_id: str,
        job_id: str,
        candidate_id: str,
    ) -> CandidateDetailResponse:
        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        # candidate_id may be resume_id or analysis_id
        analysis = analysis_repository.get_by_resume_and_job(db, user_id, candidate_id, job_id)
        if not analysis:
            analysis = analysis_repository.get_by_user_and_id(db, user_id, candidate_id)
            if analysis and analysis.job_id != job_id:
                analysis = None
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate match result not found for this job.",
            )

        resume = resume_repository.get_by_user_and_id(db, user_id, analysis.resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

        sd = resume.structured_data if isinstance(resume.structured_data, dict) else {}
        classification = analysis.match_classification or classify_match(
            analysis.overall_score,
            len((analysis.analysis_result or {}).get("missing_required_skills", [])),
            analysis.hard_filter_passed,
        )

        return CandidateDetailResponse(
            analysis_id=analysis.id,
            resume_id=resume.id,
            job_id=job.id,
            candidate_name=sd.get("name") or resume.name,
            original_filename=resume.original_filename,
            email=sd.get("email") or "",
            phone=sd.get("phone") or "",
            location=resume.candidate_location or sd.get("location") or "Unknown",
            experience_years=resume.candidate_years,
            overall_score=analysis.overall_score,
            skill_score=analysis.skill_score,
            experience_score=analysis.experience_score,
            education_score=analysis.education_score,
            keyword_score=analysis.keyword_score,
            semantic_score=analysis.semantic_score,
            match_classification=classification,
            ai_reranked=bool(analysis.ai_reranked),
            hard_filter_passed=bool(analysis.hard_filter_passed),
            hard_filter_notes=list(analysis.hard_filter_notes or []),
            skills=list(sd.get("skills") or []),
            analysis_result=analysis.analysis_result or {},
            recommendations=analysis.recommendations or [],
            structured_resume=sd,
            created_at=analysis.created_at,
        )


screening_service = ScreeningService()

