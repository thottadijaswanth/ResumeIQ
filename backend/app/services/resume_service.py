import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.ai import LocalDeterministicEmbeddingProvider, get_embedding_provider
from backend.app.config import settings
from backend.app.document_processing import DocumentParser
from backend.app.matching.fast_extractor import FastCandidateExtractor
from backend.app.matching.semantic_matcher import SemanticMatcher
from backend.app.models.resume import Resume, ResumeEmbedding
from backend.app.repositories.resume_repository import resume_repository
from backend.app.schemas.resume import (
    BulkResumeFailureItem,
    BulkResumeUploadItem,
    BulkResumeUploadResponse,
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
    StructuredResume,
)
from backend.app.utils.logger import logger


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _build_combined_resume_text(structured: StructuredResume, raw_text: str) -> str:
    exp_text = " ".join(
        f"{e.role} {e.company} {' '.join(e.responsibilities)}" for e in structured.experience[:4]
    )
    return (
        f"{structured.summary} Skills: {', '.join(structured.skills)}. "
        f"Experience: {exp_text}. {raw_text[:1200]}"
    )


def _extract_single_file_payload(
    filename: str,
    file_bytes: bytes,
    content_type: str,
    explicit_name: str = "",
) -> Dict:
    """CPU-only extraction step (safe for ThreadPoolExecutor across batches)."""
    file_hash = _compute_file_hash(file_bytes)
    raw_text, file_type = DocumentParser.parse_document(filename, file_bytes, content_type)
    base_name = explicit_name.strip() or filename.rsplit(".", 1)[0]
    structured_data, candidate_years, candidate_location = FastCandidateExtractor.extract_candidate_profile(
        raw_text, fallback_name=base_name
    )
    return {
        "filename": filename,
        "name": explicit_name.strip() or structured_data.name or base_name,
        "file_type": file_type,
        "file_size": len(file_bytes),
        "file_hash": file_hash,
        "raw_text": raw_text,
        "structured_data": structured_data,
        "candidate_years": candidate_years,
        "candidate_location": candidate_location,
    }


def _compute_embeddings_safe(texts: List[str]) -> List[List[float]]:
    """
    Compute embeddings using the configured provider, gracefully falling back to
    offline LocalDeterministicEmbeddingProvider (1536-dim) if cloud embeddings fail
    (e.g., quota exhausted or offline) so resume uploads never fail.
    """
    if not texts:
        return []
    try:
        embedder = get_embedding_provider()
        return embedder.get_embeddings(texts)
    except Exception as exc:
        logger.warning(
            f"Configured embedding provider failed ({type(exc).__name__}); "
            "using offline LocalDeterministicEmbeddingProvider so upload completes."
        )
        return LocalDeterministicEmbeddingProvider(dim=settings.EMBEDDING_DIMENSIONS).get_embeddings(texts)


