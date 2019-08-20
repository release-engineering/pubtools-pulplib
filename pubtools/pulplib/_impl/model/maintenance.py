import logging
import datetime
import json
import re

import jsonschema

from pubtools.pulplib._impl import compat_attr as attr
from ..schema import load_schema
from .common import InvalidDataException


LOG = logging.getLogger("pubtools.pulplib")

def _iso_time_now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


@attr.s(kw_only=True)
class MaintainedRepo(object):
    """Details about the maintenance"""

    message = attr.ib(default=None, type=str)
    """Why this repository is in maintenance"""
    owner = attr.ib(default=None, type=str)
    """Who set this repository in maintenance mode"""
    started = attr.ib(default=None, type=str)
    """When did the maintenance start"""

@attr.s(kw_only=True)
class MaintenanceReport(object):
    """Represent the maintenance status of pulp"""

    _SCHEMA = load_schema("maintenance")

    last_updated = attr.ib(default=_iso_time_now(), type=str)
    """:class:`~datetime.datetime` in UTC when this report was last updated,
    if it's the first time the report is created, current time is used."""

    last_updated_by = attr.ib(default="Content Delivery", type=str)
    """Person/party who updated the report last time"""

    repos = attr.ib(default=None, type=dict)
    """A dictionary contains repo_id: :class:`MaintainedRepo` pairs, indicates
    which repositories are in maintenance mode and details.
    If empty, then it means no repositories is in maintenance mode.
    """

    @classmethod
    def from_data(cls, data):
        """Create a new report with a dictionary"""
        try:
            jsonschema.validate(instance=data, schema=cls._SCHEMA)
        except jsonschema.exceptions.ValidationError as error:
            LOG.exception("%s.from_data invoked with invalid data", cls.__name__)
            raise InvalidDataException(str(error))

        maintenance = cls(
            last_updated=data["last_updated"],
            last_updated_by=data["last_updated_by"],
            repos={},
        )
        for repo_id, details in data["repos"].iteritems():
            maintenance.repos[repo_id] = MaintainedRepo(**details)

        return maintenance

    def json(self):
        """Output a json format report.

        Returns:
            A string contains the maintenance report in json format.
        """
        report = {
            "last_updated": self.last_updated,
            "last_updated_by": self.last_updated_by,
            "repos": {},
        }

        for repo_id, details in self.repos.iteritems():
            report["repos"].update(
                {
                    repo_id: {
                        "message": details.message,
                        "owner": details.owner,
                        "started": details.started,
                    }
                }
            )

        return json.dumps(report, indent=4, sort_keys=True)

    def add(self, repo_ids, **kwargs):
        """Add entries to maintenance report and update the timestamp. Every
        entry added to the report represents a repository in maintenace mode.

        Args:
            repo_ids (list[str]):
            A list of repositories ids that will be added to the report.

            Optional keyword args:
                message (str):
                    Reason why put the repo to maintenance.
                owner (str):
                    Who set the maintenance mode.

        """
        message = kwargs.get('message') or "Maintenance mode is enabled"
        owner = kwargs.get('owner') or "Content Delivery"

        for repo in repo_ids:
            self.repos[repo] = MaintainedRepo(
                owner=owner, message=message, started=_iso_time_now()
            )

        self._update_owner_time(owner)

    def remove(self, regex, **kwargs):
        """Remove entries from the maintenece report. Once the entry is removed,
        it means the corresponding repository isn't in maintenance mode anymore.

        Args:
            regex (str):
                A python regular expression style pattern used to match repository
                ids in the report. The matched entries will be removed.

            Optional keyword args:
                owner (str):
                    Who unset the maintenance mode.
        """
        owner = kwargs.get('owner') or "Content Delivery"


        to_remove = []
        for repo_id in self.repos:
            if re.match(regex, repo_id):
                to_remove.append(repo_id)

        for repo_id in to_remove:
            self.repos.pop(repo_id)

        self._update_owner_time(owner)

    def _update_owner_time(self, owner):
        self.last_updated_by = owner or "Content Delivery"
        self.last_updated = _iso_time_now()