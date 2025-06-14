 .. This file provides the instructions for how to display the API documentation generated using sphinx autodoc
   extension. Use it to declare Python documentation sub-directories via appropriate modules (autodoc, etc.).

Command Line Interfaces
=======================

.. automodule:: sl_shared_assets.cli
   :members:
   :undoc-members:
   :show-inheritance:

.. click:: sl_shared_assets.cli:verify_session_integrity
   :prog: sl-verify-session
   :nested: full

.. click:: sl_shared_assets.cli:generate_project_manifest_file
   :prog: sl-project-manifest
   :nested: full

.. click:: sl_shared_assets.cli:generate_system_configuration_file
   :prog: sl-create-system-config
   :nested: full

.. click:: sl_shared_assets.cli:generate_server_credentials_file
   :prog: sl-create-server-credentials
   :nested: full

.. click:: sl_shared_assets.cli:generate_project_configuration_file
   :prog: sl-create-project
   :nested: full

.. click:: sl_shared_assets.cli:generate_experiment_configuration_file
   :prog: sl-create-experiment
   :nested: full

.. click:: sl_shared_assets.cli:ascend_tyche_directory
   :prog: sl-ascend-tyche
   :nested: full

Tools
=====
.. automodule:: sl_shared_assets.tools
   :members:
   :undoc-members:
   :show-inheritance:

Data and Configuration Classes
==============================
.. automodule:: sl_shared_assets.data_classes
   :members:
   :undoc-members:
   :show-inheritance:

Server
======
.. automodule:: sl_shared_assets.server
   :members:
   :undoc-members:
   :show-inheritance:
