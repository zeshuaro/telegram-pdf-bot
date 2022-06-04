class CLIServiceError(Exception):
    pass


class CLINonZeroExitStatusError(CLIServiceError):
    pass
