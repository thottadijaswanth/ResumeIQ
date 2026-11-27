import json
import httpx
import pytest
from backend.app.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIModelNotFoundError,
    AIRateLimitError,
    AIStructuredOutputError,
    AITimeoutError,
    AIUnavailableError,
    CandidateMatchingAgent,
    LocalDeterministicEmbeddingProvider,
    MockAIProvider,
    OllamaProvider,
    OpenAIEmbeddingProvider,
    OpenAIProvider,
    get_ai_provider,
    get_embedding_provider,
    get_fallback_ai_provider,
    run_with_ai_fallback,
)
from backend.app.config import settings
from backend.app.matching.scoring_engine import ScoringEngine
from backend.app.schemas.analysis import CandidateMatchAssessment, RequirementEvidence
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.resume import ExperienceItem, StructuredResume


def _sample_resume() -> StructuredResume:
    return StructuredResume(
        name="Jordan Lee",
        email="jordan@example.com",
        summary="Backend engineer specializing in Python and FastAPI.",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience=[
            ExperienceItem(
                company="InnoTech",
                role="Backend Engineer",
                start_date="2022",
                end_date="Present",
                duration="3 years",
                responsibilities=["Built REST APIs using FastAPI and PostgreSQL."],
                technologies=["Python", "FastAPI", "PostgreSQL"],
            )
        ],
    )


def _sample_job() -> StructuredJob:
    return StructuredJob(
        job_title="Senior Backend Engineer",
        company="CloudScale",
        required_skills=["Python", "FastAPI", "Kubernetes"],
        preferred_skills=["Redis"],
        years_of_experience=3.0,
        responsibilities=["Design resilient REST APIs."],
        keywords=["Python", "FastAPI", "Kubernetes"],
    )


# ---------------------------------------------------------------------------
# Provider & Embedding Selection Tests
# ---------------------------------------------------------------------------


def test_provider_selection(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
    provider = get_ai_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://127.0.0.1:11434"
    assert provider.model == "llama3.1:8b"

    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-secret-12345")
    monkeypatch.setattr(settings, "OPENAI_BASE_URL", "https://custom.inference.local/v1")
    monkeypatch.setattr(settings, "OPENAI_MODEL", "custom-model")
    provider = get_ai_provider()
    assert isinstance(provider, OpenAIProvider)
    assert provider.base_url == "https://custom.inference.local/v1"
    assert provider.model == "custom-model"

    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    provider = get_ai_provider()
    assert isinstance(provider, MockAIProvider)


def test_invalid_provider_raises_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "unsupported_vendor")
    with pytest.raises(AIConfigurationError, match="Unsupported AI_PROVIDER"):
        get_ai_provider()

    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY"):
        get_ai_provider()


def test_embedding_provider_selection(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    assert isinstance(get_embedding_provider(), LocalDeterministicEmbeddingProvider)

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "mock")
    assert isinstance(get_embedding_provider(), LocalDeterministicEmbeddingProvider)

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "openai")
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "sk-embed-123")
    emb = get_embedding_provider()
    assert isinstance(emb, OpenAIEmbeddingProvider)

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "unknown_embed")
    with pytest.raises(AIConfigurationError, match="Unsupported EMBEDDING_PROVIDER"):
        get_embedding_provider()


# ---------------------------------------------------------------------------
# OllamaProvider Tests (Sync & Async, Error Modes, JSON Repair)
# ---------------------------------------------------------------------------


def test_ollama_success_and_structured_parsing():
    seen_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.path == "/api/chat":
            body = json.loads(request.content.decode("utf-8"))
            if body.get("format") == "json":
                payload = {
                    "name": "Jordan Lee",
                    "email": "jordan@example.com",
                    "skills": ["Python", "FastAPI"],
                }
                return httpx.Response(
                    200,
                    json={
                        "message": {"role": "assistant", "content": f"```json\n{json.dumps(payload)}\n```"},
                        "prompt_eval_count": 40,
                        "eval_count": 25,
                    },
                )
            return httpx.Response(
                200,
                json={"message": {"role": "assistant", "content": "Hello from local Ollama"}},
            )
        return httpx.Response(404)

    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="qwen2.5:7b",
        transport=httpx.MockTransport(handler),
    )

    text = provider.generate_sync("Say hello")
    assert text == "Hello from local Ollama"

    resume = provider.extract_structured_resume("Jordan Lee Python FastAPI")
    assert isinstance(resume, StructuredResume)
    assert resume.name == "Jordan Lee"
    assert "FastAPI" in resume.skills
    assert all(url.startswith("http://localhost:11434") for url in seen_urls)


