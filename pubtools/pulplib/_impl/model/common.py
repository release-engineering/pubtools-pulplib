import logging
import datetime

import jsonschema
import six

from more_executors.futures import f_map, f_proxy

from pubtools.pulplib._impl import compat_attr as attr
from pubtools.pulplib._impl.util import lookup, dict_put

from .attr import PULP2_FIELD
from .convert import get_converter

LOG = logging.getLogger("pubtools.pulplib")


class DetachedException(Exception):
    """If an operation is attempted on a Pulp object which requires an active client,
    and the object is not attached to any client, this exception is raised.
    """


class InvalidDataException(Exception):
    """Raised if raw Pulp data appears to be invalid (i.e. not matching expected schema)."""


class PulpObject(object):
    """Base class for all modeled Pulp objects.

    Instances of PulpObject subclasses may be obtained by get and search methods
    on :class:`~pubtools.pulplib.Client`, or may be instantiated directly by calls
    to :meth:`from_data` when the client is not used.

    Objects which are created via a client may be used to issue further requests
    to Pulp (for example, to update or delete the object).

    Pulp objects use `attrs <http://www.attrs.org/en/stable/>`_.
    Attributes are immutable. Helper functions such as :func:`attr.evolve`
    may be used to produce new instances.

    Attributes exposed on these Pulp objects include some generic attributes
    applicable to any Pulp installation, but also some custom attributes
    which only make sense for `release-engineering <https://github.com/release-engineering>`_
    Pulp servers.
    """

    # Classes should put a valid JSON schema here. This one will refuse to
    # validate anything.
    _SCHEMA = False

    @classmethod
    def from_data(cls, data):
        """Obtain a detached instance using data obtained from Pulp.

        This method is provided so that callers who are not using
        :class:`~pubtools.pulplib.Client` may make use of the Pulp object classes.

        This method must be invoked on the appropriate ``PulpObject`` subclass
        matching ``data``.  For example, ``Repository.from_data`` must be invoked
        with a repository object provided by Pulp's API.

        Args:
            data (dict)
                A dict containing a raw representation of a Pulp object, as rendered
                by Pulp's API.

        Returns:
            a new instance of ``cls``

        Raises:
            InvalidDataException
                If the provided ``data`` fails validation against an expected schema.

        Example:

            Opting-out of using the ``Client`` class and instead doing a plain ``requests.get``:

            .. code-block:: python

                url = 'https://pulp.example.com/pulp/api/v2/repositories/zoo/'
                data = requests.get(url).json()
                repo = Repository.from_data(data)
        """

        try:
            jsonschema.validate(instance=data, schema=cls._SCHEMA)

            kwargs = cls._data_to_init_args(data)
            return cls(**kwargs)

        except Exception as error:  # pylint:disable=broad-except
            LOG.exception(
                (
                    "An error occurred while loading Pulp data!\n"
                    "  Model class: %s\n"
                    "  Raw data:    %s"
                ),
                cls,
                repr(data),
            )

            msg = "%s.from_data invoked with invalid Pulp data", cls.__name__
            six.raise_from(InvalidDataException(msg), error)

    def _to_data(self):
        """Inverse of from_data: serialize a model object back to native Pulp form.

        This method is currently intended for internal use only.

        Returns:
            This object, in the native format used by pulp2 (i.e. some
            JSON-encodable type).
        """
        fields = attr.fields(type(self))

        out = {}
        for field in fields:
            pulp_field = field.metadata.get(PULP2_FIELD)

            if not pulp_field:
                # This field does not map to pulp
                continue

            python_value = getattr(self, field.name)

            # Note: in theory we should also get and use PY_PULP2_CONVERTER
            # here if that was set on the metadata. It's not currently
            # implemented because ErratumUnit is the only type for which
            # this code can be reached from public API, and it has no fields
            # which need a custom converter, so it would be dead code.
            # Implement it when you need it!
            #
            # For now, conversions supported by PulpObject are sufficient.
            pulp_value = PulpObject._any_to_data(python_value)

            # Put converted value into the output dict:
            # This may create nested dicts if needed, e.g. if
            # pulp_field is "notes.foobar", this will create a "notes"
            # dict in out if it does not already exist.
            dict_put(out, pulp_field, pulp_value)

        return out

    @classmethod
    def _any_to_data(cls, value):
        """Like the instance method _to_data, but also handles non-PulpObject values."""

        if isinstance(value, list):
            # Lists of objects are converted recursively.
            return [cls._any_to_data(elem) for elem in value]

        if isinstance(value, PulpObject):
            # It's a model object, then delegate to the instance method.
            return value._to_data()

        if isinstance(value, datetime.datetime):
            # For datetimes, we always use an ISO8601 timestamp format.
            return value.strftime("%Y-%m-%dT%H:%M:%SZ")

        # For anything else, we assume it can be used as-is.
        # strs and ints for example fall into this path.
        return value

    @classmethod
    def _data_to_init_args(cls, data):
        # maps from raw Pulp dict to a kwargs dict used to initialize
        # a new object of this class.
        #
        # The default implementation looks at defined attributes and metadata
        # (PULP2_FIELD).  If this is not sufficient, subclasses can override
        # this, and can also call super() to reuse this as needed.
        out = {}
        fields = attr.fields(cls)
        absent = object()

        for field in fields:
            pulp_field = field.metadata.get(PULP2_FIELD)
            if pulp_field:
                value = lookup(data, pulp_field, absent)
                if value is not absent:
                    converter = get_converter(field, value)
                    value = converter(value)
                    out[field.name] = value

        return out


@attr.s(kw_only=True, frozen=True)
class WithClient(object):
    # A mixin for objects holding a private reference to client.

    _client = attr.ib(default=None, init=False, repr=False, cmp=False, hash=False)

    def _set_client(self, client):
        self.__dict__["_client"] = client


class Deletable(WithClient):
    # A mixin for objects representing deletable resources.

    def __detach(self, retval):
        LOG.debug("Detaching %s after successful delete", self)
        self._set_client(None)
        return retval

    def _delete(self, resource_type, resource_id):
        client = self._client
        if not client:
            raise DetachedException()

        delete_f = client._delete_resource(resource_type, resource_id)
        delete_f = f_map(delete_f, self.__detach)
        return f_proxy(delete_f)
