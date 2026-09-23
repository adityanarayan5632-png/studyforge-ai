"""Supabase JWT verification for FastAPI."""

import os
import httpx
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL")
SUPABASE_ISSUER = os.getenv("SUPABASE_ISSUER")

if not SUPABASE_JWKS_URL or not SUPABASE_ISSUER:
    raise RuntimeError("SUPABASE_JWKS_URL and SUPABASE_ISSUER must be set in environment")


class SupabaseUser(BaseModel):
    """Authenticated Supabase user claims."""
    sub: str
    email: Optional[str] = None
    role: str = "authenticated"
    aud: str = "authenticated"


class JWKSCache:
    """Cache for JWKS keys."""

    def __init__(self, jwks_url: str):
        self.jwks_url = jwks_url
        self._keys: Optional[dict] = None

    async def get_keys(self) -> dict:
        if self._keys is None:
            await self._refresh()
        return self._keys

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            self._keys = response.json()

    def clear(self) -> None:
        self._keys = None


_jwks_cache = JWKSCache(SUPABASE_JWKS_URL)


async def get_signing_key(token: str) -> dict:
    """Extract the signing key from JWKS based on token's kid header."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise JWTError("Token missing kid header")

    jwks = await _jwks_cache.get_keys()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    _jwks_cache.clear()
    jwks = await _jwks_cache.get_keys()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError(f"Signing key not found for kid: {kid}")


async def verify_supabase_token(token: str) -> SupabaseUser:
    """Verify a Supabase access token and return user claims."""
    try:
        signing_key = await get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=SUPABASE_ISSUER,
        )
        return SupabaseUser(**payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> SupabaseUser:
    """FastAPI dependency to get the current authenticated Supabase user."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await verify_supabase_token(credentials.credentials)


async def get_current_user_id(
    user: SupabaseUser = Depends(get_current_user),
) -> str:
    """FastAPI dependency to get just the current user's Supabase ID."""
    return user.sub