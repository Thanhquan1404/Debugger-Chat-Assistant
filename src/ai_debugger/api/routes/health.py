from fastapi import APIRouter

from ai_debugger import __version__
from ai_debugger.api.schemas import Envelope, HealthData

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=Envelope,
    summary="Health check",
    description="Returns 200 when the API is up and the container is ready.",
)
async def health() -> Envelope:
    return Envelope(
        data=HealthData(version=__version__).model_dump(),
        success=True,
    )
