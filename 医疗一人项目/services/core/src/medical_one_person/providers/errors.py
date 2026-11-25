from __future__ import annotations


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderAuthenticationError(RuntimeError):
    pass


class ProviderRateLimited(RuntimeError):
    pass


class ProviderBudgetExceeded(RuntimeError):
    pass


class ProviderResponseInvalid(RuntimeError):
    pass
