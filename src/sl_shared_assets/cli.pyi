from .server import generate_server_credentials as generate_server_credentials
from .data_classes import replace_root_path as replace_root_path

def replace_local_root_directory(path: str) -> None:
    """Replaces the root directory used to store all lab projects on the local PC with the specified directory.

    To ensure all projects are saved in the same location, this library resolves and saves the absolute path to the
    project directory when it is used for the first time. All future projects reuse the same 'root' path. Since this
    information is stored in a typically hidden user directory, this CLI can be used to replace the local directory
    path, if necessary.
    """

def generate_server_credentials_file(output_directory: str, host: str, username: str, password: str) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This CLI is used during the initial PC setup (typically, VRPC) to allow it to access the lab BioHPC server.
    """
