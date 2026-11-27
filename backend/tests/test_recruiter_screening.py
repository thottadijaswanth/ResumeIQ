import io
import json
import time
import fitz
import httpx
from backend.app.ai import OllamaProvider
from backend.app.config import settings
from backend.app.services.screening_service import screening_service


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_structured_job_creation(client, auth_headers):
    res = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "title": "Senior Java Backend Developer",
            "company": "FinTech India",
            "location": "Hyderabad, India",
            "work_mode": "Hybrid",
            "min_experience": 4,
            "max_experience": 7,
            "required_skills": ["Java", "Spring Boot", "REST", "SQL"],
            "preferred_skills": ["AWS", "Docker", "Kubernetes"],
            "employment_type": "Full-time",
            "description": "Build scalable payment APIs in Java and Spring Boot.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Senior Java Backend Developer"
    assert data["location"] == "Hyderabad, India"
    assert data["work_mode"] == "Hybrid"
    assert data["min_experience"] == 4.0
    assert data["max_experience"] == 7.0
    assert "Java" in data["required_skills"]
    assert "Spring Boot" in data["required_skills"]


def test_batch_resume_upload_1_10_100_caching_and_partial_errors(client, auth_headers):
    # 1. Single batch upload + duplicate cache verification
    pdf1 = _make_pdf_bytes(
        "Rahul Kumar\nHyderabad, India\nrahul@example.com\n"
        "Senior Java Developer (2020-Present)\n5 years of experience\n"
        "Skills: Java, Spring Boot, SQL, AWS, Docker\n"
    )
    r1 = client.post(
        "/api/resumes/batch",
        headers=auth_headers,
        files=[("files", ("rahul.pdf", io.BytesIO(pdf1), "application/pdf"))],
    )
    assert r1.status_code == 201
    assert r1.json()["processed_count"] == 1
    assert r1.json()["cached_count"] == 0

    # Re-upload exact same file -> hits SHA-256 cache
    r1_dup = client.post(
        "/api/resumes/batch",
        headers=auth_headers,
        files=[("files", ("rahul_copy.pdf", io.BytesIO(pdf1), "application/pdf"))],
    )
    assert r1_dup.status_code == 201
    assert r1_dup.json()["cached_count"] == 1
    assert r1_dup.json()["resumes"][0]["id"] == r1.json()["resumes"][0]["id"]

    # 2. Upload 10 resumes including 1 corrupt PDF -> 9 succeed, 1 isolated failure
    batch_10 = []
    for idx in range(9):
        content = _make_pdf_bytes(
            f"Candidate Batch10-{idx}\nHyderabad\ncand{idx}@example.com\n"
            f"Software Engineer (2021-Present)\nSkills: Java, Spring Boot, SQL\n"
        )
        batch_10.append(("files", (f"cand10_{idx}.pdf", io.BytesIO(content), "application/pdf")))
    batch_10.append(("files", ("corrupt_file.pdf", io.BytesIO(b"not a valid pdf"), "application/pdf")))

    r10 = client.post("/api/resumes/batch", headers=auth_headers, files=batch_10)
    assert r10.status_code == 201
    b10 = r10.json()
    assert b10["total_received"] == 10
    assert b10["processed_count"] == 9
    assert b10["failed_count"] == 1
    assert b10["failed_files"][0]["filename"] == "corrupt_file.pdf"

    # 3. Upload 100 resumes scoped to a job (2 chunks of 50 as client would send, or 100 in one call)
    job_res = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "title": "Java Engineer",
            "location": "Hyderabad, India",
            "work_mode": "Hybrid",
            "min_experience": 3,
            "required_skills": ["Java", "SQL"],
            "description": "Backend Java and SQL engineering role.",
        },
    )
    job_id = job_res.json()["id"]

    batch_100 = []
    for idx in range(100):
        content = _make_pdf_bytes(
            f"Candidate Hundred-{idx}\nBangalore\nhundred{idx}@example.com\n"
            f"Developer 4 years of experience. Skills: Java, SQL, Docker\n"
        )
        batch_100.append(("files", (f"cand100_{idx}.pdf", io.BytesIO(content), "application/pdf")))

    r100 = client.post(f"/api/jobs/{job_id}/resumes", headers=auth_headers, files=batch_100)
    assert r100.status_code == 201
    assert r100.json()["processed_count"] == 100
    assert r100.json()["failed_count"] == 0


