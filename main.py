import os
import logging

from pathlib import Path

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Get the directory where main.py is located
AGENTS_DIR = Path(__file__).parent
# Session service uri (use GOOGLE_CLOUD_LOCATION_DEPLOY for GCP resource location)
if os.getenv("AGENT_ENGINE_ID") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true":
    deploy_location = os.getenv("GOOGLE_CLOUD_LOCATION_DEPLOY") or os.getenv("GOOGLE_CLOUD_LOCATION", "")
    SESSION_SERVICE_URI = (
        f"agentengine://projects/{os.getenv('GOOGLE_CLOUD_PROJECT', '')}"
        f"/locations/{deploy_location}"
        f"/reasoningEngines/{os.getenv('AGENT_ENGINE_ID', '')}"
    )
    logging.info(f"Using Vertex AI Agent Engine for sessions: {os.getenv('AGENT_ENGINE_ID')}")
    logging.info(f"Agent Engine location: {deploy_location}")
else:
    SESSION_SERVICE_URI = "sqlite:///./sessions.db"
    if os.getenv("AGENT_ENGINE_ID") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() != "true":
        logging.warning("AGENT_ENGINE_ID is set but GOOGLE_GENAI_USE_VERTEXAI=false")
        logging.warning("Using SQLite sessions (ephemeral on Cloud Run).")
        logging.warning("Set GOOGLE_GENAI_USE_VERTEXAI=true to use Vertex AI Agent Engine for persistent sessions.")
# Persistent artifacts GS bucket
ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET")
# Allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=str(AGENTS_DIR),
    session_service_uri=SESSION_SERVICE_URI,
    artifact_service_uri=f"gs://{ARTIFACT_BUCKET}" if ARTIFACT_BUCKET else None,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))