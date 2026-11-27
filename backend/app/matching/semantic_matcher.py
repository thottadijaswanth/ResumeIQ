from typing import List, Tuple
from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.analysis import RequirementEvidence
from backend.app.ai.embeddings import (
    LocalDeterministicEmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)
from backend.app.config import settings


class SemanticMatcher:
    @classmethod
    def chunk_resume(cls, resume: StructuredResume) -> List[Tuple[str, str]]:
        """Return list of (chunk_type, chunk_text)."""
        chunks = []
        if resume.summary:
            chunks.append(("summary", f"Professional Summary: {resume.summary}"))

        for exp in resume.experience:
            text = f"Role: {exp.role} at {exp.company}. Responsibilities: {' '.join(exp.responsibilities)}. Achievements: {' '.join(exp.achievements)}. Technologies: {', '.join(exp.technologies)}."
            chunks.append(("experience", text))

        for proj in resume.projects:
            text = f"Project: {proj.name}. Description: {proj.description}. Technologies: {', '.join(proj.technologies)}. Achievements: {' '.join(proj.achievements)}."
            chunks.append(("project", text))

        if resume.skills:
            chunks.append(("skills", f"Technical and Professional Skills: {', '.join(resume.skills)}"))

        return chunks

    @classmethod
    def chunk_job(cls, job: StructuredJob) -> List[Tuple[str, str]]:
        """Return list of (chunk_type, chunk_text)."""
        chunks = []
        if job.job_title:
            chunks.append(("title", f"Job Title: {job.job_title} at {job.company}"))

        for resp in job.responsibilities:
            chunks.append(("responsibility", f"Responsibility: {resp}"))

        for qual in job.qualifications:
            chunks.append(("qualification", f"Requirement: {qual}"))

        for req in job.education_requirements:
            chunks.append(("education_req", f"Education Requirement: {req}"))

        if not chunks:
            chunks.append(("general", f"Job Position: {job.job_title} with skills {', '.join(job.required_skills)}"))

        return chunks

    @classmethod
    def match_semantic(
        cls,
        resume: StructuredResume,
        job: StructuredJob,
    ) -> Tuple[float, List[RequirementEvidence]]:
        """
        Embed chunks and calculate bidirectional semantic similarity.
        Returns:
            (semantic_score: 0-100, requirements_evidence: List[RequirementEvidence])
        """
        embedder = get_embedding_provider()

        resume_chunks = cls.chunk_resume(resume)
        job_chunks = cls.chunk_job(job)

        if not resume_chunks or not job_chunks:
            return 50.0, []

        resume_texts = [c[1] for c in resume_chunks]
        job_texts = [c[1] for c in job_chunks]

        try:
            resume_vectors = embedder.get_embeddings(resume_texts)
            job_vectors = embedder.get_embeddings(job_texts)
        except Exception:
            fallback_embedder = LocalDeterministicEmbeddingProvider(dim=settings.EMBEDDING_DIMENSIONS)
            resume_vectors = fallback_embedder.get_embeddings(resume_texts)
            job_vectors = fallback_embedder.get_embeddings(job_texts)

        evidence_list: List[RequirementEvidence] = []
        similarity_scores: List[float] = []

        for j_idx, (j_type, j_text) in enumerate(job_chunks):
            j_vec = job_vectors[j_idx]
            best_sim = -1.0
            best_resume_snippet = ""

            for r_idx, (r_type, r_text) in enumerate(resume_chunks):
                r_vec = resume_vectors[r_idx]
                sim = cosine_similarity(j_vec, r_vec)
                if sim > best_sim:
                    best_sim = sim
                    best_resume_snippet = r_text

            similarity_scores.append(best_sim)

            # Categorize match status
            if best_sim >= 0.70:
                status = "Strong match"
            elif best_sim >= 0.45:
                status = "Partial match"
            else:
                status = "Not found"

            # Trim snippet if too long
            display_snippet = best_resume_snippet[:160] + "..." if len(best_resume_snippet) > 160 else best_resume_snippet
            if status == "Not found":
                display_snippet = "No direct alignment identified in resume."

            evidence_list.append(
                RequirementEvidence(
                    requirement=j_text,
                    match_status=status,
                    evidence=display_snippet,
                    confidence=round(max(0.0, best_sim), 2),
                )
            )

        avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.5
        # Scale similarity to 0-100 range
        semantic_score = round(min(100.0, max(0.0, avg_similarity * 100.0)), 2)

        return semantic_score, evidence_list

