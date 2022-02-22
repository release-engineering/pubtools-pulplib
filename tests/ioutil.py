class ZeroesIO(object):
    """A minimal file-like object which returns a specified number of zero bytes."""

    def __init__(self, count):
        self._remaining = count

    def read(self, size):
        size = min(size, self._remaining)
        out = b"\x00" * size
        self._remaining -= size
        return out

    def close(self):
        pass
