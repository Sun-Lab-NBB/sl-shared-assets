from .tools import ascend_tyche_data as ascend_tyche_data
from .server import generate_server_credentials as generate_server_credentials
from .data_classes import replace_root_path as replace_root_path

def replace_local_root_directory(path: str) -> None:
    """Replaces the root directory used to store all lab projects on the local PC with the specified directory.

    To ensure all projects are saved in the same location, this library resolves and saves the absolute path to the
    project directory the first time ProjectConfiguration class instance is created on a new PC. All future projects
    automatically reuse the same 'root' directory path. Since this information is stored in a typically hidden user
    directory, this CLI can be used to replace the local directory path, if necessary.
    """

def generate_server_credentials_file(output_directory: str, host: str, username: str, password: str) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This CLI is used to set up new PCs to work with the lab BioHPC server. While this is primarily intended for the
    VRPC, any machined that interacts with BioHPC server can use this CLI to build the access credentials file.
    """

def ascend_tyche_directory(path: str, output_directory: str, server_directory: str) -> None:
    """Restructures old Tyche project data to use the modern Sun lab data structure.

    This CLI is used to convert ('ascend') the old Tyche project data to the modern Sun lab structure. After
    ascension, the data can be processed and analyzed using all modern Sun lab (sl-) tools and libraries. Note, this
    process expects the input data to be preprocessed using an old Sun lab mesoscope data preprocessing pipeline. It
    will not work for any other project or data.
    """
