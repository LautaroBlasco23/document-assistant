"""Plan limit enforcement helpers."""

from fastapi import HTTPException

from core.model.user import UserLimits


class PlanLimitExceeded(HTTPException):
    def __init__(self, resource: str, current: int, max_limit: int, message: str):
        super().__init__(
            status_code=402,
            detail={
                "error": "Plan limit exceeded",
                "resource": resource,
                "current": current,
                "max": max_limit,
                "message": message,
            }
        )


def check_can_create_tree(limits: UserLimits) -> None:
    if not limits.can_create_tree:
        raise PlanLimitExceeded(
            resource="knowledge_tree",
            current=limits.current_knowledge_trees,
            max_limit=limits.max_knowledge_trees,
            message=f"You've reached the limit of {limits.max_knowledge_trees} knowledge trees.",
        )


def check_can_create_document(limits: UserLimits) -> None:
    if not limits.can_create_document:
        raise PlanLimitExceeded(
            resource="document",
            current=limits.current_documents,
            max_limit=limits.max_documents,
            message=f"You've reached the limit of {limits.max_documents} documents.",
        )
