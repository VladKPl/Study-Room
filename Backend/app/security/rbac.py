from typing import Callable

from fastapi import Depends, Header, HTTPException

from app.models.users import UserRole


def get_current_role(x_role: str | None = Header(default=None, alias="X-Role")) -> UserRole:
    raw_role = (x_role or UserRole.GUEST.value).strip().lower()
    try:
        return UserRole(raw_role)
    except ValueError as exc:
        allowed_values = ", ".join(role.value for role in UserRole)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-Role value. Allowed: {allowed_values}",
        ) from exc


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


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> int | None:
    if x_user_id is None or x_user_id.strip() == "":
        return None

    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-User-Id must be an integer") from exc

    if user_id <= 0:
        raise HTTPException(status_code=400, detail="X-User-Id must be greater than 0")

    return user_id
