""".. moduleauthor:: Kai <z@kwi.li>"""


class APIException(Exception):
    """The API server returned an error."""

    def __init__(self, code: int, msg: str) -> None:
        super().__init__(msg)
        self.code = code


class KeepException(Exception):
    """Generic Keep error."""


class LoginException(KeepException):
    """Login exception."""


class BrowserLoginRequiredException(LoginException):
    """Browser login required error."""

    def __init__(self, url) -> None:
        self.url = url


class LabelException(KeepException):
    """Keep label error."""


class SyncException(KeepException):
    """Keep consistency error."""


class ResyncRequiredException(SyncException):
    """Full resync required error."""


class UpgradeRecommendedException(SyncException):
    """Upgrade recommended error."""


class MergeException(KeepException):
    """Node consistency error."""


class InvalidException(KeepException):
    """Constraint error."""


class ParseException(KeepException):
    """Parse error."""

    def __init__(self, msg: str, raw: dict) -> None:
        super().__init__(msg)
        self.raw = raw
