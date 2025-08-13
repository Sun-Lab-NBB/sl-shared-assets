from pathlib import Path

from sl_shared_assets.tools.project_management_tools import resolve_checksum

resolve_checksum(
    session_path=Path("/home/cyberaxolotl/Data/MaalstroomicFlow/15/2025-07-25-12-22-39-807526"),
    regenerate_checksum=False,
    manager_id=1234,
)
