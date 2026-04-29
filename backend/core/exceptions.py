class RateLimitError(Exception):
    """Raised when an LLM provider returns HTTP 429 after all retries are exhausted."""

    def __init__(self, provider: str, retry_after: float, message: str = ""):
        self.provider = provider
        self.retry_after = retry_after
        self.message = message or f"{provider} rate limit exceeded; retry after {retry_after:.0f}s"
        super().__init__(self.message)


class ProviderNotConfigured(Exception):
    """Raised when a user requests a provider they have not configured credentials for."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"Provider '{provider}' is not configured. Add an API key in Settings.")
