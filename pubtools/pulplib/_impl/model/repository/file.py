import os
import logging

from attr import validators
from frozenlist2 import frozenlist

from .base import Repository, SyncOptions, repo_type
from ..attr import pulp_attrib
from ... import compat_attr as attr


LOG = logging.getLogger("pubtools.pulplib")


@attr.s(kw_only=True, frozen=True)
class FileSyncOptions(SyncOptions):
    """Options controlling a file repository
    :meth:`~pubtools.pulplib.Repository.sync`.
    """

    remove_missing = pulp_attrib(default=False, type=bool)
    """If true, as the repository is synchronized, old files will be removed.
    """


@repo_type("iso-repo")
@attr.s(kw_only=True, frozen=True)
class FileRepository(Repository):
    """A :class:`~pubtools.pulplib.Repository` for generic file distribution."""

    # this class only overrides some defaults for attributes defined in super

    type = pulp_attrib(default="iso-repo", type=str, pulp_field="notes._repo-type")

    is_sigstore = attr.ib(
        default=attr.Factory(
            lambda self: self.id == "redhat-sigstore", takes_self=True
        ),
        type=bool,
        validator=validators.instance_of(bool),
    )

    mutable_urls = attr.ib(
        default=attr.Factory(lambda: frozenlist(["PULP_MANIFEST"])),
        type=list,
        converter=frozenlist,
    )

    def upload_file(self, file_obj, relative_url=None):
        """Upload a file to this repository.

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of a file to upload.

                Otherwise, it should be a
                `file-like object <https://docs.python.org/3/glossary.html#term-file-object>`_
                pointing at the bytes to upload. The client takes ownership
                of this file object; it should not be modified elsewhere,
                and will be closed when upload completes.

            relative_url (str)
                Path that should be used in remote repository, can either
                be a path to a directory or a path to a file, e.g:

                - if relative_url is 'foo/bar/' and file_obj has name 'f.txt',
                  the resulting remote path wll be 'foo/bar/f.txt'.

                - if relative_url is 'foo/bar/f.txt', no matter what the
                  name of file_obj is, the remote path is 'foo/bar/f.txt'.

                If omitted, the local name of the file will be used. Or,
                if file_obj is a file object without a `name` attribute,
                passing `relative_url` is mandatory.

        Returns:
            Future[list of :class:`~pubtools.pulplib.Task`]
                A future which is resolved after content has been imported
                to this repo.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 1.2.0
        """
        relative_url = self._get_relative_url(file_obj, relative_url)

        unit_key_fn = lambda upload: {
            "name": relative_url,
            "checksum": upload[0],
            "size": upload[1],
        }

        return self._upload_then_import(file_obj, relative_url, "iso", unit_key_fn)

    def _get_relative_url(self, file_obj, relative_url):
        is_file_object = "close" in dir(file_obj)
        if not is_file_object:
            name = os.path.basename(file_obj)
            if not relative_url:
                relative_url = name
            elif relative_url.endswith("/"):
                relative_url = os.path.join(relative_url, name)
        elif is_file_object and (not relative_url or relative_url.endswith("/")):
            msg = "%s is missing a name attribute and relative_url was not provided"
            raise ValueError(msg % file_obj)

        return relative_url