class ResumeService:
    @staticmethod
    def _to_list_item(r: Resume) -> ResumeListResponse:
        skills: List[str] = []
        if isinstance(r.structured_data, dict):
            skills = list(r.structured_data.get("skills") or [])[:12]
        return ResumeListResponse(
            id=r.id,
            name=r.name,
            original_filename=r.original_filename,
            file_type=r.file_type,
            file_size=r.file_size,
            file_hash=r.file_hash,
            candidate_years=r.candidate_years,
            candidate_location=r.candidate_location,
            processing_status=r.processing_status or "ready",
            skills=skills,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    @staticmethod
    def _persist_parsed_resume(db: Session, user_id: str, parsed: Dict) -> Resume:
        structured_data: StructuredResume = parsed["structured_data"]

        combined_text = _build_combined_resume_text(structured_data, parsed["raw_text"])
        chunks = SemanticMatcher.chunk_resume(structured_data)
        all_texts = [combined_text] + [c[1] for c in chunks]
        vectors = _compute_embeddings_safe(all_texts)
        combined_vec = vectors[0]
        chunk_vecs = vectors[1:]

        db_resume = Resume(
            user_id=user_id,
            name=parsed["name"],
            original_filename=parsed["filename"],
            file_type=parsed["file_type"],
            file_size=parsed["file_size"],
            file_hash=parsed["file_hash"],
            raw_text=parsed["raw_text"],
            structured_data=structured_data.model_dump(),
            candidate_years=parsed["candidate_years"],
            candidate_location=parsed["candidate_location"],
            combined_embedding=combined_vec,
            processing_status="ready",
            ai_provider_used="deterministic-nlp",
            ai_model_used="fast-extractor-v2",
            processed_at=_utc_now_naive(),
        )
        created = resume_repository.create(db, db_resume)

        if chunks:
            db_embeddings = [
                ResumeEmbedding(
                    resume_id=created.id,
                    chunk_type=chunks[i][0],
                    chunk_text=chunks[i][1],
                    embedding=chunk_vecs[i],
                    embedding_metadata={"chunk_index": i},
                )
                for i in range(len(chunks))
            ]
            resume_repository.add_embeddings(db, db_embeddings)
        return created

    @classmethod
    def process_and_create_resume(
        cls,
        db: Session,
        user_id: str,
        name: str,
        file: UploadFile,
    ) -> ResumeResponse:
        filename = file.filename or "resume.pdf"
        file_bytes = file.file.read()
        file_hash = _compute_file_hash(file_bytes)

        # Cache hit check by SHA-256 fingerprint
        cached = resume_repository.get_by_user_and_hash(db, user_id, file_hash)
        if cached:
            return ResumeResponse.model_validate(cached)

        try:
            parsed = _extract_single_file_payload(
                filename, file_bytes, file.content_type or "", explicit_name=name
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        created = cls._persist_parsed_resume(db, user_id, parsed)
        return ResumeResponse.model_validate(created)

    @classmethod
    def process_batch_resumes(
        cls,
        db: Session,
        user_id: str,
        files_payload: List[Tuple[str, bytes, str]],
    ) -> BulkResumeUploadResponse:
        """
        Process a batch of resumes efficiently:
        1. Deduplicate against already cached SHA-256 fingerprints in DB.
        2. Parse PDF/DOCX + normalize profiles concurrently across bounded workers.
        3. Isolate corrupt/invalid files without failing the batch.
        4. Batch-embed & store candidate profiles once for reuse across jobs.
        """
        total_received = len(files_payload)
        items: List[BulkResumeUploadItem] = []
        failed: List[BulkResumeFailureItem] = []
        to_extract: List[Tuple[str, bytes, str, str]] = []
        seen_hashes_in_batch: Dict[str, Resume] = {}
        cached_count = 0

        for filename, file_bytes, content_type in files_payload:
            file_hash = _compute_file_hash(file_bytes)
            existing = seen_hashes_in_batch.get(file_hash) or resume_repository.get_by_user_and_hash(
                db, user_id, file_hash
            )
            if existing:
                cached_count += 1
                seen_hashes_in_batch[file_hash] = existing
                skills = (existing.structured_data or {}).get("skills", []) if isinstance(existing.structured_data, dict) else []
                items.append(
                    BulkResumeUploadItem(
                        id=existing.id,
                        name=existing.name,
                        original_filename=existing.original_filename,
                        cached=True,
                        candidate_years=existing.candidate_years,
                        candidate_location=existing.candidate_location,
                        skills_count=len(skills),
                    )
                )
            else:
                to_extract.append((filename, file_bytes, content_type, file_hash))

        parsed_records: List[Dict] = []
        if to_extract:
            max_workers = max(1, min(settings.MAX_CONCURRENT_RESUME_PROCESSING, len(to_extract)))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map = {
                    pool.submit(_extract_single_file_payload, fname, fbytes, ctype): (fname, fhash)
                    for fname, fbytes, ctype, fhash in to_extract
                }
                for fut in as_completed(future_map):
                    fname, _ = future_map[fut]
                    try:
                        parsed_records.append(fut.result())
                    except Exception as exc:
                        failed.append(
                            BulkResumeFailureItem(
                                filename=fname,
                                reason=str(exc) or "Unable to extract text from resume file.",
                            )
                        )

        if parsed_records:
            # Batch-generate combined embeddings in one call (resilient local fallback if cloud unavailable)
            combined_texts = [
                _build_combined_resume_text(rec["structured_data"], rec["raw_text"])
                for rec in parsed_records
            ]
            combined_vectors = _compute_embeddings_safe(combined_texts)

            now = _utc_now_naive()
            created_resumes: List[Resume] = []
            for idx, rec in enumerate(parsed_records):
                if rec["file_hash"] in seen_hashes_in_batch:
                    existing = seen_hashes_in_batch[rec["file_hash"]]
                    cached_count += 1
                    skills = (existing.structured_data or {}).get("skills", []) if isinstance(existing.structured_data, dict) else []
                    items.append(
                        BulkResumeUploadItem(
                            id=existing.id,
                            name=existing.name,
                            original_filename=existing.original_filename,
                            cached=True,
                            candidate_years=existing.candidate_years,
                            candidate_location=existing.candidate_location,
                            skills_count=len(skills),
                        )
                    )
                    continue

                structured_data: StructuredResume = rec["structured_data"]
                db_resume = Resume(
                    user_id=user_id,
                    name=rec["name"],
                    original_filename=rec["filename"],
                    file_type=rec["file_type"],
                    file_size=rec["file_size"],
                    file_hash=rec["file_hash"],
                    raw_text=rec["raw_text"],
                    structured_data=structured_data.model_dump(),
                    candidate_years=rec["candidate_years"],
                    candidate_location=rec["candidate_location"],
                    combined_embedding=combined_vectors[idx],
                    processing_status="ready",
                    ai_provider_used="deterministic-nlp",
                    ai_model_used="fast-extractor-v2",
                    processed_at=now,
                )
                db.add(db_resume)
                created_resumes.append(db_resume)
                seen_hashes_in_batch[rec["file_hash"]] = db_resume

            if created_resumes:
                db.commit()
                for res_obj in created_resumes:
                    db.refresh(res_obj)
                    skills = (res_obj.structured_data or {}).get("skills", []) if isinstance(res_obj.structured_data, dict) else []
                    items.append(
                        BulkResumeUploadItem(
                            id=res_obj.id,
                            name=res_obj.name,
                            original_filename=res_obj.original_filename,
                            cached=False,
                            candidate_years=res_obj.candidate_years,
                            candidate_location=res_obj.candidate_location,
                            skills_count=len(skills),
                        )
                    )

        logger.info(
            f"Batch resume upload complete user_id={user_id} received={total_received} "
            f"processed={len(items)} cached={cached_count} failed={len(failed)}"
        )

        return BulkResumeUploadResponse(
            total_received=total_received,
            processed_count=len(items),
            cached_count=cached_count,
            failed_count=len(failed),
            resumes=items,
            failed_files=failed,
        )

    @classmethod
    def get_user_resumes(cls, db: Session, user_id: str, skip: int = 0, limit: int = 200) -> List[ResumeListResponse]:
        resumes = resume_repository.get_user_resumes(db, user_id, skip=skip, limit=limit)
        return [cls._to_list_item(r) for r in resumes]

    @staticmethod
    def get_resume_by_id(db: Session, user_id: str, resume_id: str) -> ResumeResponse:
        resume = resume_repository.get_by_user_and_id(db, user_id, resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        return ResumeResponse.model_validate(resume)

    @staticmethod
    def update_resume(db: Session, user_id: str, resume_id: str, update_data: ResumeUpdate) -> ResumeResponse:
        resume = resume_repository.get_by_user_and_id(db, user_id, resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

        if update_data.name:
            resume.name = update_data.name.strip()
        if update_data.structured_data:
            resume.structured_data = update_data.structured_data.model_dump()

        updated = resume_repository.update(db, resume)
        return ResumeResponse.model_validate(updated)

    @staticmethod
    def delete_resume(db: Session, user_id: str, resume_id: str) -> bool:
        resume = resume_repository.get_by_user_and_id(db, user_id, resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        return resume_repository.delete(db, resume_id)


resume_service = ResumeService()
