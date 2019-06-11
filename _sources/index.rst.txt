pubtools-pulplib
================

A Pulp library for publishing tools.

.. warning::
    As of 2019-06, this project is considered **alpha**.
    All API is subject to change without warning.
    Information in these docs may be missing or wrong.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api-reference

Quick Start
-----------

Install pubtools-pulplib from PyPI:

::

    pip install pubtools-pulplib

In your Python code, construct a ``pubtools.pulplib.Client`` and call
the desired methods to perform actions on Pulp.

.. code-block:: python

    from pubtools.pulplib import Client

    # Make a client pointing at this Pulp server
    client = Client(url='https://pulp.example.com/', user='admin', password='admin')

    # Get a particular repo by ID.
    # All methods return Future instances; .result() blocks
    repo = client.get_repository('zoo').result()

    # Pulp objects have relevant methods, e.g. publish().
    # Returned future may encapsulate one or more Pulp tasks.
    publish = repo.publish().result()
