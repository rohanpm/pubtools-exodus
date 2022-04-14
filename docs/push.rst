push
====

.. argparse::
   :module: pubtools.exodus._tasks.push
   :func: doc_parser
   :prog: pubtools-exodus-push


Example
.......

A typical invocation to push a staged directory would look like this:

.. code-block:: shell

  pubtools-exodus-push \
    staged:/path/to/staged/content

Note that the ``pubtools-exodus-push`` command accepts any source of content supported
by the `pushsource library <https://release-engineering.github.io/pushsource/>`_.


Example: additional exodus-rsync arguments
..........................................

The ``pubtools-exodus-push`` command also accepts arguments supported by
`exodus-rsync <https://github.com/release-engineering/exodus-rsync/>`_.

``exodus-rsync`` arguments one might wish to provide to ``pubtools-exodus-push``:

.. code-block:: shell

   pubtools-exodus-push \
     --dry-run \
     --exodus-conf=/path/to/exodus-rsync.conf \ 
     staged:/path/to/staged/content
