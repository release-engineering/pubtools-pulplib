import logging

from monotonic import monotonic


class TimedLogger(object):
    """A helper to log messages only if a certain amount of time has passed
    since the previous log.

    Intended for loops where you want to log progress sometimes but you don't
    know how fast the loop will run, making it potentially too spammy to
    log at every iteration or even at some fixed interval of iterations.
    """

    def __init__(self, logger=None, interval=10):
        """Construct a new timed logger.

        Arguments:
            logger
                Underlying logger object to which messages will be routed.

            interval
                Minimum amount of time, in seconds, which must pass between
                messages. Each time a message is logged, if the amount of
                time passed since the previous log is less than this, the
                message will be discarded.
        """
        logger = logger or logging.getLogger("pubtools.pulplib")

        self._interval = interval

        # We start counting from the time we're constructed. That means we
        # won't produce any log message at all until we've been alive for at
        # least 'interval' seconds.
        self._last_log = monotonic()

        # The log methods we support. Feel free to add others like warn/error
        # if needed, but it's not clear there's a use-case.
        self.debug = self._wrap(logger.debug)
        self.info = self._wrap(logger.info)

    def _wrap(self, logmethod):
        def new_logmethod(*args, **kwargs):
            now = monotonic()
            if now - self._last_log < self._interval:
                # Too soon, don't log yet
                return
            # OK, we should log
            self._last_log = now
            return logmethod(*args, **kwargs)

        return new_logmethod