@pytest.mark.asyncio
async def test_ollama_async_generate_and_structured():
    async def async_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"job_title": "ML Engineer", "required_skills": ["Python"]}),
                }
            },
        )

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="mistral:7b",
        async_transport=httpx.MockTransport(async_handler),
    )
    result = await provider.generate_structured("Extract ML job", StructuredJob)
    assert isinstance(result, StructuredJob)
    assert result.job_title == "ML Engineer"


def test_ollama_invalid_json_retry_and_failure():
    attempts = {"count": 0}

    def retry_then_succeed(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(200, json={"message": {"content": "Not valid JSON at all"}})
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"job_title": "Backend Dev", "required_skills": ["Go"]})}},
        )

    provider = OllamaProvider(transport=httpx.MockTransport(retry_then_succeed))
    job = provider.extract_structured_job("Backend Dev using Go")
    assert attempts["count"] == 2
    assert job.job_title == "Backend Dev"

    def always_bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "{broken json"}})

    bad_provider = OllamaProvider(transport=httpx.MockTransport(always_bad))
    with pytest.raises(AIStructuredOutputError):
        bad_provider.extract_structured_job("Backend Dev")


def test_ollama_timeout_unavailable_and_missing_model():
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    timeout_provider = OllamaProvider(
        max_retries=1, retry_delay=0.0, transport=httpx.MockTransport(timeout_handler)
    )
    with pytest.raises(AITimeoutError):
        timeout_provider.generate_sync("hi")

    def connect_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    down_provider = OllamaProvider(
        max_retries=1, retry_delay=0.0, transport=httpx.MockTransport(connect_handler)
    )
    with pytest.raises(AIUnavailableError, match="Cannot connect to Ollama"):
        down_provider.generate_sync("hi")

    def missing_model_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'qwen2.5:7b' not found"})

    missing_provider = OllamaProvider(
        model="qwen2.5:7b", transport=httpx.MockTransport(missing_model_handler)
    )
    with pytest.raises(AIModelNotFoundError, match="not installed"):
        missing_provider.generate_sync("hi")


# ---------------------------------------------------------------------------
# OpenAIProvider & Cloud Embeddings Tests
# ---------------------------------------------------------------------------


def test_openai_provider_success_and_error_handling():
    secret = "sk-super-secret-value-999"

    def success_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {secret}"
        assert str(request.url) == "https://custom.openai-compatible.example/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"job_title": "Platform Engineer", "required_skills": ["Docker", "Python"]}
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            },
        )

    provider = OpenAIProvider(
        api_key=secret,
        model="gpt-4o-mini",
        base_url="https://custom.openai-compatible.example/v1",
        transport=httpx.MockTransport(success_handler),
    )
    job = provider.extract_structured_job("Platform Engineer Docker Python")
    assert job.job_title == "Platform Engineer"

    def auth_fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"Invalid key {secret}"}})

    auth_provider = OpenAIProvider(
        api_key=secret, transport=httpx.MockTransport(auth_fail_handler)
    )
    with pytest.raises(AIAuthenticationError) as exc_info:
        auth_provider.generate_sync("hello")
    assert secret not in str(exc_info.value)

    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    rl_provider = OpenAIProvider(
        api_key=secret,
        max_retries=1,
        retry_delay=0.0,
        transport=httpx.MockTransport(rate_limit_handler),
    )
    with pytest.raises(AIRateLimitError):
        rl_provider.generate_sync("hello")

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    to_provider = OpenAIProvider(
        api_key=secret,
        max_retries=0,
        transport=httpx.MockTransport(timeout_handler),
    )
    with pytest.raises(AITimeoutError):
        to_provider.generate_sync("hello")


def test_openai_embedding_provider():
    def embed_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/embeddings"
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]},
        )

    emb = OpenAIEmbeddingProvider(
        api_key="sk-embed-test", transport=httpx.MockTransport(embed_handler)
    )
    vec = emb.get_embedding("Python backend developer")
    assert vec == [0.1, 0.2, 0.3]


# ---------------------------------------------------------------------------
# CandidateMatchingAgent & Deterministic Matching Parity Tests
# ---------------------------------------------------------------------------


