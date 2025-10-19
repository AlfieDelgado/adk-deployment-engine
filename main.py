import os
import logging
from datetime import datetime

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from google.adk.cli.fast_api import get_fast_api_app

# Import the authentication middleware
try:
    # Standalone import
    from shared.adk_shared.auth_middleware import AuthenticationMiddleware
    from shared.adk_shared.adk_integration import ADKUserContextMiddleware
except ImportError:
    # Submodule import
    from adk_shared.auth_middleware import AuthenticationMiddleware
    from adk_shared.adk_integration import ADKUserContextMiddleware

# Get the directory where main.py is located
AGENT_DIR = Path(__file__).parent
# Session service uri
if os.getenv("AGENT_ENGINE_ID"):
    SESSION_SERVICE_URI = (
        f"agentengine://projects/{os.getenv('GOOGLE_CLOUD_PROJECT', '')}"
        f"/locations/{os.getenv('GOOGLE_CLOUD_LOCATION', '')}"
        f"/reasoningEngines/{os.getenv('AGENT_ENGINE_ID', '')}"
    )
else:
    SESSION_SERVICE_URI = "sqlite:///./sessions.db"
# Persistent artifacts GS bucket
ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET")
# Allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

logger = logging.getLogger(__name__)

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=str(AGENT_DIR),
    session_service_uri=SESSION_SERVICE_URI,
    artifact_service_uri=f"gs://{ARTIFACT_BUCKET}" if ARTIFACT_BUCKET else None,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# Add authentication middleware to handle user ID extraction automatically
app.add_middleware(AuthenticationMiddleware)

# Add ADK user context middleware to inject authenticated user IDs into ADK endpoints
app.add_middleware(ADKUserContextMiddleware)

# Add a simple endpoint for debugging authentication
@app.get("/auth/user-info")
async def get_user_info(request: Request):
    """
    Get information abbout the authenticated user.

    Useful for debugging authentication setup
    """
    # Import here to avoid circular imports
    try:
        from shared.adk_shared.auth_middleware import decode_google_iam_token
    except ImportError:
        from adk_shared.auth_middleware import decode_google_iam_token


    user_id = getattr(request.state, "user_id", "developer")

    # Get authentication headers for debugging
    authorization = request.headers.get("authorization", "")
    x_goog_authenticated_user_email = request.headers.get("x-goog-authenticated-user-email", "")
    x_user_id = request.headers.get("x-user-id", "")

    # Determine authentication source for debugging
    auth_source = "development"
    if authorization.startswith("Bearer "):
        auth_source = "iam"
        # Extract additional info from IAM token if available
        token = authorization[7:]
        claims = decode_google_iam_token(token)
        iam_info = {
            "subject": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "exp": datetime.fromtimestamp(claims.get("exp", 0)).isoformat() if claims.get("exp") else None,
            "iat": datetime.fromtimestamp(claims.get("iat", 0)).isoformat() if claims.get("iat") else None,
        }
    else:
        iam_info = {}
        if x_goog_authenticated_user_email:
            auth_source = "iap"
        elif x_user_id:
            auth_source = "custom"

    return {
        "user_id": user_id,
        "authentication_source": auth_source,
        "authenticated_user_email": x_goog_authenticated_user_email,
        "custom_user_id": x_user_id,
        "iam_claims": iam_info
    }


# Add endpoint to test ADK user context injection
@app.get("/auth/test-adk-context")
async def test_adk_context(request: Request):
    """
    Test endpoint to verify ADK user context injection is working.

    This endpoint simulates how ADK would receive the authenticated user ID.
    """
    user_id = getattr(request.state, "user_id", "developer")

    # Check if the ADK user context middleware has injected the user ID
    headers = dict(request.headers)
    adk_user_id_header = headers.get("x-adk-user-id")

    # Check if path was modified for ADK
    path_was_modified = "user" not in request.url.path and user_id != "developer"

    return {
        "request_state_user_id": user_id,
        "adk_user_id_header": adk_user_id_header,
        "path_was_modified": path_was_modified,
        "current_path": request.url.path,
        "authentication_successful": user_id != "developer"
    }


# Add endpoint to test manual IAM token injection
@app.get("/auth/test-manual-token")
async def test_manual_token(request: Request):
    """
    Test endpoint to verify manual IAM token injection works.

    Use this to test if our JWT decoding works with manual tokens.
    """
    # Import here to avoid circular imports
    try:
        from shared.adk_shared.auth_middleware import decode_google_iam_token
    except ImportError:
        from adk_shared.auth_middleware import decode_google_iam_token

    # Get authorization header
    authorization = request.headers.get("authorization", "")

    result = {
        "has_authorization_header": bool(authorization),
        "authorization_starts_with_bearer": authorization.startswith("Bearer "),
        "authorization_length": len(authorization) if authorization else 0
    }

    if authorization.startswith("Bearer "):
        token = authorization[7:]
        claims = decode_google_iam_token(token)

        result.update({
            "token_length": len(token),
            "claims": claims,
            "decoded_successfully": bool(claims),
            "user_id_from_claims": (
                claims.get("sub") or
                claims.get("email", "").split("@")[0] or
                claims.get("name") or
                claims.get("user_id")
            ) if claims else None
        })

    return result

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
