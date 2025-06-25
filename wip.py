from sl_shared_assets.tools.project_management_tools import ProjectManifest
from pathlib import Path

manifest = ProjectManifest(manifest_file=Path("/home/cyberaxolotl/Data/TestMice_manifest.feather"))

manifest.print_notes(animal_id="6")