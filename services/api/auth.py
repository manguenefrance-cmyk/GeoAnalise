from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .config import settings
from .db import Membership, Organization, User, get_db

bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    if not credentials:
        raise HTTPException(401, "AUTH_REQUIRED")
    token = credentials.credentials
    if token.startswith("test:"):
        if settings.app_env != "test":
            raise HTTPException(401, "INVALID_TOKEN")
        name = token[5:]
        if not name or len(name) > 80 or not name.replace("-", "").isalnum():
            raise HTTPException(401, "INVALID_TOKEN")
        claims = {"uid": f"test:{name}", "email": f"{name}@example.test", "name": name}
    else:
        try:
            import firebase_admin
            from firebase_admin import auth

            if not firebase_admin._apps:
                firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
            claims = auth.verify_id_token(token, check_revoked=True)
            if not claims.get("email_verified"):
                raise HTTPException(403, "EMAIL_NOT_VERIFIED")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(401, "INVALID_TOKEN") from exc
    user = db.scalar(select(User).where(User.firebase_uid == claims["uid"]))
    if not user:
        try:
            org = Organization(name=f"{claims.get('name', 'Personal')} workspace")
            db.add(org)
            db.flush()
            user = User(
                firebase_uid=claims["uid"],
                email=claims.get("email", ""),
                display_name=claims.get("name", ""),
                organization_id=org.id,
            )
            db.add(user)
            db.flush()
            db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.scalar(select(User).where(User.firebase_uid == claims["uid"]))
    if not db.scalar(
        select(Membership.id).where(
            Membership.user_id == user.id, Membership.organization_id == user.organization_id
        )
    ):
        raise HTTPException(403, "MEMBERSHIP_REQUIRED")
    return user


def require_editor(db, user):
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id, Membership.organization_id == user.organization_id
        )
    )
    if not member or member.role not in ("owner", "editor"):
        raise HTTPException(403, "EDIT_ACCESS_REQUIRED")