def test_candidate_matching_agent_across_providers():
    resume = _sample_resume()
    job = _sample_job()
    evidence = [
        RequirementEvidence(
            requirement="Responsibility: Design resilient REST APIs.",
            match_status="Strong match",
            evidence="Built REST APIs using FastAPI and PostgreSQL.",
            confidence=0.88,
        )
    ]

    agent_payload = {
        "candidate_id": "cand-1",
        "required_skill_assessment": [
            {"skill": "Python", "status": "strong", "evidence": "Used Python in Backend Engineer role", "confidence": 0.95},
            {"skill": "FastAPI", "status": "strong", "evidence": "Built REST APIs using FastAPI", "confidence": 0.93},
            {"skill": "Kubernetes", "status": "not_found", "evidence": "", "confidence": 0.0},
        ],
        "preferred_skill_assessment": [
            {"skill": "Redis", "status": "not_found", "evidence": "", "confidence": 0.0}
        ],
        "experience_assessment": {
            "relevant_years": 3.0,
            "required_years": 3.0,
            "summary": "Meets 3 years requirement.",
            "evidence": ["Backend Engineer at InnoTech (3 years)"],
            "status": "strong",
        },
        "responsibility_match": {
            "matched_responsibilities": ["Design resilient REST APIs."],
            "missing_responsibilities": [],
            "evidence": ["Built REST APIs using FastAPI and PostgreSQL."],
            "status": "strong",
        },
        "seniority_match": {
            "target_level": "Senior",
            "candidate_level": "Backend Engineer",
            "status": "partial",
            "evidence": "Backend Engineer",
        },
        "missing_requirements": ["Kubernetes"],
        "contradictions": [],
        "recommendation": "moderate_match",
        "confidence": 0.82,
    }

    ollama = OllamaProvider(
        model="qwen2.5:7b",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"message": {"content": json.dumps(agent_payload)}})
        ),
    )
    openai = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200, json={"choices": [{"message": {"content": json.dumps(agent_payload)}}]}
            )
        ),
    )
    mock = MockAIProvider()

    for provider in (ollama, openai, mock):
        assessment = CandidateMatchingAgent(provider).evaluate(
            candidate_id="cand-1",
            resume=resume,
            job=job,
            relevant_evidence=evidence,
        )
        assert isinstance(assessment, CandidateMatchAssessment)
        assert assessment.candidate_id == "cand-1"
        assert assessment.provider == provider.provider_name
        missing_k8s = [s for s in assessment.required_skill_assessment if s.skill.lower() == "kubernetes"]
        assert missing_k8s and missing_k8s[0].status == "not_found"


def test_deterministic_scoring_survives_ai_provider_failure(monkeypatch):
    def down_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    down_ollama = OllamaProvider(
        max_retries=0, transport=httpx.MockTransport(down_handler)
    )
    monkeypatch.setattr("backend.app.matching.scoring_engine.run_with_ai_fallback", lambda name, fn: (_ for _ in ()).throw(AIUnavailableError("down", provider="ollama")))

    result, recommendations = ScoringEngine.analyze_resume_against_job(
        resume=_sample_resume(),
        job=_sample_job(),
        raw_resume_text="Jordan Lee Python FastAPI PostgreSQL",
        candidate_id="cand-1",
    )
    # Deterministic engine scores are still produced reliably
    assert 0.0 <= result.overall_score <= 100.0
    assert result.skill_score > 0.0
    assert result.ai_matching_assessment is None
    assert recommendations == []


# ---------------------------------------------------------------------------
# Fallback & Privacy Guard Tests
# ---------------------------------------------------------------------------


def test_fallback_respects_privacy_and_configuration(monkeypatch):
    # 1. Privacy: ollama must NEVER silently fall back to openai
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", True)
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "openai")
    monkeypatch.setattr(settings, "AI_ALLOW_CLOUD_FALLBACK", False)
    assert get_fallback_ai_provider("ollama") is None

    # 2. Ollama -> mock fallback works locally when enabled
    monkeypatch.setattr(settings, "AI_FALLBACK_PROVIDER", "mock")
    fallback = get_fallback_ai_provider("ollama")
    assert isinstance(fallback, MockAIProvider)

    down_ollama = OllamaProvider(
        max_retries=0,
        transport=httpx.MockTransport(lambda req: (_ for _ in ()).throw(httpx.ConnectError("down", request=req))),
    )
    job, used_fallback = run_with_ai_fallback(
        "extract_structured_job",
        lambda p: p.extract_structured_job("Senior Python Developer with FastAPI"),
        primary_provider=down_ollama,
    )
    assert used_fallback is True
    assert isinstance(job, StructuredJob)

    # 3. Disabled fallback raises controlled provider error
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", False)
    with pytest.raises(AIUnavailableError):
        run_with_ai_fallback(
            "extract_structured_job",
            lambda p: p.extract_structured_job("Senior Python Developer"),
            primary_provider=down_ollama,
        )


# ---------------------------------------------------------------------------
# /api/ai/health Endpoint Integration Tests
# ---------------------------------------------------------------------------


