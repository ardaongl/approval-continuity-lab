"""Shared bounds and classified failures, independent of IO."""
MAX_INT = 9_007_199_254_740_991
DAY = 86_400_000
MAX_REPORT = 1_048_576
STATES = ("pending", "approved", "rejected", "consumed", "revoked", "expired", "superseded")
EXITS = {"OK": 0}
for _code, _names in {
    2: "INPUT_INVALID INPUT_LIMIT UNSUPPORTED_VERSION LIMIT_EXCEEDED",
    3: "ROLE_FORBIDDEN CALLER_MISMATCH NOT_FOUND INVALID_STATE BINDING_MISMATCH IDEMPOTENCY_CONFLICT APPROVAL_PENDING APPROVAL_CONSUMED APPROVAL_REVOKED REVIEW_REJECTED PENDING_EXPIRED GRANT_EXPIRED CONTEXT_CHANGED TOOL_CHANGED POLICY_CHANGED REVIEWER_CHANGED TARGET_REVISION_CHANGED REPLACED CLOCK_REGRESSION REVISION_CONFLICT TOO_LATE POLICY_DISABLED REVIEWER_INELIGIBLE TARGET_SCOPE_MISMATCH",
    4: "SCENARIO_FAILED", 65: "DATABASE_VERSION STATE_CORRUPT", 66: "INPUT_IO",
    69: "STATE_EXISTS STORAGE_ERROR", 70: "INTERNAL_ERROR", 74: "OUTPUT_IO",
    75: "STORAGE_BUSY", 130: "INTERRUPTED",
}.items():
    EXITS.update(dict.fromkeys(_names.split(), _code))


class Failure(Exception):
    def __init__(self, code, details=None):
        self.code = code
        self.details = details or []
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise Failure(code)


def add(a, b):
    require(a <= MAX_INT - b, "LIMIT_EXCEEDED")
    return a + b
