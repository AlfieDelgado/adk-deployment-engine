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
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # For root and dev-ui paths, extract user ID but don't require full auth
        # These paths serve static assets and the web UI
        if request.url.path in ["/", "/dev-ui", "/dev-ui/"] or request.url.path.startswith("/dev-ui/"):
            # Extract user ID from authentication headers if available
            user_id = self._extract_user_id_from_headers(request)
            request.state.user_id = user_id
            return await call_next(request)
        
        # Skip authenticaiton for certain endpoints
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Extract user ID from authentication headers
        user_id = self._extract_user_id_from_headers(request)
        
        # Store user_id in request state for downstream use
        request.state.user_id = user_id
        
        # If this is an endpoint with user_id in the path, we need to reqrite the URL
        if "/users/" in request.url.path:
            # Replace the user_id in the path with the authenticated user_id
            path_parts = request.url.path.split("/")
            # Find the index of "users" and replace the next element
            if "users" in path_parts:
                users_index = path_parts.index("users")
                if users_index + 1 <len(path_parts):
                    # Replace the path user_id with authenticated user_id
                    original_user_id = path_parts[users_index + 1]
                    path_parts[users_index + 1] = user_id

                    # Create new URL with the correct user_id
                    new_path = "/".join(path_parts)
                    if request.url.query:
                        new_path += f"?{request.url.query}"

                    # Log the user ID substitution for debugging
                    if original_user_id != user_id:
                        logger.info(
                            f"Replaced path user_id '{original_user_id}' with authenticated user_id '{user_id}'"
                        )

                    # Create a new request with the modified path
                    scope = dict(request.scope)
                    scope["path"] = "/".join(path_parts)
                    if request.url.query:
                        scope["query_string"] = request.url.query.encode()

                    request = Request(scope)

        response = await call_next(request)
        return response

    def _extract_user_id_from_headers(self, request: Request) -> str:
        """Extract user ID from various authentication methods."""
        
        # Priority 1: IAM authentication (production)
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            claims = decode_google_iam_token(token)

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
        logger.warning("No authentication headers found, using development_user")
        return "development_user"
