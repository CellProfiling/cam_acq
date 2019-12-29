"""Provide exceptions."""


class CamAcqError(Exception):
    """Represent the base camacq exception."""


class MissingActionTypeError(CamAcqError):
    """Represent a missing action type error."""

    def __init__(self, action_type):
        """Set up the error."""
        super().__init__(f"No such action type registered: {action_type}")


class MissingActionError(CamAcqError):
    """Represent a missing action error."""

    def __init__(self, action_id):
        """Set up the error."""
        super().__init__(f"No such action id registered: {action_id}")


class SampleError(CamAcqError):
    """Represent a sample error."""


class TemplateError(CamAcqError):
    """Represent a template error."""

    def __init__(self, exc):
        """Set up the error."""
        super().__init__(f"{exc.__class__.__name__}: {exc}")
