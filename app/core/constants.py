"""Values the SRS fixes. Admin-editable values live in app_setting instead (settings_store.py)."""

PASSWORD_MIN_LENGTH = 12  # FR-1.7
LOCKOUT_ATTEMPTS = 5  # FR-1.7
LOCKOUT_MINUTES = 15  # FR-1.7
IDLE_TIMEOUT_MINUTES = 30  # FR-1.7
MEMBER_MAX_SESSIONS = 5  # FR-2.3
RESUMABLE_CHUNK_MB = 50  # FR-3.12
AUDIT_ONLINE_DAYS = 180  # FR-12.1
EXPERT_DELETION_WORKING_DAYS = 2  # FR-8.3

# D-01: images must never exceed 20 MB, whatever Admin sets.
IMAGE_LIMIT_MAX_MB = 20

# D-14: the free-space reserve is never smaller than this, however small the percentage.
STORAGE_RESERVE_MIN_GB = 5
# D-14: Admins are warned when the data disk passes these shares of its size.
STORAGE_WARNING_PERCENT = 75
STORAGE_CRITICAL_PERCENT = 85

# FR-2.1: exactly four login types. Visitors are anonymous and have no login.
LOGIN_TYPES = ("member", "admin", "reviewer", "approver")
