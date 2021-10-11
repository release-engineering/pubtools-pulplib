import logging
import datetime
import os

import jsonschema
from frozenlist2 import frozenlist


from pubtools.pulplib._impl import compat_attr as attr
from .attr import pulp_attrib
from .convert import read_timestamp, write_timestamp
from ..schema import load_schema
from .common import InvalidDataException


LOG = logging.getLogger("pubtools.pulplib")


USER = os.environ.get("USER")
HOSTNAME = os.environ.get("HOSTNAME")


@attr.s(kw_only=True, frozen=True)
class MaintenanceEntry(object):
    """Details about the maintenance status of a specific repository.

    .. versionadded:: 1.4.0
    """

    repo_id = pulp_attrib(type=str)
    """ID of repository in maintenance.

    Note: there is no guarantee that a repository of this ID currently exists
    in the Pulp server."""
    message = pulp_attrib(default=None, type=str)
    """Why this repository is in maintenance."""
    owner = pulp_attrib(default=None, type=str)
    """Who set this repository in maintenance mode."""
    started = pulp_attrib(default=None, type=datetime.datetime)
    """:class:`~datetime.datetime` in UTC at when the maintenance started."""


@attr.s(kw_only=True, frozen=True)
class MaintenanceReport(object):
    """Represents the maintenance status of Pulp repositories.

    On release-engineering Pulp servers, it's possible to put individual repositories
    into "maintenance mode".  When in maintenance mode, external publishes of a repository
    will be blocked.  Other operations remain possible.

    This object holds information on the set of repositories currently in maintenance mode.

    .. versionadded:: 1.4.0
    """

    _OWNER = "%s@%s" % (USER, HOSTNAME) if all([USER, HOSTNAME]) else "pubtools.pulplib"

    _SCHEMA = load_schema("maintenance")

    last_updated = pulp_attrib(default=None, type=datetime.datetime)
    """:class:`~datetime.datetime` in UTC when this report was last updated,
    if it's the first time the report is created, current time is used."""

    last_updated_by = pulp_attrib(default=None, type=str)
    """Person/party who updated the report last time."""

    entries = pulp_attrib(
        default=attr.Factory(frozenlist), type=list, converter=frozenlist
    )
    """A list of :class:`MaintenanceEntry` objects, indicating
    which repositories are in maintenance mode and details.
    If empty, then it means no repositories are in maintenance mode.
    """

    @entries.validator
    def _check_duplicates(self, _, value):
        # check if there's duplicate entries
        repo_ids = [entry.repo_id for entry in value]
        if len(repo_ids) != len(set(repo_ids)):
            raise ValueError("Duplicate entries")

    @classmethod
    def _from_data(cls, data):
        """Create a new report with raw data

        Args:
            data (dict):
                A dict containing a raw representation of the maintenance status.

        Returns:
            a new instance of ``cls``

        Raises:
            InvalidDataException
                If the provided ``data`` fails validation against an expected schema.
        """
        try:
            jsonschema.validate(instance=data, schema=cls._SCHEMA)
        except jsonschema.exceptions.ValidationError as error:
            LOG.exception("%s.from_data invoked with invalid data", cls.__name__)
            raise InvalidDataException(str(error))

        entries = []
        for repo_id, details in data["repos"].items():
            entries.append(
                MaintenanceEntry(
                    repo_id=repo_id,
                    message=details["message"],
                    owner=details["owner"],
                    started=read_timestamp(details["started"]),
                )
            )

        maintenance = cls(
            last_updated=read_timestamp(data["last_updated"]),
            last_updated_by=data["last_updated_by"],
            entries=entries,
        )

        return maintenance

    def _export_dict(self):
        """export a raw dictionary of maintenance report"""
        report = {
            "last_updated": write_timestamp(self.last_updated),
            "last_updated_by": self.last_updated_by or self._OWNER,
            "repos": {},
        }

        for entry in self.entries:
            report["repos"].update(
                {
                    entry.repo_id: {
                        "message": entry.message,
                        "owner": entry.owner,
                        "started": write_timestamp(entry.started),
                    }
                }
            )

        return report

    def add(self, repo_ids, **kwargs):
        """Add entries to maintenance report and update the timestamp. Every
        entry added to the report represents a repository in maintenance mode.

        Args:
            repo_ids (list[str]):
                A list of repository ids. New entries with these repository ids will
                be added to the maintenance report.

                Note: it's users' responsibility to make sure the repository exists in
                the Pulp server, this method doesn't check for the existence of repositories.

            message (str) (optional):
                Reason why put the repo to maintenance.

            owner (str) (optional):
                Who set the maintenance mode.

        Returns:
           :class:`~pubtools.pulplib.MaintenanceReport`
                A copy of this maintenance report with added repositories.

        """
        message = kwargs.get("message") or "Maintenance mode is enabled"
        owner = kwargs.get("owner") or self._OWNER

        to_add = []
        for repo in repo_ids:
            to_add.append(
                MaintenanceEntry(
                    repo_id=repo,
                    owner=owner,
                    message=message,
                    started=datetime.datetime.utcnow(),
                )
            )
        entries = list(self.entries)
        entries.extend(to_add)

        # filter out duplicated entries. Filtering is in reverse order, which
        # means existed entries will be replaced by newer ones with same repo_id
        filtered_entries = []
        entry_ids = set()
        for entry in reversed(entries):
            if entry.repo_id not in entry_ids:
                filtered_entries.append(entry)
                entry_ids.add(entry.repo_id)

        return attr.evolve(
            self,
            entries=filtered_entries,
            last_updated_by=owner,
            last_updated=datetime.datetime.utcnow(),
        )

    def remove(self, repo_ids, **kwargs):
        """Remove entries from the maintenance report. Remove entries means the
        removing corresponding repositories from maintenance mode.

        Args:
            repo_ids (list[str]):
                A list of repository ids. Entries match repository ids will be removed
                from the maintenance report.

            owner (str) (optional):
                Who unset the maintenance mode.

        Returns:
            :class:`~pubtools.pulplib.MaintenanceReport`
                A copy of this maintenance report with removed repositories.
        """
        owner = kwargs.get("owner") or self._OWNER

        repo_ids = set(repo_ids)
        # convert to set, make checking faster
        new_entries = []
        for entry in self.entries:
            if entry.repo_id not in repo_ids:
                new_entries.append(entry)

        return attr.evolve(self, last_updated_by=owner, entries=new_entries)
