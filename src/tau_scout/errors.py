class ScoutError(Exception):
    """A deliberately public, credential-free application error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ProviderError(ScoutError):
    def __init__(self, code: str, message: str, *, uncertain: bool = False):
        super().__init__(code, message)
        self.uncertain = uncertain
