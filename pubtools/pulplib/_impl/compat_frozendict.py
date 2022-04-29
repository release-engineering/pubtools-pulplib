import sys

if sys.version_info >= (3, 0):
    # pylint: disable=unused-import,no-name-in-module
    from frozendict.core import frozendict
else:
    frozendict = dict  # pragma: no cover
