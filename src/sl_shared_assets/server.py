from dataclasses import dataclass
from ataraxis_data_structures import YamlConfig
from pathlib import Path


def generate_server_credentials(
    output_directory: Path, username: str, password: str, host: str = "cbsuwsun.biohpc.cornell.edu"
) -> None:
    """Generates a new server_credentials.yaml file under the specified directory, using input information.

    This function provides a convenience interface for generating new BioHPC server credential files. Generally, this is
    only used when setting up new host-computers in the lab.
    """
    ServerCredentials(username=username, password=password, host=host).to_yaml(
        file_path=output_directory.joinpath("server_credentials.yaml")
    )


@dataclass()
class ServerCredentials(YamlConfig):
    """This class stores the hostname and credentials used to log into the BioHPC cluster to run Sun lab processing
    pipelines.

    Primarily, this is used during runtime to start data processing once it is transferred to the BioHPC server during
    preprocessing.
    """

    username: str = "YourNetID"
    """The username to use for server authentication."""
    password: str = "YourPassword"
    """The password to use for server authentication."""
    host: str = "cbsuwsun.biohpc.cornell.edu"
    """The hostname or IP address of the server to connect to."""
