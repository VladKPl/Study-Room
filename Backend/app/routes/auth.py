import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.password_reset_tokens import PasswordResetToken
from app.models.users import OAuthAccount, User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenPairResponse,
)
from app.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    parse_subject_user_id,
    verify_password,
)
from app.services.email import SMTPSettings, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_STATE_COOKIE = "oauth_google_state"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _password_reset_ttl_minutes() -> int:
    return int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))


def _frontend_google_success_redirect_url() -> str | None:
    value = os.getenv("FRONTEND_GOOGLE_SUCCESS_REDIRECT_URL", "").strip()
    return value or None


def _frontend_google_error_redirect_url() -> str | None:
    value = os.getenv("FRONTEND_GOOGLE_ERROR_REDIRECT_URL", "").strip()
    return value or None


def _frontend_password_reset_url() -> str | None:
    value = os.getenv("FRONTEND_PASSWORD_RESET_URL", "").strip()
    return value or None


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError:
        return default


def _smtp_settings() -> SMTPSettings | None:
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not host or not from_email:
        return None

    username = os.getenv("SMTP_USERNAME", "").strip() or None
    password = os.getenv("SMTP_PASSWORD", "").strip() or None
    from_name = os.getenv("SMTP_FROM_NAME", "").strip() or None

    return SMTPSettings(
        host=host,
        port=_int_env("SMTP_PORT", 587),
        username=username,
        password=password,
        from_email=from_email,
        from_name=from_name,
        starttls=_truthy_env("SMTP_STARTTLS", "true"),
        use_ssl=_truthy_env("SMTP_USE_SSL", "false"),
        timeout_seconds=_float_env("SMTP_TIMEOUT_SECONDS", 10.0),
    )


def _with_query_params(url: str, params: dict[str, str]) -> str:
    split = urlsplit(url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def _with_fragment_params(url: str, params: dict[str, str]) -> str:
    split = urlsplit(url)
    fragment_query = urlencode(params)
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, fragment_query))


def _hash_reset_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


def _send_password_reset_email_task(to_email: str, reset_url: str) -> None:
    settings = _smtp_settings()
    if settings is None:
        return
    try:
        send_password_reset_email(
            to_email=to_email,
            reset_url=reset_url,
            settings=settings,
        )
    except Exception:
        logger.exception("Password reset email failed for %s", to_email)


def _google_error_redirect_response(error_code: str) -> RedirectResponse | None:
    redirect_base = _frontend_google_error_redirect_url()
    if not redirect_base:
        return None
    redirect_url = _with_query_params(redirect_base, {"error": error_code})
    redirect_response = RedirectResponse(url=redirect_url, status_code=302)
    redirect_response.delete_cookie(key=GOOGLE_STATE_COOKIE)
    return redirect_response


def _google_success_redirect_response(token_pair: TokenPairResponse) -> RedirectResponse | None:
    redirect_base = _frontend_google_success_redirect_url()
    if not redirect_base:
        return None
    user_payload = {
        "id": str(token_pair.user.id),
        "email": str(token_pair.user.email),
        "full_name": token_pair.user.full_name,
        "role": token_pair.user.role.value,
    }
    redirect_url = _with_fragment_params(
        redirect_base,
        {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": token_pair.token_type,
            "user_id": user_payload["id"],
            "email": user_payload["email"],
            "full_name": user_payload["full_name"],
            "role": user_payload["role"],
        },
    )
    redirect_response = RedirectResponse(url=redirect_url, status_code=302)
    redirect_response.delete_cookie(key=GOOGLE_STATE_COOKIE)
    return redirect_response


def _issue_token_pair(user: User) -> TokenPairResponse:
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
    )


