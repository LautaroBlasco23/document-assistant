from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str
    display_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class SubscriptionPlan:
    id: UUID
    slug: str
    name: str
    description: str | None
    max_documents: int
    max_knowledge_trees: int
    is_active: bool
    created_at: datetime


@dataclass
class UserSubscription:
    id: UUID
    user_id: UUID
    plan_id: UUID
    assigned_at: datetime


@dataclass
class UserLimits:
    max_documents: int
    max_knowledge_trees: int
    current_documents: int
    current_knowledge_trees: int
    can_create_document: bool
    can_create_tree: bool
