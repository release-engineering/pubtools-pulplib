import os
import logging
import traceback

from more_executors.retry import RetryPolicy, ExceptionRetryPolicy

from .errors import TaskFailedException

LOG = logging.getLogger("pubtools.pulplib")

ATTEMPTS = int(os.environ.get("PUBTOOLS_PULPLIB_RETRY_ATTEMPTS", "10"))
SLEEP = float(os.environ.get("PUBTOOLS_PULPLIB_RETRY_SLEEP", "1.0"))
MAX_SLEEP = float(os.environ.get("PUBTOOLS_PULPLIB_RETRY_MAX_SLEEP", "120.0"))


class PulpRetryPolicy(RetryPolicy):
    def __init__(self, max_attempts=ATTEMPTS, sleep=SLEEP, max_sleep=MAX_SLEEP):
        super(PulpRetryPolicy, self).__init__()
        self._max_attempts = max_attempts
        self._delegate = ExceptionRetryPolicy(
            max_attempts=max_attempts, sleep=sleep, max_sleep=max_sleep
        )

    def should_retry(self, attempt, future):
        # This is still using only the default ExceptionRetryPolicy behavior.
        # I expect at some point we will need to fine-tune this and look
        # at the error in more detail in order to decide whether to retry.
        retry = self._delegate.should_retry(attempt, future)

        exception = future.exception()
        if exception and getattr(exception, "response", None) is not None:
            # if returned status code is 404, never retry on that
            if exception.response.status_code == 404:
                return False

        if exception and retry:
            self._log_retry(attempt, future)

        return retry

    def sleep_time(self, attempt, future):
        return self._delegate.sleep_time(attempt, future)

    def _log_retry(self, attempt, future):
        # TODO: it would be nice if we could add some info here about
        # *what* is being retried. But it's a bit of a challenge since
        # future objects themselves don't come with any info on what was
        # done to create the future.
        exception = future.exception()
        LOG.warning(
            "Retrying due to error: %s [%d/%d]%s",
            exception,
            attempt,
            self._max_attempts,
            self._traceback(exception),
            extra={"event": {"type": "pulp-retry"}},
        )

    def _traceback(self, exception):
        out = ""

        if isinstance(exception, TaskFailedException):
            # No point logging traceback of this exception, the message
            # "task failed: <id>" is already all the useful info
            pass
        elif hasattr(exception, "__traceback__"):
            out = "\n" + "".join(
                traceback.format_exception(None, exception, exception.__traceback__)
            )

        return out
