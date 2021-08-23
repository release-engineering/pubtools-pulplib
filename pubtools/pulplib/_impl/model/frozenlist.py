import functools


class FrozenList(list):
    # An immutable list subclass, intended for use on model fields.

    # Set of overridden methods is taken from collections.abc.MutableSequence.

    def __raise_immutable(self):
        raise NotImplementedError("cannot modify immutable list")

    def __setitem__(self, *_args, **_kwargs):
        self.__raise_immutable()

    def __delitem__(self, *_args, **_kwargs):
        self.__raise_immutable()

    def __iadd__(self, *_args, **_kwargs):
        self.__raise_immutable()

    def insert(self, *_args, **_kwargs):
        self.__raise_immutable()

    def append(self, *_args, **_kwargs):
        self.__raise_immutable()

    def extend(self, *_args, **_kwargs):
        self.__raise_immutable()

    def pop(self, *_args, **_kwargs):
        self.__raise_immutable()

    def remove(self, *_args, **_kwargs):
        self.__raise_immutable()

    # FrozenList is hashable if everything within it is hashable
    def __hash__(self):
        return hash(tuple(self))


def frozenlist_or_none_converter(obj, map_fn=(lambda x: x)):
    if obj is not None:
        return FrozenList(map_fn(obj))
    return None


frozenlist_or_none_sorted_converter = functools.partial(
    frozenlist_or_none_converter, map_fn=sorted
)
