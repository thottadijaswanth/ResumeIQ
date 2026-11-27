def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_user_registration_success(client):
    res = client.post(
        "/api/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "Password123!",
            "full_name": "Jane Candidate",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "candidate@example.com"
    assert data["user"]["full_name"] == "Jane Candidate"


def test_duplicate_registration_fails(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "First User",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_login_success(client):
    # Register first
    client.post(
        "/api/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "Password123!",
            "full_name": "Login User",
        },
    )

    # Login
    res = client.post(
        "/api/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "Password123!",
        },
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_invalid_password_fails(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "user@example.com",
            "password": "CorrectPassword123!",
            "full_name": "Test User",
        },
    )

    res = client.post(
        "/api/auth/login",
        json={
            "email": "user@example.com",
            "password": "WrongPassword!",
        },
    )
    assert res.status_code == 401


def test_current_user_profile(client, auth_headers):
    res = client.get("/api/users/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "testuser@example.com"


def test_unauthorized_access_fails(client):
    res = client.get("/api/users/me")
    assert res.status_code == 401

