import os
import logging

from more_executors.futures import f_flat_map, f_map

from .base import Repository, repo_type
from ..attr import pulp_attrib
from ..common import DetachedException
from ... import compat_attr as attr


LOG = logging.getLogger("pubtools.pulplib")


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
    )

    mutable_urls = attr.ib(default=attr.Factory(lambda: ["PULP_MANIFEST"]), type=list)

    def upload_file(self, file_obj, relative_url=None):
        """Upload a file to this repository.

        Args:
            file_obj (str, file object)
                If it's a string, then it's the path of file to upload.
                Else, it ought to be a file-like object

            relative_url (str)
                Path that should be used in remote repository

                If omitted, filename will be used.
        Returns:
            Future[:class:`~pubtools.pulplib.Task`]
                A future which is resolved when import succeeds.

                The future contains the task to import uploaded content
                to repository

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """
        if not self._client:
            raise DetachedException()

        relative_url = self._get_relative_url(file_obj, relative_url)

        # request upload id and wait for it
        upload_id = self._client._request_upload().result()["upload_id"]

        upload_complete_f, checksum, size = self._client._do_upload_file(
            upload_id, self.id, file_obj
        )

        unit_key = {"name": relative_url, "digest": checksum, "size": size}

        import_complete_f = f_flat_map(
            upload_complete_f,
            lambda _: self._client._do_import(self.id, upload_id, "iso", unit_key),
        )

        f_map(
            import_complete_f, lambda _: self._client._delete_upload_request(upload_id)
        )

        return import_complete_f

    def _get_relative_url(self, file_obj, relative_url):
        is_path = isinstance(file_obj, str)
        if is_path:
            if not relative_url:
                relative_url = file_obj
            elif relative_url.endswith("/"):
                _, name = os.path.split(file_obj)
                relative_url = os.path.join(relative_url, name)
        elif not is_path and (not relative_url or relative_url.endswith("/")):
            msg = "Must provide complete relative_url if the file's not from disk"
            LOG.exception(msg)
            raise ValueError(msg)

        return relative_url
