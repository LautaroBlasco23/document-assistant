"""User management endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from api.auth import CurrentUser
from api.deps import ServicesDep

router = APIRouter(prefix="/users", tags=["users"])


class PlanSummary(BaseModel):
    slug: str
    name: str
    description: str | None


class UserLimitsResponse(BaseModel):
    max_documents: int
    max_knowledge_trees: int
    current_documents: int
    current_knowledge_trees: int
    can_create_document: bool
    can_create_tree: bool
    plan: PlanSummary | None


@router.get("/me/limits", response_model=UserLimitsResponse)
async def get_my_limits(
    current_user: CurrentUser,
    services: ServicesDep
) -> UserLimitsResponse:
    """Get current usage and plan limits."""
    limits = services.subscription_store.get_user_limits(current_user.id)
    plan = services.subscription_store.get_plan_for_user(current_user.id)
    return UserLimitsResponse(
        max_documents=limits.max_documents,
        max_knowledge_trees=limits.max_knowledge_trees,
        current_documents=limits.current_documents,
        current_knowledge_trees=limits.current_knowledge_trees,
        can_create_document=limits.can_create_document,
        can_create_tree=limits.can_create_tree,
        plan=(
            PlanSummary(slug=plan.slug, name=plan.name, description=plan.description)
            if plan is not None
            else None
        ),
    )
