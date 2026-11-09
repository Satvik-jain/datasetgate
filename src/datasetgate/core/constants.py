"""Global constants and exit codes for DatasetGate."""


class ExitCode:
    """CLI exit codes."""

    SUCCESS = 0  # Quality gate passed
    GATE_FAILED = 1  # Quality gate failed due to policy violations
    INVALID_USAGE = 2  # Bad CLI arguments or invalid configuration
    RUNTIME_ERROR = 3  # Unexpected execution / environment error
