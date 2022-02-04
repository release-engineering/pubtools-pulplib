"""Helpers for generating UD-related repo notes."""
import functools
import os
import logging
import json

from more_executors.futures import f_map, f_flat_map, f_return, f_zip

from ..model import FileUnit
from ..criteria import Criteria

LOG = logging.getLogger("pubtools.pulplib")

UD_MAPPINGS_NOTE = os.getenv("PULP_UD_MAPPINGS_NOTE") or "ud_file_release_mappings_2"


class MappingsHelper(object):
    """A wrapper for the raw release mappings dict.

    This wrapper provides a utility function for adding items to the dict
    while keeping track of whether any changes have been made.
    """

    def __init__(self, data):
        self._data = data
        self.changed = False

    def set_file_mapping(self, version, filename, order):
        """Ensure a mapping exists in the dict for a given
        version, filename & order.

        order can be None if no specific order is required.

        Sets self.changed to True if any changes occur.
        """

        # Example of the structure we're updating:
        #
        # {
        #   "4.8.10": [
        #     {
        #     "filename": "oc-4.8.10-linux.tar.gz",
        #     "order": 1.0
        #     },
        #     {
        #     "filename": "oc-4.8.10-macosx.zip",
        #     "order": 3.0
        #     },
        #     ...,
        #   ],
        #   "4.8.11": [ ... ],
        #   ...,
        # }
        if self._data.get(version) is None:
            self._data[version] = []
            self.changed = True

        file_list = self._data[version]

        file_dict = None
        for elem in file_list:
            if elem.get("filename") == filename:
                file_dict = elem
                break
        else:
            file_dict = {"filename": filename}
            file_list.append(file_dict)
            self.changed = True

        if order is None:
            # When asked to set an order of None we'll interpret it as
            # a request to make no changes at all (rather than actually
            # setting the order to none). This keeps the possibility open
            # of ignoring pulplib logic and manually setting the order
            # values to something else by standalone tools, without pulplib
            # resetting the values every time a publish happens.
            #
            # It's intentional to make changes up to this point rather than
            # returning early if order is None, because we need to ensure
            # that filenames are put under the right 'version' even if there
            # is no 'order'.
            return

        if order == file_dict.get("order"):
            # Nothing to be changed
            return

        file_dict["order"] = order
        self.changed = True

    @property
    def as_json(self):
        """The mapping converted to JSON form, suitable for storing on Pulp."""
        return json.dumps(self._data, sort_keys=True)


def compile_ud_mappings(repo, do_request):
    """Perform the UD mappings note compilation & update process for a given repo.

    Arguments:
        repo (~pulplib.FileRepository)
            A repository.
        do_request (callable)
            A function which can be invoked to perform an HTTP request to Pulp.

    Returns:
        A Future, resolved when the update completes successfully.
    """
    LOG.debug("%s: compiling %s", repo.id, UD_MAPPINGS_NOTE)

    # 1. Get current mappings.
    #
    # Requires a fresh retrieval of the repo since we don't store
    # these mappings on our model.
    #
    repo_url = "pulp/api/v2/repositories/%s/" % repo.id

    repo_raw_f = do_request(repo_url, method="GET")
    mappings_f = f_map(
        repo_raw_f, lambda data: (data.get("notes") or {}).get(UD_MAPPINGS_NOTE) or "{}"
    )

    # Mappings are stored as JSON, so decode them
    mappings_f = f_map(mappings_f, json.loads)

    # Wrap them in our helper for keeping track of changes
    mappings_f = f_map(mappings_f, MappingsHelper)

    # 2. Iterate over all files in the repo
    files_f = repo.search_content(Criteria.with_unit_type(FileUnit))

    # 3. Mutate the mappings as needed for each file
    updated_mappings_f = f_flat_map(
        f_zip(mappings_f, files_f),
        lambda tup: update_mappings_for_files(tup[0], tup[1]),
    )

    # 4. Upload them back if any changes
    handle_changes = functools.partial(
        upload_changed_mappings, repo=repo, repo_url=repo_url, do_request=do_request
    )
    return f_flat_map(updated_mappings_f, handle_changes)


def upload_changed_mappings(mappings, repo, repo_url, do_request):
    """Upload mappings back to repo, if and only if they've been changed."""

    if not mappings.changed:
        LOG.debug("%s: no changes required to %s", repo.id, UD_MAPPINGS_NOTE)
        return f_return()

    body = {"delta": {"notes": {UD_MAPPINGS_NOTE: mappings.as_json}}}

    # Note: Pulp docs are a bit ambiguous with respect to whether a repo PUT
    # will generate a task or not. In fact it generates tasks only if a
    # distributor or importer is being updated. Hence the request here doesn't
    # return a specific value, only a Future which succeeds if request
    # succeeds.
    update_f = do_request(repo_url, method="PUT", json=body)

    return f_map(
        update_f, lambda _: LOG.info("Updated %s in %s", UD_MAPPINGS_NOTE, repo.id)
    )


def update_mappings_for_files(mappings, file_page):
    # Updates mappings for every file in a single page, plus all
    # following pages (async).
    #
    # Returns Future[mappings] once all pages are processed.

    for unit in file_page.data:
        version = unit.version
        if version:
            mappings.set_file_mapping(version, unit.path, unit.display_order)

    if not file_page.next:
        # No more files, just return the mappings
        return f_return(mappings)

    # There's more files, keep going to the next page.
    return f_flat_map(
        file_page.next, lambda page: update_mappings_for_files(mappings, page)
    )
