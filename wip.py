from pathlib import Path

from sl_shared_assets.tools.project_management_tools import resolve_checksum

resolve_checksum(
    session_path=Path("/media/Data/MaalstroomicFlow/15/2025-07-13-19-08-43-998260"),
    regenerate_checksum=False,
    create_processed_data_directory=False,
    manager_id=1234,
)
