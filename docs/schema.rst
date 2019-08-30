.. _schemas:

Schemas
=======

This document shows the schemas for Pulp data understood by this library,
in `JSON schema`_ format.

These schemas may be useful when providing data to the
:meth:`~pubtools.pulplib.PulpObject.from_data` methods, or as a general
reference.

.. contents::
  :local:


Repository
----------

.. include:: ../pubtools/pulplib/_impl/schema/repository.yaml
    :code: yaml


Task
----

.. include:: ../pubtools/pulplib/_impl/schema/task.yaml
    :code: yaml


Unit
----

.. include:: ../pubtools/pulplib/_impl/schema/unit.yaml
    :code: yaml


Maintenance
-----------

.. include:: ../pubtools/pulplib/_impl/schema/maintenance.yaml
    :code: yaml

.. _JSON schema: https://json-schema.org/