def _get_google_oauth_config() -> tuple[str, str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    return client_id, client_secret, redirect_uri


def _exchange_google_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google token exchange failed")
    payload = response.json()
    if not payload.get("access_token"):
        raise HTTPException(status_code=400, detail="Google token response is invalid")
    return payload


def _fetch_google_userinfo(access_token: str) -> dict:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google userinfo request failed")
    payload = response.json()
    if not payload.get("sub") or not payload.get("email"):
        raise HTTPException(status_code=400, detail="Google userinfo response is invalid")
    return payload


@router.get("/google/login")
def google_login():
    client_id, _, redirect_uri = _get_google_oauth_config()
    state = secrets.token_urlsafe(32)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    response = RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query}", status_code=302)
    response.set_cookie(
        key=GOOGLE_STATE_COOKIE,
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/google/callback", response_model=TokenPairResponse)
def google_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    request_state = request.cookies.get(GOOGLE_STATE_COOKIE)
    if not request_state or state != request_state:
        redirect_response = _google_error_redirect_response("invalid_oauth_state")
        if redirect_response is not None:
            return redirect_response
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        client_id, client_secret, redirect_uri = _get_google_oauth_config()
        token_payload = _exchange_google_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        google_user = _fetch_google_userinfo(token_payload["access_token"])
    except HTTPException:
        redirect_response = _google_error_redirect_response("google_oauth_failed")
        if redirect_response is not None:
            return redirect_response
        raise
    provider = "google"
    provider_user_id = str(google_user["sub"])
    normalized_email = _normalize_email(google_user["email"])
    full_name = google_user.get("name") or normalized_email.split("@")[0]
    email_verified = bool(google_user.get("email_verified"))

    oauth_account = db.query(OAuthAccount).filter(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    ).first()

    if oauth_account:
        user = oauth_account.user
    else:
        user = db.query(User).filter(User.email == normalized_email).first()
        if not user:
            user = User(
                email=normalized_email,
                full_name=full_name,
                role=UserRole.STUDENT,
                is_email_verified=email_verified,
            )
            db.add(user)
            db.flush()
        elif email_verified and not user.is_email_verified:
            user.is_email_verified = True

        db.add(
            OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=normalized_email,
            )
        )

    if not user.is_active:
        redirect_response = _google_error_redirect_response("user_inactive")
        if redirect_response is not None:
            return redirect_response
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    db.commit()
    db.refresh(user)
    response.delete_cookie(key=GOOGLE_STATE_COOKIE)
    token_pair = _issue_token_pair(user)
    redirect_response = _google_success_redirect_response(token_pair)
    if redirect_response is not None:
        return redirect_response
    return token_pair


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    normalized_email = _normalize_email(payload.email)
    exists = db.query(User).filter(User.email == normalized_email).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = User(
        email=normalized_email,
        full_name=(payload.full_name or normalized_email.split("@")[0]),
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token_pair(user)


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return _issue_token_pair(user)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = parse_subject_user_id(decoded)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(user.id, user.role)
    return AccessTokenResponse(access_token=access_token)


@router.post("/password/forgot", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    normalized_email = _normalize_email(payload.email)
    generic_message = "If the account exists, password reset instructions were generated"
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not user.is_active:
        return ForgotPasswordResponse(message=generic_message)

    now = datetime.now(timezone.utc)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    raw_token = secrets.token_urlsafe(48)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=now + timedelta(minutes=_password_reset_ttl_minutes()),
        )
    )
    db.commit()

    reset_url = None
    frontend_reset_url = _frontend_password_reset_url()
    if frontend_reset_url:
        reset_url = _with_query_params(frontend_reset_url, {"token": raw_token})
        background_tasks.add_task(
            _send_password_reset_email_task,
            to_email=user.email,
            reset_url=reset_url,
        )

    if not _truthy_env("PASSWORD_RESET_DEBUG_RETURN_TOKEN"):
        return ForgotPasswordResponse(message=generic_message)

    return ForgotPasswordResponse(
        message=generic_message,
        reset_token=raw_token,
        reset_url=reset_url,
    )


@router.post("/password/reset", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    token_hash = _hash_reset_token(payload.token)
    token_row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).first()
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or expired",
        )

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user or not user.is_active:
        token_row.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is invalid or expired",
        )

    user.password_hash = hash_password(payload.new_password)
    token_row.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != token_row.id,
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return ResetPasswordResponse(message="Password has been reset successfully")
