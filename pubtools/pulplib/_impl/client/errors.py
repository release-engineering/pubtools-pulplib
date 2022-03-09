class PulpException(Exception):
    """Raised when the Pulp server has responded with an unrecoverable error
    (generally a failed HTTP response which persisted over several retries).
    """


class TaskFailedException(PulpException):
    """Raised when a Pulp task has completed with errors."""

    def __init__(self, task):
        self.task = task
        """The :class:`~pubtools.pulplib.Task` which has failed.
        Error details may be accessed from the task.
        """

        super(TaskFailedException, self).__init__(task.error_details)


class MissingTaskException(PulpException):
    # this is not public API, this exception should be extremely rare
    pass
