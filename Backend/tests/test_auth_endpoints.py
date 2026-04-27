from urllib.parse import parse_qs, urlparse

from app.models import OAuthAccount, User, UserRole
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


def test_refresh_returns_new_access_token(client, db_session):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "RefreshPass123"},
    )
    assert register_response.status_code == 201
    refresh_token = register_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


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


def test_google_callback_redirects_to_frontend_when_configured(client, monkeypatch):
    _set_google_env(monkeypatch)
    monkeypatch.setenv("FRONTEND_GOOGLE_SUCCESS_REDIRECT_URL", "http://frontend.local/auth/google/callback")

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
            "sub": "google-user-redirect",
            "email": "redirect-user@example.com",
            "name": "Redirect User",
            "email_verified": True,
        },
    )

    response = client.get(
        f"/api/v1/auth/google/callback?code=test-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    parsed = urlparse(location)
    fragment = parse_qs(parsed.fragment)
    assert parsed.netloc == "frontend.local"
    assert fragment["access_token"][0]
    assert fragment["refresh_token"][0]
    assert fragment["email"][0] == "redirect-user@example.com"
    assert fragment["role"][0] == UserRole.STUDENT.value


def test_forgot_password_returns_generic_message_for_unknown_email(client, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_DEBUG_RETURN_TOKEN", "true")

    response = client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "unknown-user@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "If the account exists" in payload["message"]
    assert payload["reset_token"] is None


def test_forgot_password_sends_email_when_smtp_is_configured(client, db_session, monkeypatch):
    monkeypatch.setenv("FRONTEND_PASSWORD_RESET_URL", "http://frontend.local/auth/reset-password")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_STARTTLS", "false")

    captured = {}

    def _fake_send_password_reset_email(*, to_email, reset_url, settings):
        captured["to_email"] = to_email
        captured["reset_url"] = reset_url
        captured["host"] = settings.host

    monkeypatch.setattr(auth_routes, "send_password_reset_email", _fake_send_password_reset_email)

    user = User(
        email="mailer@example.com",
        full_name="Mailer User",
        password_hash=hash_password("OldPass123"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "mailer@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reset_token"] is None
    assert captured["to_email"] == "mailer@example.com"
    assert captured["host"] == "smtp.example.test"
    assert "token=" in captured["reset_url"]


def test_forgot_and_reset_password_flow_with_debug_token(client, db_session, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_DEBUG_RETURN_TOKEN", "true")
    monkeypatch.setenv("FRONTEND_PASSWORD_RESET_URL", "http://frontend.local/auth/reset-password")

    user = User(
        email="reset-me@example.com",
        full_name="Reset Me",
        password_hash=hash_password("OldPass123"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    forgot_response = client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "reset-me@example.com"},
    )
    assert forgot_response.status_code == 200
    forgot_payload = forgot_response.json()
    assert forgot_payload["reset_token"]
    assert "token=" in forgot_payload["reset_url"]

    reset_response = client.post(
        "/api/v1/auth/password/reset",
        json={"token": forgot_payload["reset_token"], "new_password": "NewPass123"},
    )
    assert reset_response.status_code == 200
    assert "successfully" in reset_response.json()["message"]

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-me@example.com", "password": "OldPass123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-me@example.com", "password": "NewPass123"},
    )
    assert new_login.status_code == 200


def test_password_reset_token_cannot_be_reused(client, db_session, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_DEBUG_RETURN_TOKEN", "true")

    user = User(
        email="reuse-token@example.com",
        full_name="Reuse Token",
        password_hash=hash_password("InitialPass123"),
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    db_session.commit()

    forgot_response = client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "reuse-token@example.com"},
    )
    token = forgot_response.json()["reset_token"]

    first_reset = client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "FirstReset123"},
    )
    assert first_reset.status_code == 200

    second_reset = client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "SecondReset123"},
    )
    assert second_reset.status_code == 400
