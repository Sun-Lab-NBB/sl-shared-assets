from sl_shared_assets.tools.project_management_tools import ProjectManifest
from pathlib import Path

file = Path("/home/cyberaxolotl/Data/TestMice_manifest.feather")
manifest = ProjectManifest(file)
manifest.print_summary(6)