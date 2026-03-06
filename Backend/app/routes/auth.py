import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import OAuthAccount, User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
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

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_STATE_COOKIE = "oauth_google_state"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


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
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    client_id, client_secret, redirect_uri = _get_google_oauth_config()
    token_payload = _exchange_google_code_for_token(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    google_user = _fetch_google_userinfo(token_payload["access_token"])
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    db.commit()
    db.refresh(user)
    response.delete_cookie(key=GOOGLE_STATE_COOKIE)
    return _issue_token_pair(user)


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
