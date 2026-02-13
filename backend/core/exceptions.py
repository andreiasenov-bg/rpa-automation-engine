"""Custom exceptions for the RPA automation engine."""


class RPAException(Exception):
    """Base exception for RPA automation engine."""

    def __init__(self, message: str, status_code: int = 500):
        """Initialize exception with message and status code.

        Args:
            message: Exception message
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(RPAException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found"):
        """Initialize NotFoundError with 404 status code."""
        super().__init__(message, 404)


class UnauthorizedError(RPAException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Unauthorized"):
        """Initialize UnauthorizedError with 401 status code."""
        super().__init__(message, 401)


class ForbiddenError(RPAException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden"):
        """Initialize ForbiddenError with 403 status code."""
        super().__init__(message, 403)


class ValidationError(RPAException):
    """Validation error exception."""

    def __init__(self, message: str = "Validation failed"):
        """Initialize ValidationError with 422 status code."""
        super().__init__(message, 422)


class ConflictError(RPAException):
    """Resource conflict exception."""

    def __init__(self, message: str = "Resource conflict"):
        """Initialize ConflictError with 409 status code."""
        super().__init__(message, 409)
