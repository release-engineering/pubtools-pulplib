API: searching
==============

.. _model_fields:

Model vs Pulp fields
....................

.. versionadded:: 1.3.0

The :class:`~pubtools.pulplib.Criteria` and :class:`~pubtools.pulplib.Matcher`
classes are able to operate on two types of fields:

- Model fields: fields documented on the :class:`~pubtools.pulplib.PulpObject`
  class hierarchy.  ``eng_product_id`` from the
  :class:`~pubtools.pulplib.Repository` class is an example of a model field.

- Pulp fields: any arbitrary fields within the Pulp 2.x database.
  ``notes.eng_product`` is an example of a Pulp field.

Generally, searching on model fields should be preferred when possible,
as this allows your code to avoid a dependency on Pulp implementation details
and allows you to use the same field names everywhere.

However, not all model fields support this, as not every model field has
a direct mapping with a Pulp field.  Attempting to search on an unsupported
model field will raise an exception.


Class reference
...............

.. autoclass:: pubtools.pulplib.Criteria
   :members:

.. autoclass:: pubtools.pulplib.Matcher
   :members:

.. autoclass:: pubtools.pulplib.Page
   :members:
