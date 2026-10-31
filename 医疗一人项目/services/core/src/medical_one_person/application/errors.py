class ApplicationError(Exception):
    """Base class for expected application failures."""


class NotFoundError(ApplicationError):
    pass


class RevisionConflictError(ApplicationError):
    pass


class IdempotencyConflictError(ApplicationError):
    pass


class ArchivedProjectError(ApplicationError):
    pass


class BudgetExceededError(ApplicationError):
    pass


class ConflictingOperationError(ApplicationError):
    pass


class TaskDependencyError(ApplicationError):
    pass


class TaskNotReadyError(ApplicationError):
    pass


class PlanStateError(ApplicationError):
    pass


class ReviewPolicyError(ApplicationError):
    pass


class LeaseConflictError(ApplicationError):
    pass


class AgentConfigurationError(ApplicationError):
    pass


class AgentOutputValidationError(ApplicationError):
    pass


class AgentRunError(ApplicationError):
    pass
