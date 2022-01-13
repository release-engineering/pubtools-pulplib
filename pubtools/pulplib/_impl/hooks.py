import sys

from pubtools.pluggy import hookspec, pm


# pylint: disable=unused-argument


@hookspec
def pulp_repository_pre_publish(repository, options):
    """Invoked as the first step in publishing a Pulp repository.

    If a hookimpl returns a non-None value, that value will be used to replace
    the options for this publish. This can be used to adjust publish options
    from within a hook.

    Args:
        repository (:class:`~pubtools.pulplib.Repository`):
            The repository to be published.

        options (:class:`~pubtools.pulplib.PublishOptions`):
            The options to use in publishing.

    Returns:
        options (:class:`~pubtools.pulplib.PublishOptions`):
            The potentially adjusted options used for this publish.
    """


@hookspec
def pulp_repository_published(repository, options):
    """Invoked after a Pulp repository has been successfully published.

    Args:
        repository (:class:`~pubtools.pulplib.Repository`):
            The repository which has been published.

        options (:class:`~pubtools.pulplib.PublishOptions`):
            The options used for this publish.
    """


pm.add_hookspecs(sys.modules[__name__])
