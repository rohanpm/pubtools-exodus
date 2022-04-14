exodus-gw configuration
=======================


Required environment variables
..............................

All Exodus CDN operations must go through `exodus-gw <https://release-engineering.github.io/exodus-gw/>`_.

pubtools-exodus authenticates to ``exodus-gw`` using the following environment variables:

* ``EXODUS_GW_ENV`` (the name of the ``exodus-gw`` environment to operate against)
* ``EXODUS_GW_URL`` (the URL for the ``exodus-gw`` environment to operate against)
* ``EXODUS_GW_CERT`` (the local path to a cert used to authenticate with ``exodus-gw``)
* ``EXODUS_GW_KEY`` (the local path to a key used to authenticate with ``exodus-gw``)

If any of the required environment variables are not set, ``pubtools-exodus`` operations will
fail with a runtime error.


Required configuration file
...........................

The ``pubtools-exodus-push`` entry point is a wrapper around `exodus-rsync <https://github.com/release-engineering/exodus-rsync/>`_. As such, any configuration
required for ``exodus-rsync`` is also required for ``pubtools-exodus-push``. ``exodus-rsync`` uses a `configuration file <https://github.com/release-engineering/exodus-rsync/#configuration>`_ to authenticate with ``exodus-gw``.

The ``exodus-rsync`` configuration file should look something like this:

.. code-block:: shell

   $ cat /etc/exodus-rsync.conf
     gwcert: $EXODUS_GW_CERT
     gwkey: $EXODUS_GW_KEY
     gwenv: $EXODUS_GW_ENV
     gwurl: $EXODUS_GW_URL
     environments:
       prefix: exodus


To enforce consistency between the ``exodus-gw`` authentication parameters provided by ``pubtools-exodus``
and ``exodus-rsync``, the ``gwcert``, ``gwkey``, ``gwenv``, and ``gwurl`` keys should be assigned
their respective ``EXODUS_GW_*`` environment variable. Note that the ``exodus-rsync`` configuration 
file supports environment variable expansion. The variables will be expanded at run-time.

Please see the `exodus-rsync configuration <https://github.com/release-engineering/exodus-rsync/#configuration>`_ documentation for more details.


Enabling pulp hooks
...................

``pubtools-exodus`` can optionally extend the behavior of other projects in the pubtools family,
causing them to integrate with ``exodus-gw``. This is enabled if and only if the ``EXODUS_ENABLED``
environment variable is set to one of the following values (strings are not case-sensitive):

* "1"
* "true"
* "t"
* "yes"
* "y"
