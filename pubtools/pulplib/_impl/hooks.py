import sys

from pubtools.pluggy import hookspec, pm


# pylint: disable=unused-argument


@hookspec
def pulp_repository_published(repository, options):
    """Invoked after a Pulp repository has been successfully published.

    :param repository: the repository which has been published.
    :type repository: pubtools.pulplib.Repository
    :param options: the options used for this publish.
    :type options: pubtools.pulplib.PublishOptions
    """


pm.add_hookspecs(sys.modules[__name__])
