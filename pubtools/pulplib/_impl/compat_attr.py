import sys

import attr


# pylint: disable=invalid-name

# Wrappers around attr module to handle some Py2 vs Py3 incompatibilities.

if sys.version_info < (3,):  # pragma: no cover

    def s(*args, **kwargs):
        if "kw_only" in kwargs:
            # This is only implemented for Python 3.
            # attrs will raise if kw_only is provided on Py2.
            # To avoid having to deal with this everywhere, we'll just silently
            # accept the keyword on Py2.
            #
            # Note this means we're technically exporting a different API on
            # Py2 vs Py3, i.e. keywords-only isn't enforced on Py2.
            # This isn't ideal, but is mitigated by the fact that any new code
            # using this library will surely not be tested solely on Py2.
            kwargs = kwargs.copy()
            del kwargs["kw_only"]

        return attr.s(*args, **kwargs)


else:
    s = attr.s

ib = attr.ib
Factory = attr.Factory
fields = attr.fields
fields_dict = attr.fields_dict
evolve = attr.evolve
