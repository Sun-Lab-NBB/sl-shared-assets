 .. This file provides the instructions for how to display the API documentation generated using sphinx autodoc
   extension. Use it to declare Python documentation sub-directories via appropriate modules (autodoc, etc.).

Command Line Interfaces
=======================

.. automodule:: sl_shared_assets.cli
   :members:
   :undoc-members:
   :show-inheritance:

.. click:: sl_shared_assets.cli:replace_local_root_directory
   :prog: sl-replace-root
   :nested: full

.. click:: sl_shared_assets.cli:generate_server_credentials_file
   :prog: sl-generate-credentials
   :nested: full

.. click:: sl_shared_assets.cli:ascend_tyche_directory
   :prog: sl-ascend
   :nested: full

Tools
=====
.. automodule:: sl_shared_assets.tools
   :members:
   :undoc-members:
   :show-inheritance:

Suite2P Configuration
=====================
.. automodule:: sl_shared_assets.suite2p
   :members:
   :undoc-members:
   :show-inheritance:

General Data and Configuration Classes
======================================
.. automodule:: sl_shared_assets.data_classes
   :members:
   :undoc-members:
   :show-inheritance:

Compute Server Tools
====================
.. automodule:: sl_shared_assets.server
   :members:
   :undoc-members:
   :show-inheritance:
