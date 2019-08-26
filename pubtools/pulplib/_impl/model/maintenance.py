import logging
import datetime
import json
import os

import jsonschema

from pubtools.pulplib._impl import compat_attr as attr
from ..schema import load_schema
from .common import InvalidDataException


LOG = logging.getLogger("pubtools.pulplib")


USER = os.environ.get("USER")
HOSTNAME = os.environ.get("HOSTNAME")
OWNER = "%s@%s" % (USER, HOSTNAME)


def iso_time_now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


@attr.s(kw_only=True, frozen=True)
class MaintenanceEntry(object):
    """Details about the maintenance"""

    id = attr.ib(default=None, type=str)
    """ID of repository in maintenance"""
    message = attr.ib(default=None, type=str)
    """Why this repository is in maintenance"""
    owner = attr.ib(default=None, type=str)
    """Who set this repository in maintenance mode"""
    started = attr.ib(default=None, type=datetime.datetime)
    """:class:`~datetime.datetime` in UTC at when the maintenance started"""


@attr.s(kw_only=True, frozen=True)
class MaintenanceReport(object):
    """Represents the maintenance status of Pulp repositories

    On release-engineering Pulp servers, it's possible to put individual repositories
    into "maintenance mode".  When in maintenance mode, external publishes of a repository
    will be blocked.  Other operations remain possible.

    This object holds information on the set of repositories currently in maintenance mode.
    """

    _SCHEMA = load_schema("maintenance")

    last_updated = attr.ib(default=iso_time_now(), type=datetime.datetime)
    """:class:`~datetime.datetime` in UTC when this report was last updated,
    if it's the first time the report is created, current time is used."""

    last_updated_by = attr.ib(default=None, type=str)
    """Person/party who updated the report last time"""

    entries = attr.ib(default=attr.Factory(tuple), type=tuple)
    """A tuple contains :class:`MaintenanceEntry` objects, indicates
    which repositories are in maintenance mode and details.
    If empty, then it means no repositories is in maintenance mode.
    """

    @classmethod
    def from_data(cls, data):
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
            entries.append(MaintenanceEntry(id=repo_id, **details))

        maintenance = cls(
            last_updated=data["last_updated"],
            last_updated_by=data["last_updated_by"],
            entries=tuple(entries),
        )

        return maintenance

    def _json(self):
        """Output a json format report.

        Returns:
            A string contains the maintenance report in json format.
        """
        report = {
            "last_updated": self.last_updated,
            "last_updated_by": self.last_updated_by,
            "repos": {},
        }

        for entry in self.entries:
            report["repos"].update(
                {
                    entry.id: {
                        "message": entry.message,
                        "owner": entry.owner,
                        "started": entry.started,
                    }
                }
            )

        return json.dumps(report, indent=4, sort_keys=True)

    def add(self, repo_ids, **kwargs):
        """Add entries to maintenance report and update the timestamp. Every
        entry added to the report represents a repository in maintenace mode.

        Args:
            repo_ids (list[str]):
                A list of repository ids. New entries with these repository ids will
                be added to the maintenance report.

            Optional keyword args:
                message (str):
                    Reason why put the repo to maintenance.
                owner (str):
                    Who set the maintenance mode.

        """
        message = kwargs.get("message") or "Maintenance mode is enabled"
        owner = kwargs.get("owner") or OWNER

        to_add = []
        for repo in repo_ids:
            to_add.append(
                MaintenanceEntry(
                    id=repo, owner=owner, message=message, started=iso_time_now()
                )
            )
        entries = list(self.entries)
        entries.extend(to_add)

        return MaintenanceReport(last_updated_by=owner, entries=tuple(entries))

    def remove(self, repo_ids, **kwargs):
        """Remove entries from the maintenece report. Once the entry is removed,
        it means the corresponding repository isn't in maintenance mode anymore.

        Args:
            repo_ids (list[str]):
                A list of repository ids. Entries match repository ids will be removed
                from the maintenance report.

            Optional keyword args:
                owner (str):
                    Who unset the maintenance mode.
        """
        owner = kwargs.get("owner") or OWNER

        repo_ids = set(repo_ids)
        # convert to set, make checking faster
        to_remove = []
        for entry in self.entries:
            if entry.id in repo_ids:
                to_remove.append(entry)

        entries = list(self.entries)
        for entry in to_remove:
            entries.remove(entry)

        return MaintenanceReport(last_updated_by=owner, entries=tuple(entries))