def test_multi_stage_screening_ranking_and_qwen_top_k(client, auth_headers, monkeypatch):
    # Create ONE job
    job_res = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "title": "Senior Java Backend Developer",
            "company": "CorePayments",
            "location": "Hyderabad, India",
            "work_mode": "Hybrid",
            "min_experience": 4,
            "max_experience": 7,
            "required_skills": ["Java", "Spring Boot", "SQL"],
            "preferred_skills": ["AWS", "Docker"],
            "description": "4-7 years Java backend developer building Spring Boot microservices.",
        },
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Upload 6 diverse candidates (strong match, partial match, under-experienced hard filter, unknown location)
    candidates_text = [
        (
            "strong_cand.pdf",
            "Priya Sharma\nHyderabad, India\npriya@example.com\n"
            "Senior Java Engineer at PayCorp (2020-Present)\n5 years of experience.\n"
            "Built Spring Boot microservices and SQL APIs on AWS and Docker.\n"
            "Education: B.Tech Computer Science\n",
        ),
        (
            "junior_cand.pdf",
            "Rohan Verma\nHyderabad, India\nrohan@example.com\n"
            "Junior Developer\n0.5 years of experience.\n"
            "Skills: Java, SQL\n",
        ),
        (
            "unknown_loc.pdf",
            "Ananya Patel\nananya@example.com\n"
            "Backend Developer (2020-Present)\n4 years of experience.\n"
            "Skills: Java, Spring Boot, SQL, Docker\n",
        ),
        (
            "python_cand.pdf",
            "Vikram Nair\nBangalore, India\nvikram@example.com\n"
            "Python Developer (2021-Present)\n4 years of experience.\n"
            "Skills: Python, Django, PostgreSQL\n",
        ),
    ]
    files = [
        ("files", (fname, io.BytesIO(_make_pdf_bytes(text)), "application/pdf"))
        for fname, text in candidates_text
    ]
    up = client.post(f"/api/jobs/{job_id}/resumes", headers=auth_headers, files=files)
    assert up.status_code == 201
    assert up.json()["processed_count"] == 4

    # Configure mocked Ollama qwen3:1.7b and limit rerank_top_k=2
    ollama_calls = []

    def mock_ollama_handler(request: httpx.Request) -> httpx.Response:
        ollama_calls.append(str(request.url))
        assert str(request.url).startswith("http://127.0.0.1:11434")
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "classification": "STRONG_MATCH",
                            "confidence": 0.91,
                            "strengths": ["Strong Java and Spring Boot production experience"],
                            "gaps": [],
                            "evidence": ["Built Spring Boot microservices and SQL APIs"],
                        }
                    )
                }
            },
        )

    mock_ollama = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:1.7b",
        transport=httpx.MockTransport(mock_ollama_handler),
    )
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen3:1.7b")
    monkeypatch.setattr("backend.app.services.screening_service.get_ai_provider", lambda: mock_ollama)

    screen_res = client.post(
        f"/api/jobs/{job_id}/screen",
        headers=auth_headers,
        json={"use_ai_rerank": True, "rerank_top_k": 2},
    )
    assert screen_res.status_code == 202
    run_id = screen_res.json()["id"]

    status_res = client.get(
        f"/api/jobs/{job_id}/screening-status?run_id={run_id}",
        headers=auth_headers,
    )
    assert status_res.status_code == 200
    status_body = status_res.json()
    assert status_body["status"] == "completed"
    assert status_body["total_resumes"] == 4
    assert status_body["matched_resumes"] == 4
    # Only top_k=2 shortlisted candidates were sent to Qwen3 1.7B!
    assert status_body["reranked_count"] == 2
    assert len(ollama_calls) == 2

    # Verify ranked candidate table, filters, sorting, and detail endpoint
    ranked = client.get(f"/api/jobs/{job_id}/candidates", headers=auth_headers).json()
    assert len(ranked) == 4
    assert ranked[0]["candidate_name"] == "Priya Sharma"
    assert ranked[0]["overall_score"] > ranked[-1]["overall_score"]
    # Candidate with 0.5 yrs vs 4-7 yrs fails hard filter
    junior_row = next(r for r in ranked if r["candidate_name"] == "Rohan Verma")
    assert junior_row["hard_filter_passed"] is False
    # Candidate with missing location gets "Unknown" and is not rejected
    unknown_row = next(r for r in ranked if r["candidate_name"] == "Ananya Patel")
    assert unknown_row["location"] == "Unknown"
    assert unknown_row["hard_filter_passed"] is True

    # Filter by required_skill
    filtered = client.get(
        f"/api/jobs/{job_id}/candidates?required_skill=Spring%20Boot",
        headers=auth_headers,
    ).json()
    assert all("Spring Boot" in c["matched_skills"] for c in filtered)

    # Candidate detail endpoint
    detail = client.get(
        f"/api/jobs/{job_id}/candidates/{ranked[0]['resume_id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["ai_reranked"] is True


def test_screening_no_silent_mock_fallback_when_ollama_unavailable(client, auth_headers, monkeypatch):
    job_id = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "title": "Backend Engineer",
            "location": "Remote",
            "work_mode": "Remote",
            "required_skills": ["Python"],
            "description": "Python backend engineer.",
        },
    ).json()["id"]

    client.post(
        f"/api/jobs/{job_id}/resumes",
        headers=auth_headers,
        files=[
            (
                "files",
                (
                    "dev.pdf",
                    io.BytesIO(_make_pdf_bytes("Alex Dev\nalex@example.com\nSkills: Python\n3 years of experience")),
                    "application/pdf",
                ),
            )
        ],
    )

    down_ollama = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:1.7b",
        max_retries=0,
        transport=httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("refused", request=req))
        ),
    )
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", False)
    monkeypatch.setattr("backend.app.services.screening_service.get_ai_provider", lambda: down_ollama)

    screen_res = client.post(
        f"/api/jobs/{job_id}/screen",
        headers=auth_headers,
        json={"use_ai_rerank": True},
    )
    assert screen_res.status_code == 202

    status_body = client.get(f"/api/jobs/{job_id}/screening-status", headers=auth_headers).json()
    assert status_body["status"] == "completed"
    assert status_body["ai_rerank_used"] is False
    assert status_body["reranked_count"] == 0
    assert "Local AI unavailable" in status_body["ai_error"]


