"""FastAPI dependency injection helpers."""

from typing import Annotated

from fastapi import Depends

from api.services import get_services, Services


async def get_services_dep() -> Services:
    """FastAPI dependency to inject services."""
    return get_services()


# Annotated type for easy use in routers
ServicesDep = Annotated[Services, Depends(get_services_dep)]
