class ProcuraError(Exception):
    """Base error safe to map at an interface boundary."""


class OpportunityNotFoundError(ProcuraError):
    pass


class ConfigurationError(ProcuraError):
    pass


class UpstreamServiceError(ProcuraError):
    pass


class WatchlistNotFoundError(ProcuraError):
    pass


class DuplicateWatchlistError(ProcuraError):
    pass


class RequestBudgetExceededError(ProcuraError):
    pass
