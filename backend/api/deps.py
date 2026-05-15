"""FastAPI dependency injection helpers."""

from typing import Annotated

from fastapi import Depends, Request

from api.services import Services


async def get_services_dep(request: Request) -> Services:
    """FastAPI dependency to inject services from app state."""
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services_dep)]
