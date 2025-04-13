from pathlib import Path

import appdirs
from ataraxis_base_utilities import ensure_directory_exists


def replace_root_path(path: Path) -> None:
    """Replaces the path to the local root directory used to store all Sun lab projects with the provided path.

    When ProjectConfiguration class is instantiated for the first time on a new machine, it asks the user to provide
    the path to the local directory where to save all Sun lab projects. This path is then stored inside the default
    user data directory as a .yaml file to be reused for all future projects. To support replacing this path without
    searching for the user data directory, which is usually hidden, this function finds and updates the contents of the
    file that stores the local root path.

    Args:
        path: The path to the new local root directory.
    """
    # Resolves the path to the static .txt file used to store the local path to the root directory
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("root_path.txt")

    # In case this function is called before the app directory is created, ensures the app directory exists
    ensure_directory_exists(path_file)

    # Ensures that the input root directory exists
    ensure_directory_exists(path)

    # Replaces the contents of the root_path.txt file with the provided path
    with open(path_file, "w") as f:
        f.write(str(path))
