"""
FastAPI application for the Medical Prior Authorization Environment.

Exposes the MedicalPAEnvironment over HTTP and WebSocket endpoints,
compatible with the OpenEnv EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    uvicorn medical_pa_env.server.app:app --host 0.0.0.0 --port 8000
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv-core is required. Install with: pip install openenv-core"
    ) from e

try:
    from ..models import MedicalPAAction, MedicalPAObservation
    from .medical_pa_environment import MedicalPAEnvironment
except (ImportError, ModuleNotFoundError):
    from models import MedicalPAAction, MedicalPAObservation
    from server.medical_pa_environment import MedicalPAEnvironment


# Create the FastAPI app via OpenEnv's create_app factory
app = create_app(
    MedicalPAEnvironment,
    MedicalPAAction,
    MedicalPAObservation,
    env_name="medical_pa_env",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    """Entry point for direct execution.

    Usage:
        python -m medical_pa_env.server.app
        uv run --project . server
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
