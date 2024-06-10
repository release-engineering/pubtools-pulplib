import json
import random
import string
from time import sleep
import os
import logging

from datetime import datetime, timedelta
from more_executors.futures import f_map
from requests.exceptions import HTTPError

LOCK_CLAIM_STR = "pulplib-lock-claim-"

LOCK_VALID_FROM_OFFSET = int(os.getenv("PULPLIB_LOCK_VALID_FROM_OFFSET", "10"))
LOCK_EXPIRATION_OFFSET = int(os.getenv("PULPLIB_LOCK_EXPIRATION_OFFSET", "1800"))
LOCK_EXPIRATION_OFFSET_MIN = int(os.getenv("PULPLIB_LOCK_EXPIRATION_OFFSET_MIN", "300"))
LOCK_EXPIRATION_OFFSET_MAX = int(
    os.getenv("PULPLIB_LOCK_EXPIRATION_OFFSET_MAX", "216000")
)

AWAIT_ACTIVATION_SLEEP = int(os.getenv("PULPLIB_AWAIT_ACTIVATION_SLEEP", " 10"))

LOG = logging.getLogger("pubtools.pulplib")


# datetime is a built-in so cannot be mocked directly.
# This function is a workaround to allow mocking for testing.
def now():
    return datetime.now()  # pragma: no cover


class LockClaim(object):
    def __init__(self, **kwargs):
        expiration_offset = kwargs.get("expiration_offset")
        expiration_offset = (
            expiration_offset if expiration_offset else LOCK_EXPIRATION_OFFSET
        )
        expiration_offset = max(
            min(expiration_offset, LOCK_EXPIRATION_OFFSET_MAX),
            LOCK_EXPIRATION_OFFSET_MIN,
        )
        self.id = (
            kwargs["id"]
            if "id" in kwargs
            else "".join(random.choices(string.ascii_letters + string.digits, k=8))
        )
        self.context = kwargs["context"]
        self.created = (
            datetime.fromtimestamp(kwargs["created"]) if "created" in kwargs else now()
        )
        self.valid_from = (
            datetime.fromtimestamp(kwargs["valid_from"])
            if "valid_from" in kwargs
            else self.created + timedelta(seconds=LOCK_VALID_FROM_OFFSET)
        )
        self.expires = (
            datetime.fromtimestamp(kwargs["expires"])
            if "expires" in kwargs
            else self.created + timedelta(seconds=expiration_offset)
        )

    @property
    def as_json(self):
        data = {
            "id": self.id,
            "context": self.context,
            "created": datetime.timestamp(self.created),
            "valid_from": datetime.timestamp(self.valid_from),
            "expires": datetime.timestamp(self.expires),
        }
        return json.dumps(data)

    def __lt__(self, other):
        return self.created < other.created

    def __eq__(self, other):
        return self.id == other.id

    @staticmethod
    def from_json_data(json_data):
        return LockClaim(**json_data)

    @property
    def is_valid(self):
        return self.valid_from < now() < self.expires

    @property
    def is_expired(self):
        return now() > self.expires


class RepoLock(object):
    def __init__(
        self,
        repo_id,
        client,
        lock_context,
        expiration_offset,
    ):
        self._repo_id = repo_id
        self._client = client
        self._lock_claim = None
        self._lock_context = lock_context
        self._expiration_offset = expiration_offset

    def __enter__(self):
        LOG.info("Attempting to lock %s.", self._repo_id)
        self.remove_expired_locks()
        self._lock_claim = LockClaim(
            context=self._lock_context, expiration_offset=self._expiration_offset
        )
        self.submit_lock_claim()
        self.await_lock_activation()

    def __exit__(self, exc_type, exc_value, tb):
        if self._lock_claim.is_expired:
            logging.error(
                "Client requested lock on repo %s for %s seconds "
                "but was held for %s seconds (%s)",
                self._repo_id,
                (self._lock_claim.expires - self._lock_claim.created).seconds,
                (now() - self._lock_claim.created).seconds,
                self._lock_claim.context,
            )
        self.delete_lock_claim()
        self._lock_claim = None

    def get_repo_lock_data(self, filter_invalid=False):
        LOG.debug("Getting current repo lock data for %s.", self._repo_id)
        locks_f = self._client._get_repo_lock_data(self._repo_id)
        locks_f = f_map(
            locks_f,
            lambda locks: [
                LockClaim.from_json_data(json.loads(l)) for l in locks.values()
            ],
        )
        parsed_locks = locks_f.result()
        parsed_locks.sort()
        if filter_invalid:
            parsed_locks = [l for l in parsed_locks if l.is_valid]
        return parsed_locks

    def await_lock_activation(self):
        # if `now` is later than `valid_from`, the timedelta is negative and
        # the seconds value becomes a whole day minus the timedelta ~ 86400.
        # total_seconds returns a negative time value, which we clamp.
        sleep(max((self._lock_claim.valid_from - now()).total_seconds(), 0))
        while True:
            lock_claims = self.get_repo_lock_data(filter_invalid=True)
            # If our claim is the oldest valid lock claim.
            if self._lock_claim == lock_claims[0]:
                LOG.info("Lock obtained for %s.", self._repo_id)
                return
            LOG.info("Awaiting lock for %s.", self._repo_id)
            sleep(AWAIT_ACTIVATION_SLEEP)

    def submit_lock_claim(self):
        LOG.info(
            "Submitting lock with id '%s' to %s (%s).",
            self._lock_claim.id,
            self._repo_id,
            self._lock_claim.context,
        )
        self._client._update_repo_lock_data(
            self._repo_id,
            {LOCK_CLAIM_STR + self._lock_claim.id: self._lock_claim.as_json},
        )

    def delete_lock_claim(self):
        LOG.info(
            "Deleting lock with id '%s' from %s (%s).",
            self._lock_claim.id,
            self._repo_id,
            self._lock_claim.context,
        )
        note_delta = {LOCK_CLAIM_STR + self._lock_claim.id: None}
        try:
            self._client._update_repo_lock_data(
                self._repo_id, note_delta, await_result=True
            )
        except HTTPError as e:
            if self._pulp_exception_from_missing_lock(e, list(note_delta.keys())):
                logging.error("Lock %s has already been deleted.", self._lock_claim.id)
            else:
                raise e  # pragma: no cover

    def _pulp_exception_from_missing_lock(self, e, lock_names):
        # If we try to delete a lock from pulp notes that's already been
        # deleted, it will result in a 500 error due to a KeyError exception
        # If multiple locks are sent for deletion, it appears Pulp will fail on
        # the first missing one and not carry out any deletions.
        lock_names = ["KeyError: '%s'\n" % lock for lock in lock_names]
        return any(
            [exception in lock_names for exception in e.response.json()["exception"]]
        )

    def remove_expired_locks(self):
        expired_locks = [lock for lock in self.get_repo_lock_data() if lock.is_expired]
        if expired_locks:
            for lock in expired_locks:
                LOG.warning(
                    "Removing expired lock with id %s from %s (%s).",
                    lock.id,
                    self._repo_id,
                    lock.context,
                )
            invalid_locks_delta = {
                LOCK_CLAIM_STR + lock.id: None for lock in expired_locks
            }
            try:
                self._client._update_repo_lock_data(self._repo_id, invalid_locks_delta)
            except HTTPError as e:
                if self._pulp_exception_from_missing_lock(
                    e, list(invalid_locks_delta.keys())
                ):
                    logging.error(
                        "An error occurred while trying to delete an expired "
                        "lock. The locks have already been deleted"
                    )
                else:
                    raise e  # pragma: no cover
