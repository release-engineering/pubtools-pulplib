Logging
=======

``pubtools-pulplib`` produces various log messages which may be of interest to
clients.

These log messages are sent to the ``pubtools.pulplib`` :class:`~logging.Logger`. For a
general-purpose command, it's recommended to enable this logger at ``INFO`` level.


Waiting on Pulp
---------------

If the library is awaiting the completion of Pulp tasks and no progress is being
made, it will produce an ``INFO`` log message every few minutes with a count of the
running and waiting tasks in Pulp, such as:

.. code-block::

  [INFO] Still waiting on Pulp, load: 1 running, 3 waiting
  [INFO] Still waiting on Pulp, load: 2 running, 39 waiting
  [INFO] Still waiting on Pulp, load: 1 running, 39 waiting
  [INFO] Still waiting on Pulp, load: 1 running, 39 waiting

These messages will include an ``event`` attribute of the form:

.. code-block:: yaml

  event:
    type: awaiting-pulp
    running-tasks: <count>
    waiting-tasks: <count>


Task state changes
------------------

A log message will be produced when a Pulp task is created, cancelled,
succeeds or fails. Failed Pulp tasks produce a ``WARNING``; other state
changes produce an ``INFO`` message.

.. code-block::

  [INFO] Created Pulp task: 54ba8e8c-10aa-40f9-a9a9-36be54431bde
  [INFO] Pulp task completed: 54ba8e8c-10aa-40f9-a9a9-36be54431bde


Retrying
--------

Many methods in this library will implicitly retry failing operations a few times.
When this occurs, a ``WARNING`` message is logged before the retry occurs, as
in the following examples:

.. code-block::

  [WARNING] Retrying due to error: 401 Client Error: Unauthorized for url: https://pulp.example.com/pulp/api/v2/repositories/search/ [1/10]
  [WARNING] Retrying due to error: Task e239ae4f-7fad-4004-bfb6-8e06f17d22ef failed [3/10]

The ``[1/10]`` indicator shows the current attempt at the operation and the maximum
number of attempts before the error will be considered fatal.

These messages will include an ``event`` attribute of the form:

.. code-block:: yaml

  event:
    type: pulp-retry
