from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.users import User, UserRole
from app.security.auth import decode_token, parse_subject_user_id


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None or authorization.strip() == "":
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1].strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>",
        )
    return parts[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User | None:
    token = _extract_bearer_token(authorization)
    if token is None:
        return None

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user_id = parse_subject_user_id(payload)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_current_role(current_user: User | None = Depends(get_current_user)) -> UserRole:
    if current_user is None:
        return UserRole.GUEST
    return current_user.role


def require_roles(*allowed_roles: UserRole) -> Callable[[UserRole], UserRole]:
    def dependency(current_role: UserRole = Depends(get_current_role)) -> UserRole:
        if current_role not in allowed_roles:
            allowed_values = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden for role '{current_role.value}'. Allowed: {allowed_values}",
            )
        return current_role

    return dependency


def get_current_user_id(current_user: User | None = Depends(get_current_user)) -> int | None:
    if current_user is None:
        return None
    return current_user.id
