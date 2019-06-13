from more_executors.retry import ExceptionRetryPolicy


def new_policy():
    # TODO: we'll need our own policy with improved logging and handling of
    # certain "no point in retrying" errors
    return ExceptionRetryPolicy()
