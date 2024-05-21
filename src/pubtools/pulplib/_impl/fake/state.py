import threading
import random
import uuid
import attr


from . import units

from pubtools.pulplib import FileUnit


class FakeState(object):
    # Private class holding all state associated with fake clients.
    #
    # A single state object can be accessed by multiple clients.
    # It can be thought of as similar to the (DB & filesystem) on a real
    # Pulp installation.
    #
    # Clients modifying state must explicitly lock this object.
    # Some read operations also require holding the lock.

    _DEFAULT_TYPE_IDS = [
        "distribution",
        "drpm",
        "erratum",
        "iso",
        "modulemd_defaults",
        "modulemd",
        "package_category",
        "package_environment",
        "package_group",
        "package_langpacks",
        "repository",
        "rpm",
        "srpm",
        "yum_repo_metadata_file",
    ]

    def __init__(self):
        self.repositories = []

        # Similar to a real Pulp server, units are stored through a "unit key"
        # layer of indirection:
        # - repos contain unit keys
        # - a unit key refers to one (and only one) unit
        #
        # By storing data in this way, we ensure we have similar behavior and
        # constraints as a real Pulp server, e.g. cannot store two different units
        # which would have the same key; updating a unit referenced from multiple repos
        # effectively updates it in all repos at once; etc.
        self.repo_unit_keys = {}
        self.units_by_key = {}

        self.publish_history = []
        self.upload_history = []
        self.uploads_pending = {}
        self.sync_history = []
        self.tasks = []
        self.maintenance_report = None
        self.type_ids = self._DEFAULT_TYPE_IDS[:]
        self.seen_unit_ids = set()
        self.lock = threading.Lock()
        self.uuidgen = random.Random()
        self.uuidgen.seed(0)
        self.unitmaker = units.UnitMaker(self.seen_unit_ids)
        # map of repo id => lock claims.
        self.repo_locks = {}
        # list containing lists of the lock state changes
        self.repo_lock_history = []

    def insert_repo_units(self, repo_id, units_to_add):
        # Insert an iterable of units into a specific repo.
        #
        # If a unit with the same key exists in multiple repos, this will update
        # matching units across *all* of those repos - same as a real pulp server.
        assert self.lock.locked()

        repo_unit_keys = self.repo_unit_keys.setdefault(repo_id, set())
        memberships = []
        if repo_id is not None:
            memberships.append(repo_id)

        for unit in units_to_add:
            # Always consume a unit ID from the unitmaker even if we don't actually
            # need it. The point of this is to ensure that if you serialize/deserialize
            # a fake client, e.g. as done in pubtools-pulp, then the freshly created
            # client will not try to use the same sequence of IDs as already used in
            # the units we've just deserialized.
            unit_id = self.unitmaker.next_unit_id()

            if not unit.unit_id:
                unit = attr.evolve(unit, unit_id=unit_id)

            self.seen_unit_ids.add(unit.unit_id)

            # Unit belongs to the repo we're adding it to.
            # Note: this may be further merged with an existing unit's
            # repository_memberships a few lines below.
            unit = attr.evolve(
                unit,
                repository_memberships=(unit.repository_memberships or [])
                + memberships,
            )

            if repo_id is not None:
                # Unit might be replacing earlier units in same repo.
                self.remove_clashing_units(repo_id, unit)

            unit_key = units.make_unit_key(unit)
            old_unit = self.units_by_key.get(unit_key)
            self.units_by_key[unit_key] = units.merge_units(old_unit, unit)
            repo_unit_keys.add(unit_key)

    def remove_clashing_units(self, repo_id, unit):
        assert self.lock.locked()

        # In preparation for adding 'unit' into a repo, remove any existing
        # units from that repo which would clash, in a compatible manner as Pulp.
        #
        # Currently this is a special case only for File units: although their
        # unit_key consists of more than just 'name' making it technically possible
        # to have multiple files with the same name in a repo, Pulp has special logic
        # to try to prevent this, so we do the same here.
        if isinstance(unit, FileUnit):
            for existing in self.repo_units(repo_id):
                if isinstance(existing, FileUnit) and existing.path == unit.path:
                    self.remove_unit(repo_id, existing)

    def remove_unit(self, repo_id, unit):
        # Remove a single unit from a repository.
        assert self.lock.locked()

        unit_key = units.make_unit_key(unit)

        # Ensure unit is no longer referenced from the repo
        self.repo_unit_keys[repo_id].remove(unit_key)

        # Ensure repo ID is no longer in memberships
        new_repos = [id for id in unit.repository_memberships if id != repo_id]
        self.units_by_key[unit_key] = attr.evolve(
            unit, repository_memberships=new_repos
        )

    @property
    def all_units(self):
        # Get all units in all repos.
        #
        # Cannot be used to modify units.
        return list(self.units_by_key.values())

    def repo_units(self, repo_id):
        # Get all units in a particular repo.
        #
        # Cannot be used to modify units.
        assert self.lock.locked()

        out = []
        for key in self.repo_unit_keys.get(repo_id) or []:
            out.append(self.units_by_key[key])
        return out

    def next_task_id(self):
        next_raw_id = self.uuidgen.randint(0, 2**128)
        return str(uuid.UUID(int=next_raw_id))

    def next_request_id(self):
        return self.next_task_id()
