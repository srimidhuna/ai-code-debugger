class DebuggerException(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class OpenRouterConfigError(DebuggerException):
    """API key is missing or misconfigured — returned as 503 so clients know the service is unconfigured."""
    def __init__(self, message: str = "OpenRouter API key is missing or misconfigured. "
                                     "Set OPENROUTER_API_KEY in your .env file."):
        super().__init__(message, status_code=503)

class OpenRouterAuthError(DebuggerException):
    """OpenRouter rejected the API key — returned as 502 (bad gateway) to distinguish from client 401s."""
    def __init__(self, message: str = "OpenRouter authentication failed. "
                                     "Verify your OPENROUTER_API_KEY is valid and active."):
        super().__init__(message, status_code=502)

class OpenRouterRateLimitError(DebuggerException):
    def __init__(self, message: str = "OpenRouter rate limit exceeded. Please try again later."):
        super().__init__(message, status_code=429)

class OpenRouterTimeoutError(DebuggerException):
    def __init__(self, message: str = "OpenRouter request timed out after 60 seconds."):
        super().__init__(message, status_code=504)

class OpenRouterModelUnavailableError(DebuggerException):
    def __init__(self, message: str = "Configured OpenRouter model is currently unavailable."):
        super().__init__(message, status_code=503)

class OpenRouterNetworkError(DebuggerException):
    def __init__(self, message: str = "Network error communicating with OpenRouter API."):
        super().__init__(message, status_code=502)

class AIValidationError(DebuggerException):
    def __init__(self, message: str = "Failed to parse or validate AI reasoning response."):
        super().__init__(message, status_code=502)

class SourceTooLargeError(DebuggerException):
    def __init__(self, message: str = "Submitted source code exceeds the 102,400 byte (100 KiB) limit."):
        super().__init__(message, status_code=413)

class SourceTooManyLinesError(DebuggerException):
    def __init__(self, message: str = "Submitted source code exceeds the 3,000 lines limit."):
        super().__init__(message, status_code=422)
