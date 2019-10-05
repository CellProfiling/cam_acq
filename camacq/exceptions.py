"""Provide exceptions."""


class CamAcqError(Exception):
    """Represent the base camacq exception."""


class TemplateError(CamAcqError):
    """Represent a template error."""

    def __init__(self, exc):
        """Set up the error."""
        super().__init__(f"{exc.__class__.__name__}: {exc}")