def test_experience_ignores_education_and_tracks_job_internship_timelines():
    from backend.app.matching.fast_extractor import FastCandidateExtractor
    from backend.app.matching.experience_matcher import ExperienceMatcher
    from backend.app.schemas.job import StructuredJob

    # 1. Student with EDUCATION (2021-2028) & PROJECTS only -> 0.0 yrs (never counts education!)
    student_text = (
        "Thottadi Jaswanth\nSoftware Development Engineer (SDE)\nVisakhapatnam, India\n"
        "SUMMARY\nComputer Science and Engineering student building full-stack apps.\n"
        "SKILLS\nJava, Python, SQL\n"
        "EDUCATION\nB.Tech - Computer Science and Engineering Jan 2025 - Jan 2028\n"
        "Diploma - Computer Engineering Jan 2022 - Jan 2025\n"
        "PROJECTS\nQuizMaster MERN Stack\n"
    )
    stud_profile, stud_years, _ = FastCandidateExtractor.extract_candidate_profile(student_text)
    assert stud_years == 0.0
    assert len(stud_profile.experience) == 0

    # 2. Candidate with 1 job (Jul 2025 - Present) + B.Tech (2021-2025) -> ~1.4 yrs (NOT 9.5 yrs!)
    rohan_text = (
        "Rohan Deshmukh\nJava Backend Developer\nBengaluru, Karnataka\n"
        "PROFESSIONAL SUMMARY\nBackend-focused Java Developer designing REST APIs.\n"
        "TECHNICAL SKILLS\nJava, Spring Boot, SQL, Docker\n"
        "EXPERIENCE\nJava Backend Developer — TechNova Solutions\nJul 2025 – Present\nBengaluru, Karnataka\n"
        "- Developed 15+ RESTful API endpoints using Spring Boot and PostgreSQL.\n"
        "PROJECTS\nE-Commerce Order Management\n"
        "EDUCATION\nB.Tech in Computer Science and Engineering\nBMS College of Engineering\n2021 – 2025\n"
    )
    rohan_profile, rohan_years, _ = FastCandidateExtractor.extract_candidate_profile(rohan_text)
    assert len(rohan_profile.experience) == 1
    assert 1.2 <= rohan_years <= 1.6  # Jul 2025 to Nov 2026 (~1.4 yrs), education 2021-2025 ignored

    # Must NOT satisfy 2+ yr job condition
    job_2yr = StructuredJob(job_title="Java Backend Developer", min_experience=2.0, required_skills=["Java"])
    exp_score, exp_gap = ExperienceMatcher.match_experience(rohan_profile, job_2yr)
    assert exp_score < 70.0
    assert len(exp_gap.gaps) > 0

    # 3. Candidate with internship + industrial job -> accurately merges timelines
    mid_text = (
        "Priya Nair\nHyderabad, India\n"
        "EXPERIENCE\nBackend Engineer — FinCore\nJul 2024 – Jun 2026\n- Built payment APIs in Java.\n"
        "Software Intern — FinCore\nJan 2024 – Jun 2024\n- Built REST endpoints.\n"
        "EDUCATION\nB.Tech Computer Science 2020 - 2024\n"
    )
    mid_profile, mid_years, _ = FastCandidateExtractor.extract_candidate_profile(mid_text)
    assert len(mid_profile.experience) == 2
    assert mid_years == 2.5  # 6 months intern + 24 months full-time = 30 months = 2.5 yrs
    ok_score, ok_gap = ExperienceMatcher.match_experience(mid_profile, job_2yr)
    assert ok_score == 100.0
    assert len(ok_gap.gaps) == 0
