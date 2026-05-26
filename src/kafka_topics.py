"""Canonical Kafka topic names for cross-service integration."""

from typing import List

# Inbound — from profile_service / auth_service
PROFILE_CHANGED = "profile_service.profile.changed"
USER_REGISTERED = "profile_service.user.registered"

# Inbound — from project_service
TASK_CREATED = "project_service.task.created"
TASK_CHANGED = "project_service.task.changed"
TASK_DELETE = "project_service.task.delete"
POST_CREATED = "project_service.post.created"
POST_CHANGED = "project_service.post.changed"
POST_DELETE = "project_service.post.delete"

INCOMING_TOPICS: List[str] = [
    USER_REGISTERED,
    PROFILE_CHANGED,
    TASK_CREATED,
    TASK_CHANGED,
    TASK_DELETE,
    POST_CREATED,
    POST_CHANGED,
    POST_DELETE,
]

# Outbound — domain events (other consumers / audit)
RESPONSE_ADD = "response_service.response.add"
RESPONSE_DELETE = "response_service.response.delete"

# Outbound — consumed by project_service (answer counters)
ANSWERS = "project-answers"

# Outbound — consumed by project_service (post comments_count)
COMMENTS = "project-comments"
