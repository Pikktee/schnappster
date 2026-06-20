"""Auth-Routen: Selbstregistrierung (mit Admin-Freischaltung) und Login."""

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.auth import create_access_token
from app.core.db import SessionDep
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.user import LoginRequest, RegisterRequest, TokenResponse, User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, session: SessionDep) -> dict:
    """Legt ein inaktives Konto an; ein Admin muss es vor dem ersten Login freischalten."""
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mit dieser E-Mail existiert bereits ein Konto.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=False,
    )
    session.add(user)
    session.commit()
    return {"detail": "Konto angelegt. Ein Administrator muss es noch freischalten."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    """Prueft E-Mail/Passwort und gibt bei freigeschaltetem Konto ein JWT zurueck."""
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-Mail oder Passwort ist falsch.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto ist noch nicht freigeschaltet.",
        )
    return TokenResponse(access_token=create_access_token(user))
