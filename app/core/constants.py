"""Values the SRS fixes. Admin-editable values live in app_setting instead (settings_store.py)."""

PASSWORD_MIN_LENGTH = 12  # FR-1.7
LOCKOUT_ATTEMPTS = 5  # FR-1.7
LOCKOUT_MINUTES = 15  # FR-1.7
IDLE_TIMEOUT_MINUTES = 30  # FR-1.7
MEMBER_MAX_SESSIONS = 5  # FR-2.3
RESUMABLE_CHUNK_MB = 50  # FR-3.12
AUDIT_ONLINE_DAYS = 180  # FR-12.1
EXPERT_DELETION_WORKING_DAYS = 2  # FR-8.3

# P1-ACC-02: after proving their email, a visitor has this long to finish registering, and may
# ask whether a User ID is free this many times.
REGISTRATION_VERIFIED_MINUTES = 30
USER_ID_CHECKS = 30
# P1-ACC-02: limits on the reserved User ID lists an Admin edits.
RESERVED_WORD_MIN = 2
RESERVED_WORD_MAX = 30
# A shorter word refused "anywhere" would refuse most honest IDs.
RESERVED_ANYWHERE_MIN = 4
RESERVED_WORDS_LIMIT = 1000

# D-01: images must never exceed 20 MB, whatever Admin sets.
IMAGE_LIMIT_MAX_MB = 20

# D-14: the free-space reserve is never smaller than this, however small the percentage.
STORAGE_RESERVE_MIN_GB = 5
# D-14: Admins are warned when the data disk passes these shares of its size.
STORAGE_WARNING_PERCENT = 75
STORAGE_CRITICAL_PERCENT = 85

# FR-2.1: exactly four login types. Visitors are anonymous and have no login.
LOGIN_TYPES = ("member", "admin", "reviewer", "approver")

# FR-1.6, D-11: mail services anyone can join. A Discom listed with one of these would let any
# stranger with an address there ask for its login.
PUBLIC_EMAIL_DOMAINS = frozenset(
    {
        "aol.com",
        "gmail.com",
        "gmx.com",
        "googlemail.com",
        "hotmail.co.uk",
        "hotmail.com",
        "icloud.com",
        "live.com",
        "live.in",
        "mail.com",
        "me.com",
        "msn.com",
        "outlook.com",
        "outlook.in",
        "proton.me",
        "protonmail.com",
        "rediffmail.com",
        "rocketmail.com",
        "yahoo.co.in",
        "yahoo.co.uk",
        "yahoo.com",
        "yahoo.in",
        "yandex.com",
        "ymail.com",
        "zoho.com",
        "zohomail.in",
    }
)

# Security.md: set-password and reset links are single-use and expire after 60 minutes.
LINK_TOKEN_MINUTES = 60

# P1-ACC-10 (FR-2.8): emailed sign-in codes are 6 digits, last 10 minutes and allow 5 tries.
EMAIL_CODE_DIGITS = 6
EMAIL_CODE_MINUTES = 10
EMAIL_CODE_MAX_TRIES = 5
# P1-ACC-10: a new emailed code at most once a minute, so the form cannot be used to flood an inbox.
EMAIL_CODE_RESEND_SECONDS = 60
