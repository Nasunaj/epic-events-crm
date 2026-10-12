"""Business exceptions (single place for the CLI to import)."""


# EpicEventsError comme classe de base : le CLI pourra faire except
# EpicEventsError pour attraper toutes les erreurs prévues d'un coup
# (et afficher str(exc) proprement) sans jamais attraper les erreurs imprévues
# (bugs, pannes BDD) qui doivent remonter vers Sentry. On généralise notre
# règle "attendu vs imprévu".
class EpicEventsError(Exception):
    """Base class: allows the CLI to catch any expected error."""


class ValidationError(EpicEventsError):
    """Input data is invalid before any write happens."""


class PermissionDeniedError(EpicEventsError):
    """The employee's role does not allow this action."""


# NotOwnedError hérite de PermissionDeniedError : c'est une sorte de refus de
# permission. L'héritage d'exceptions permet un except PermissionDeniedError
# qui attrape les deux. Design élégant, retiens-le ;
class NotOwnedError(PermissionDeniedError):
    """Role is allowed, but the target object is out of the employee's
    scope (e.g. another commercial's client)."""


class NotFoundError(EpicEventsError):
    """The requested object does not exist."""


class DuplicateError(EpicEventsError):
    """Raised when a email or employee number already exists"""
