from fastapi import APIRouter, Depends

from ..core.dependencies import get_current_user
from ..schemas import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    TokenPair,
    UserProfile,
)
from ..services.stores import (
    create_refresh_token_record,
    find_user_by_email,
    get_user_store,
    is_first_user,
    new_id,
    revoke_refresh_token,
    utcnow,
)

router = APIRouter()


@router.post("/register", response_model=TokenPair, status_code=201)
def register(data: AuthRegisterRequest) -> dict:
    from ..core.security import create_access_token, create_refresh_token, hash_password

    existing = find_user_by_email(data.email)
    if existing:
        from ..core.exceptions import ConflictError

        raise ConflictError("User with this email already exists")
    role = "owner" if is_first_user() else "user"
    password_hash = hash_password(data.password)
    user_id = new_id()
    user: dict[str, object] = {
        "id": user_id,
        "email": data.email,
        "password_hash": password_hash,
        "name": data.name,
        "role": role,
        "is_active": True,
        "created_at": utcnow(),
    }
    get_user_store().put(user)
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id)
    create_refresh_token_record(
        user_id,
        refresh_token,
        utcnow(),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/login", response_model=TokenPair)
def login(data: AuthLoginRequest) -> dict:
    from ..core.exceptions import AuthenticationError
    from ..core.security import (
        create_access_token,
        create_refresh_token,
        verify_password,
    )

    user = find_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise AuthenticationError("Invalid email or password")
    access_token = create_access_token(user["id"], user["role"])
    refresh_token = create_refresh_token(user["id"])
    create_refresh_token_record(user["id"], refresh_token, utcnow())
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/refresh", response_model=dict)
def refresh(data: AuthRefreshRequest) -> dict:
    from ..core.exceptions import AuthenticationError
    from ..core.security import create_access_token

    store = get_user_store()
    from ..services.stores import get_refresh_token_store

    rt_store = get_refresh_token_store()
    found = None
    for _, token in list(rt_store.items.items()):
        if token["token_hash"] == data.refresh_token:
            found = token
            break
    if not found:
        raise AuthenticationError("Invalid refresh token")
    user = store.get(found["user_id"])
    if not user:
        raise AuthenticationError("User not found")
    access_token = create_access_token(user["id"], user["role"])
    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@router.post("/logout", status_code=204)
def logout(
    data: AuthRefreshRequest,
    user: dict = Depends(get_current_user),
) -> None:
    revoke_refresh_token(data.refresh_token)


@router.get("/me", response_model=UserProfile)
def get_me(user: dict = Depends(get_current_user)) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "is_active": user.get("is_active", True),
        "created_at": user["created_at"],
    }
