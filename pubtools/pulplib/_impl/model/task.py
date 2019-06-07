from .common import PulpObject


class Task(PulpObject):
    """Represents a Pulp task."""

    @property
    def id(self):
        """ID of this task (str)."""

    @property
    def completed(self):
        """True if this task has completed, successfully or otherwise."""

    @property
    def succeeded(self):
        """True if this task has completed successfully."""
