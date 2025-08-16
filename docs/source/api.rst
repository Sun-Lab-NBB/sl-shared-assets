 .. This file provides the instructions for how to display the API documentation generated using sphinx autodoc
   extension. Use it to declare Python documentation sub-directories via appropriate modules (autodoc, etc.).

Command Line Interfaces
=======================

.. click:: sl_shared_assets.command_line_interfaces.manage:manage
   :prog: sl-manage
   :nested: full

.. click:: sl_shared_assets.command_line_interfaces.configure:configure
   :prog: sl-configure
   :nested: full

Tools
=====
.. automodule:: sl_shared_assets.tools
   :members:
   :undoc-members:
   :show-inheritance:

Data and Configuration Assets
=============================
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
