class APIException(Exception):
    """The API server returned an error."""
    def __init__(self, code, msg):
        super(APIException, self).__init__(msg)
        self.code = code

class KeepException(Exception):
    """Generic Keep error."""
    pass

class LoginException(KeepException):
    """Login exception."""
    pass

class LabelException(KeepException):
    """Keep label error."""
    pass

class SyncException(KeepException):
    """Keep consistency error."""
    pass

class MergeException(KeepException):
    """Node consistency error."""
    pass
