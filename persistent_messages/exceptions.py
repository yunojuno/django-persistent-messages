class PersistentMessageException(Exception):
    pass


class UndismissableMessage(PersistentMessageException):
    pass
