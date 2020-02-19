import os
import logging

from attr import validators
from more_executors.futures import f_flat_map, f_map, f_proxy

from .base import Repository, SyncOptions, repo_type
from ..frozenlist import FrozenList
from ..attr import pulp_attrib
from ..common import DetachedException
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
        default=attr.Factory(lambda: FrozenList(["PULP_MANIFEST"])),
        type=list,
        converter=FrozenList,
    )

    def upload_file(self, file_obj, relative_url=None):
        """Upload a file to this repository.

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of file to upload.
                Else, it ought to be a
                `file-like object <https://docs.python.org/3/glossary.html#term-file-object>`_.


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
                A future which is resolved when import succeeds.

                The future contains the task to import uploaded content
                to repository.

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.

        .. versionadded:: 1.2.0
        """
        if not self._client:
            raise DetachedException()

        relative_url = self._get_relative_url(file_obj, relative_url)
        name = os.path.basename(relative_url)

        # request upload id and wait for it
        upload_id = self._client._request_upload().result()["upload_id"]

        upload_complete_f = self._client._do_upload_file(upload_id, file_obj, name)

        import_complete_f = f_flat_map(
            upload_complete_f,
            lambda upload: self._client._do_import(
                self.id,
                upload_id,
                "iso",
                {"name": relative_url, "checksum": upload[0], "size": upload[1]},
            ),
        )

        f_map(
            import_complete_f, lambda _: self._client._delete_upload_request(upload_id)
        )

        return f_proxy(import_complete_f)

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
