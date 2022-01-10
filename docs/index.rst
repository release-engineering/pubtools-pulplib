pubtools-pulplib
================

A Pulp library for publishing tools.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   api/client
   api/pulpcore
   api/yum
   api/files
   api/containers
   api/maintenance
   api/searching
   api/testing
   logging
   schema

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
    with Client(url='https://pulp.example.com/', auth=('admin', 'some-password')) as client:

        # Get a particular repo by ID.
        # All methods return Future instances; .result() blocks
        repo = client.get_repository('zoo').result()

        # Pulp objects have relevant methods, e.g. publish().
        # Returned future may encapsulate one or more Pulp tasks.
        publish = repo.publish().result()
