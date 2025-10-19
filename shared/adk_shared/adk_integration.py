"""ADK Integration Helper for custom user ID handling.

This module provides utilities to integrate authentication middleware with ADK's
session management system by intercepting requests and injecting authenticated user IDs.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ADKUserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject authenticated user IDs into ADK's session context.

    This middleware intercepts requests to ADK endpoints and ensures that
    the authenticated user ID from our authentication middleware is used
    instead of ADK's default "user" value.
    """

    def __init__(self, app):
        super().__init__(app)
        # ADK endpoints that typically use user_id
        self.adk_user_endpoints = [
            "/users/",
            "/agents/",
            "/sessions/",
            "/run_sse",
            "/run_streaming"
        ]

    async def dispatch(self, request, call_next):
        """Process request and inject user context for ADK endpoints."""

        # Check if this is an ADK endpoint that needs user context
        if any(endpoint in request.url.path for endpoint in self.adk_user_endpoints):
            # Get the authenticated user ID from request state (set by our auth middleware)
            user_id = getattr(request.state, "user_id", None)

            if user_id and user_id != "developer":
                logger.info(f"Injecting authenticated user ID '{user_id}' for ADK endpoint: {request.url.path}")

                # Store the authenticated user ID in a custom header for ADK to use
                request.scope["headers"] = request.scope.get("headers", []) + [
                    (b"x-adk-user-id", user_id.encode())
                ]

                # Also store in query parameters for ADK endpoints that expect user_id
                if "user" in request.url.path:
                    logger.info(f"Found 'user' in path, will inject authenticated user ID")

                    # Modify the request to replace 'user' with the actual user ID
                    path_parts = request.url.path.split("/")
                    if "user" in path_parts:
                        user_index = path_parts.index("user")
                        if user_index + 1 < len(path_parts):
                            original_user = path_parts[user_index + 1]
                            path_parts[user_index + 1] = user_id

                            # Update the request path
                            new_path = "/".join(path_parts)
                            request.scope["path"] = new_path
                            request.scope["raw_path"] = new_path.encode()

                            logger.info(f"Replaced user ID in path: '{original_user}' -> '{user_id}'")

        response = await call_next(request)
        return response


def get_authenticated_user_id(request: Request) -> str:
    """
    Dependency function to get the authenticated user ID from request state.

    This can be used in custom endpoints to ensure consistent user ID handling.
    """
    user_id = getattr(request.state, "user_id", "developer")
    logger.info(f"Getting authenticated user ID for endpoint: {user_id}")
    return user_id


def inject_adk_user_context():
    """
    FastAPI dependency that ensures ADK endpoints receive the authenticated user ID.

    Usage:
        @app.post("/custom-agent-endpoint")
        async def custom_endpoint(user_id: str = Depends(inject_adk_user_context())):
            # Use the authenticated user ID
            pass
    """
    def dependency(request: Request) -> str:
        user_id = getattr(request.state, "user_id", "developer")

        if user_id == "developer":
            logger.warning("Using developer fallback - no authentication found")

        return user_id

    return dependency