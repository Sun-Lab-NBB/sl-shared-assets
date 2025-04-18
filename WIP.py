from pathlib import Path

from sl_shared_assets import SessionData, transfer_directory

root_folder = Path("/media/Data/Experiments/Tyche")

raw_data_paths = [folder for folder in root_folder.rglob("session_data.yaml")]

for source in raw_data_paths:
    sd = SessionData.load(session_path=source.parents[1], on_server=False)
    transfer_directory(
        source=sd.raw_data.raw_data_path, destination=sd.destinations.server_raw_data_path, verify_integrity=False
    )
