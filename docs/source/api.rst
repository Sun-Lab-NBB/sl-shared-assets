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

Packaging Tools
===============
.. automodule:: sl_shared_assets.packaging_tools
   :members:
   :undoc-members:
   :show-inheritance:

Transfer Tools
==============
.. automodule:: sl_shared_assets.transfer_tools
   :members:
   :undoc-members:
   :show-inheritance:

Suite2P Configuration Classes
=============================
.. automodule:: sl_shared_assets.suite2p
   :members:
   :undoc-members:
   :show-inheritance:

General Configuration and Data Storage Classes
==============================================
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