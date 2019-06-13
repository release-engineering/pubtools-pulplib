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
