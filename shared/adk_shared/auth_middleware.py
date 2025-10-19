"""Authentication middleware for ADK deployments.

This module provide middleware to automatically extract users IDs from
various authentication methods and integrate with existing ADK endopoints.
"""

import jwt
import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


def decode_google_iam_token(token: str) -> dict:
    """
    Decode and validate a Google Cloud IAM JWT token.
    
    This funciton decodes the token without verification (suitable for internal use)
    and extracts user identity information.

    Args:
        token (str): JWT token from Authentication header

    Returns:
        Dictionary containing token claims
    """
    try:
        # Decode the token without signature verificaiton
        # In production, you might want to verify with Google's public keys
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except jwt.DecodeError as e:
        logger.error(f"Failed to decode IAM token: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error decoding IAM token: {e}")
        return {}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically extract user ID from authentication headers."""
    
    def __init__(self, app, skip_paths: list[str] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/list-apps",
            "/debug/",
            "/favicon.ico",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/auth/user-info"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # For root and dev-ui paths, extract user ID but don't require full auth
        # These paths serve static assets and the web UI
        if request.url.path in ["/", "/dev-ui", "/dev-ui/"] or request.url.path.startswith("/dev-ui/"):
            # Extract user ID from authentication headers if available
            user_id = self._extract_user_id_from_headers(request)
            request.state.user_id = user_id
            return await call_next(request)
        
        # Skip authentication for certain endpoints
        if any(request.url.path == path or request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Extract user ID from authentication headers
        user_id = self._extract_user_id_from_headers(request)
        
        # Store user_id in request state for downstream use
        request.state.user_id = user_id

        # Log the authenticated user ID for debugging
        logger.info(f"Authentication middleware set user_id: {user_id} for path: {request.url.path}")
        logger.info(f"Request state user_id: {getattr(request.state, 'user_id', 'NOT_SET')}")

        # Note: ADK's get_fast_api_app() doesn't automatically read request.state.user_id
        # The user_id needs to be passed to ADK through its native session creation mechanism

        response = await call_next(request)
        return response

    def _extract_user_id_from_headers(self, request: Request) -> str:
        """Extract user ID from various authentication methods."""

        # Log all headers for debugging
        logger.info(f"=== Authentication Debug for path: {request.url.path} ===")
        for header_name, header_value in request.headers.items():
            # Mask authorization headers for security
            if header_name.lower() in ['authorization', 'x-goog-identity-token']:
                masked_value = header_value[:20] + "..." if len(header_value) > 20 else header_value
                logger.info(f"Header: {header_name} = {masked_value}")
            else:
                logger.info(f"Header: {header_name} = {header_value}")
        logger.info("=== End Headers ===")

        # Priority 1: IAM authentication (production)
        authorization = request.headers.get("authorization", "")
        logger.info(f"Authorization header found: {bool(authorization)}")
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            logger.info(f"Token length: {len(token)}")
            claims = decode_google_iam_token(token)
            logger.info(f"Decoded claims: {claims}")

            if claims:
                user_id = (
                    claims.get("sub") or
                    claims.get("email", "").split("@")[0] or
                    claims.get("name") or
                    claims.get("user_id")
                )

                if user_id:
                    logger.info(f"Authenticated user from IAM: {user_id}")
                    if "email" in claims:
                        logger.info(f"User email: {claims['email']}")
                    return user_id

        # Priority 2: IAP authentication (fallback)
        x_goog_authenticated_user_email = request.headers.get("x-goog-authenticated-user-email", "")
        if x_goog_authenticated_user_email:
            user_id = x_goog_authenticated_user_email.split("@")[0]
            logger.info(f"Authenticated user from IAP: {user_id} ({x_goog_authenticated_user_email})")
            return user_id

        # Priority 3: Custom header (testing/devlopment)
        x_user_id = request.headers.get("x-user-id", "")
        if x_user_id:
            logger.info(f"Using ID from X-User-ID header: {x_user_id}")
            return x_user_id

        # Priority 4: Development fallback
        logger.warning("No authentication headers found, using 'developer'")
        return "developer"
