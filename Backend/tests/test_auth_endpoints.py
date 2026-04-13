from urllib.parse import parse_qs, urlparse

from app.models import OAuthAccount, RefreshToken, User, UserRole
from app.routes import auth as auth_routes
from app.security.auth import hash_password


def test_register_creates_student_and_returns_tokens(client, db_session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new_user@example.com",
            "password": "StrongPass123",
            "full_name": "New User",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["email"] == "new_user@example.com"
    assert payload["user"]["role"] == UserRole.STUDENT.value

    user = db_session.query(User).filter(User.email == "new_user@example.com").first()
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != "StrongPass123"


def test_register_duplicate_email_returns_409(client, db_session):
    existing = User(
        email="dup@example.com",
        full_name="Dup User",
        password_hash=hash_password("Secret123"),
        role=UserRole.STUDENT,
    )
    db_session.add(existing)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "AnotherSecret123"},
    )

    assert response.status_code == 409


def test_login_success_returns_tokens(client, db_session):
    user = User(
        email="login@example.com",
        full_name="Login User",
        password_hash=hash_password("GoodPass123"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "GoodPass123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["email"] == "login@example.com"


def test_refresh_rotates_token_and_revokes_old(client, db_session):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "RefreshPass123"},
    )
    assert register_response.status_code == 201
    initial_refresh_token = register_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh_token})

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["refresh_token"] != initial_refresh_token

    old_token = db_session.query(RefreshToken).filter(
        RefreshToken.token == initial_refresh_token
    ).first()
    assert old_token is not None
    assert old_token.revoked_at is not None


def test_refresh_reuse_of_revoked_token_returns_401(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "revoke@example.com", "password": "RefreshPass123"},
    )
    assert register_response.status_code == 201
    initial_refresh_token = register_response.json()["refresh_token"]

    first_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh_token})
    assert first_refresh.status_code == 200

    second_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh_token})
    assert second_refresh.status_code == 401


def test_logout_revokes_user_refresh_tokens(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "RefreshPass123"},
    )
    assert register_response.status_code == 201
    payload = register_response.json()

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["revoked_count"] >= 1

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refresh_response.status_code == 401


def _set_google_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://testserver/api/v1/auth/google/callback")


def test_google_login_redirects_to_google(client, monkeypatch):
    _set_google_env(monkeypatch)

    response = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert "accounts.google.com" in parsed.netloc
    assert query["client_id"][0] == "google-client-id"
    assert query["redirect_uri"][0] == "http://testserver/api/v1/auth/google/callback"
    assert query["response_type"][0] == "code"
    assert query["scope"][0] == "openid email profile"
    assert "oauth_google_state=" in response.headers.get("set-cookie", "")


def test_google_callback_creates_user_and_links_oauth_account(client, db_session, monkeypatch):
    _set_google_env(monkeypatch)

    login_response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

    monkeypatch.setattr(
        auth_routes,
        "_exchange_google_code_for_token",
        lambda **kwargs: {"access_token": "google-access-token"},
    )
    monkeypatch.setattr(
        auth_routes,
        "_fetch_google_userinfo",
        lambda access_token: {
            "sub": "google-user-123",
            "email": "oauth-user@example.com",
            "name": "OAuth User",
            "email_verified": True,
        },
    )

    response = client.get(f"/api/v1/auth/google/callback?code=test-code&state={state}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["user"]["email"] == "oauth-user@example.com"

    user = db_session.query(User).filter(User.email == "oauth-user@example.com").first()
    assert user is not None
    oauth = db_session.query(OAuthAccount).filter(
        OAuthAccount.provider == "google",
        OAuthAccount.provider_user_id == "google-user-123",
    ).first()
    assert oauth is not None
    assert oauth.user_id == user.id


def test_google_callback_rejects_invalid_state(client, monkeypatch):
    _set_google_env(monkeypatch)

    response = client.get("/api/v1/auth/google/callback?code=test-code&state=bad-state")

    assert response.status_code == 400
