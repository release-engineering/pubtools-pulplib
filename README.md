pubtools-pulplib
================

A Python client for [Pulp 2.x](https://pulpproject.org/), used by
[release-engineering](https://github.com/release-engineering) publishing tools.

[![Build Status](https://github.com/release-engineering/pubtools-pulplib/actions/workflows/tox-test.yml/badge.svg)](https://github.com/release-engineering/pubtools-pulplib/actions/workflows/tox-test.yml)
[![codecov](https://codecov.io/gh/release-engineering/pubtools-pulplib/branch/master/graph/badge.svg?token=CABMY3WeIB)](https://codecov.io/gh/release-engineering/pubtools-pulplib)

- [Source](https://github.com/release-engineering/pubtools-pulplib)
- [Documentation](https://release-engineering.github.io/pubtools-pulplib/)
- [PyPI](https://pypi.org/project/pubtools-pulplib)


Installation
------------

Install the `pubtools-pulplib` package from PyPI.

```
pip install pubtools-pulplib
```


Usage Example
-------------

```python
from pubtools.pulplib import Client

# Make a client pointing at this Pulp server
with Client(url='https://pulp.example.com/', auth=('admin', 'some-password')) as client:

  # Get a particular repo by ID.
  # All methods return Future instances; .result() blocks
  repo = client.get_repository('zoo').result()

  # Pulp objects have relevant methods, e.g. publish().
  # Returned future may encapsulate one or more Pulp tasks.
  publish = repo.publish().result()
```

Development
-----------

Patches may be contributed via pull requests to
https://github.com/release-engineering/pubtools-pulplib.

All changes must pass the automated test suite, along with various static
checks.

The [Black](https://black.readthedocs.io/) code style is enforced.
Enabling autoformatting via a pre-commit hook is recommended:

```
pip install -r requirements-dev.txt
pre-commit install
```

License
-------

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
