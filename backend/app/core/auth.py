from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import jwt
from jwt import PyJWKClient
from functools import lru_cache
import structlog

from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import User

logger = structlog.get_logger()
settings = get_settings()

security = HTTPBearer()


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    jwks_url = f"{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


async def verify_clerk_token(token: str) -> dict:
    """Verify Clerk JWT and return payload."""
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate request and return current user, creating if needed."""
    payload = await verify_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-provision user from Clerk token claims
        email = payload.get("email", "")
        name = (
            payload.get("name")
            or f"{payload.get('given_name', '')} {payload.get('family_name', '')}".strip()
            or email.split("@")[0]
        )
        user = User(
            clerk_id=clerk_id,
            email=email,
            name=name,
            avatar_url=payload.get("picture"),
        )
        db.add(user)
        await db.flush()
        logger.info("New user auto-provisioned", clerk_id=clerk_id, email=email)

    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Returns user if authenticated, None otherwise."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = await verify_clerk_token(token)
        clerk_id = payload.get("sub")
        if not clerk_id:
            return None
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        return result.scalar_one_or_none()
    except HTTPException:
        return None


# Clerk webhook handler for user sync
async def verify_clerk_webhook(request: Request) -> dict:
    """Verify Clerk webhook signature."""
    from svix import Webhook
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(status_code=400, detail="Missing webhook headers")

    body = await request.body()
    webhook = Webhook(settings.CLERK_SECRET_KEY)
    try:
        event = webhook.verify(
            body,
            {"svix-id": svix_id, "svix-timestamp": svix_timestamp, "svix-signature": svix_signature},
        )
        return event
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
