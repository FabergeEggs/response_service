"""Canonical Kafka topic names for cross-service integration."""

from typing import List

# Inbound — from auth_service (user registration)
# auth_service publishes to "user.created" with payload: {data: {user_id, email, first_name, last_name}}
USER_REGISTERED = "user.created"

# Inbound — from profile_service (profile / avatar updates)
# profile_service publishes to "user-events" with event_type:
#   "user.profile.updated" → {user_id, name}
#   "user.avatar.updated"  → {user_id, avatar_link}  (ignored by response_service)
#   "user.email.updated"   → {user_id, email}         (ignored by response_service)
PROFILE_CHANGED = "user-events"

# Inbound — from project_service
TASK_CREATED = "task.created"
TASK_CHANGED = "task.updated"
TASK_DELETE = "task.deleted"
POST_CREATED = "post.created"
POST_CHANGED = "post.updated"
POST_DELETE = "post.deleted"

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
