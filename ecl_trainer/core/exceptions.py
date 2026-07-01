class PayloadExfiltrationException(ValueError):
    """Raised when outbound ledger metadata contains disallowed payload material."""


class SovereignDataExfiltrationException(PayloadExfiltrationException):
    """Raised when oracle metadata contains payload material or unsafe text."""


class LedgerVerificationException(ValueError):
    """Raised when an immutable event log cannot be verified."""


class ControlPlaneSubmissionException(RuntimeError):
    """Raised when a control-plane submission fails."""