def test_ai_health_endpoint_statuses(client, monkeypatch):
    # 1. Mock mode
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "mock"
    assert body["status"] == "healthy"
    assert body["mode"] == "mock"

    # 2. Healthy Ollama mode
    monkeypatch.setattr(settings, "AI_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
    healthy_ollama = OllamaProvider(
        model="qwen2.5:7b",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})
        ),
    )
    monkeypatch.setattr("backend.app.ai.get_ai_provider", lambda: healthy_ollama)
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    assert res.json()["provider"] == "ollama"
    assert res.json()["status"] == "healthy"
    assert res.json()["model"] == "qwen2.5:7b"

    # 3. Ollama running, model missing
    missing_model_ollama = OllamaProvider(
        model="qwen2.5:7b",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"models": [{"name": "llama3:latest"}]})
        ),
    )
    monkeypatch.setattr("backend.app.ai.get_ai_provider", lambda: missing_model_ollama)
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    assert res.json()["status"] == "unavailable"
    assert "not installed" in res.json()["message"]

    # 4. Ollama unreachable
    down_ollama = OllamaProvider(
        model="qwen2.5:7b",
        transport=httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("refused", request=req))
        ),
    )
    monkeypatch.setattr("backend.app.ai.get_ai_provider", lambda: down_ollama)
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    assert res.json()["status"] == "unavailable"
    assert "Cannot connect to Ollama" in res.json()["message"]

    # 5. OpenAI mode (verify secrets never exposed)
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    secret = "sk-never-leak-this-key"
    monkeypatch.setattr(settings, "OPENAI_API_KEY", secret)
    healthy_openai = OpenAIProvider(
        api_key=secret,
        model="gpt-4o-mini",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"data": []})),
    )
    monkeypatch.setattr("backend.app.ai.get_ai_provider", lambda: healthy_openai)
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    assert res.json()["provider"] == "openai"
    assert res.json()["status"] == "healthy"
    assert secret not in res.text


def test_auto_provider_prefers_online_then_local_ollama_offline(monkeypatch):
    from backend.app.ai import build_ai_provider

    monkeypatch.setattr(settings, "AI_PROVIDER", "auto")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-auto-test")

    # 1. Online reachable -> picks OpenAI
    online_openai = OpenAIProvider(
        api_key="sk-auto-test",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"data": []})),
    )
    local_ollama = OllamaProvider(
        model="qwen3:1.7b",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"models": [{"name": "qwen3:1.7b"}]})
        ),
    )
    monkeypatch.setattr("backend.app.ai._build_openai_provider", lambda: online_openai)
    monkeypatch.setattr("backend.app.ai._build_ollama_provider", lambda: local_ollama)

    picked_online = build_ai_provider("auto")
    assert isinstance(picked_online, OpenAIProvider)

    # 2. Offline (OpenAI unreachable) + Ollama started -> automatically selects Ollama!
    offline_openai = OpenAIProvider(
        api_key="sk-auto-test",
        transport=httpx.MockTransport(
            lambda req: (_ for _ in ()).throw(httpx.ConnectError("offline", request=req))
        ),
    )
    monkeypatch.setattr("backend.app.ai._build_openai_provider", lambda: offline_openai)
    picked_offline = build_ai_provider("auto")
    assert isinstance(picked_offline, OllamaProvider)


def test_ai_mode_switch_endpoint(client, auth_headers, monkeypatch):
    # Prevent test from modifying workspace .env on disk
    monkeypatch.setattr("backend.app.api.ai.set_ai_provider_mode", lambda p, persist_env=True: {
        "provider": p,
        "configured_provider": p,
        "status": "healthy",
        "available": True,
        "model": "qwen3:1.7b" if p == "ollama" else "gpt-4o-mini",
        "mode": "local" if p == "ollama" else "cloud",
        "embedding_provider": "local",
        "fallback_enabled": False,
        "fallback_provider": None,
        "message": "ok",
    })
    res = client.post("/api/ai/mode", headers=auth_headers, json={"provider": "ollama"})
    assert res.status_code == 200
    assert res.json()["provider"] == "ollama"


def test_batch_upload_survives_embedding_429_fallback(client, auth_headers, monkeypatch):
    import fitz
    import io

    failing_emb = OpenAIEmbeddingProvider(
        api_key="sk-quota-exhausted",
        transport=httpx.MockTransport(lambda req: httpx.Response(429, json={"error": "insufficient_quota"})),
    )
    monkeypatch.setattr("backend.app.services.resume_service.get_embedding_provider", lambda: failing_emb)

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Jane Doe\njane@example.com\nSkills: Python, Java, SQL\n4 years of experience")
    pdf_bytes = doc.tobytes()
    doc.close()

    res = client.post(
        "/api/resumes/batch",
        headers=auth_headers,
        files=[("files", ("jane.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
    )
    assert res.status_code == 201
    assert res.json()["processed_count"] == 1
    assert res.json()["failed_count"] == 0

