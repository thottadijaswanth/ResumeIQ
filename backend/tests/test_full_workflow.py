import fitz
import io


def test_full_application_workflow(client):
    # 1. Register
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "fullworkflow@example.com",
            "password": "Password123!",
            "full_name": "Full Workflow User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload synthetic PDF Resume
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 72),
        "Samantha Ray\nSenior Software Engineer\nsamantha@example.com\n"
        "Skills: Python, FastAPI, Docker, PostgreSQL, React, Git\n"
        "Experience: Senior Engineer at Tech Corp (3 years). Built REST APIs with FastAPI and Docker.\n"
        "Education: Bachelor of Science in Computer Science.\n",
    )
    pdf_bytes = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/api/resumes",
        headers=headers,
        data={"name": "Samantha Senior Resume"},
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # 3. Create Job Description
    job_res = client.post(
        "/api/jobs",
        headers=headers,
        json={
            "title": "Senior Backend Developer",
            "company": "NextGen Software",
            "location": "Remote",
            "description": (
                "We are seeking a Senior Backend Developer with 3+ years experience.\n"
                "Required skills: Python, FastAPI, PostgreSQL, Docker.\n"
                "Preferred skills: Redis, AWS.\n"
                "Responsibilities: Build scalable backend systems and REST APIs.\n"
            ),
        },
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 4. Run Analysis
    analysis_res = client.post(
        "/api/analysis",
        headers=headers,
        json={"resume_id": resume_id, "job_id": job_id},
    )
    assert analysis_res.status_code == 201
    analysis_data = analysis_res.json()
    analysis_id = analysis_data["id"]
    assert analysis_data["overall_score"] > 60.0
    assert "analysis_result" in analysis_data
    assert len(analysis_data["recommendations"]) > 0

    # 5. Tailor Resume
    tailor_res = client.post(f"/api/analysis/{analysis_id}/tailor-resume", headers=headers)
    assert tailor_res.status_code == 200
    tailored = tailor_res.json()
    assert "tailored_summary" in tailored
    assert len(tailored["suggested_reordered_skills"]) > 0

    # 6. Generate Cover Letter
    cover_res = client.post(
        f"/api/analysis/{analysis_id}/cover-letter",
        headers=headers,
        json={"tone": "Confident"},
    )
    assert cover_res.status_code == 200
    cover_data = cover_res.json()
    assert "cover_letter_text" in cover_data
    assert "NextGen Software" in cover_data["cover_letter_text"]

    # 7. Track Application
    app_res = client.post(
        "/api/applications",
        headers=headers,
        json={
            "job_id": job_id,
            "resume_id": resume_id,
            "status": "Applied",
            "notes": "Submitted tailored resume and cover letter via portal.",
        },
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 8. Update Application Status
    update_app = client.patch(
        f"/api/applications/{app_id}",
        headers=headers,
        json={"status": "Interview", "notes": "Technical screen scheduled for Thursday."},
    )
    assert update_app.status_code == 200
    assert update_app.json()["status"] == "Interview"

    # 9. Get Dashboard Application Stats
    stats_res = client.get("/api/applications/stats/summary", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_applications"] == 1
    assert stats["status_breakdown"]["Interview"] == 1

