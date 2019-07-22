import os

from .base import Repository, repo_type
from ..attr import pulp_attrib
from ..common import DetachedException
from ... import compat_attr as attr


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

    def upload_file(self, filename, relative_url=None):
        """Upload a file to this repository.

        The upload operation includes 4 steps:
            1. Request an upload id from pulp
            2. With the requested upload id, upload the file
            3. After the upload's done, import the uploaded file to repository
            4. Delete the upload request

        Args:
            filename (str)
                Path to a local file to upload.

            relative_url (str)
                Path that should be used in remote repository

                if omitted, filename will be used.
        Returns:
            Future[:class:`~pubtools.pulplib.Task`]
                A future which is resolved when publish succeeds.

                The future contains the task to delete upload request

        Raises:
            DetachedException
                If this instance is not attached to a Pulp client.
        """
        if not self._client:
            raise DetachedException()

        path, name = os.path.split(filename.rstrip("/"))
        if not relative_url:
            relative_url = path

        # request upload id and wait for it
        upload_id = self._client._request_upload().result()["upload_id"]

        # caculate hash/size of the file and upload it to pulp
        upload_fs, checksum, size = self._client._do_upload_file(
            upload_id, self.id, filename
        )

        # we need to wait for upload then it can start importing
        upload_fs.result()

        unit_key = {"name": name, "digest": checksum, "size": size}
        self._client._do_import(self.id, upload_id, "iso", unit_key).result()

        return self._client._delete_upload_request(upload_id)
