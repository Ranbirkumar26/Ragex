class RagexError(Exception):
    """Base class for domain errors shown through a stable API envelope."""


class DataUnavailableError(RagexError):
    """Raised when configured repository cannot provide required data."""


class NotFoundError(RagexError):
    """Raised when a requested domain object does not exist."""


class ExplanationRefusedError(RagexError):
    """Raised when corpus evidence is insufficient for a grounded answer."""
