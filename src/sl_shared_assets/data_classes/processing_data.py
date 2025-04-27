from dataclasses import dataclass
from ataraxis_data_structures import YamlConfig


@dataclass()
class ProcessingTracker(YamlConfig):
    """Tracks the data processing status for a single session.

    This class is used during BioHPC-server data processing runtimes to track which processing steps are enabled and
    have been successfully applied to a given session. This is used to optimize data processing and avoid unnecessary
    processing step repetitions where possible.

    Notes:
        This class uses a similar mechanism for determining whether a particular option is enabled as the
        HardwareConfiguration class. Specifically, if any field of the class is set to None (null), the processing
        associated with that field is disabled. Otherwise, if the field is False, that session has not been processed
        and, if True, the session has been processed.
    """

    checksum: bool | None = None
    """Tracks whether session data integrity has been verified using checksum recalculation method. This step should 
    be enabled for all sessions to ensure their data was transmitted intact."""
    log_extractions: bool | None = None
    """Tracks whether session's behavior and runtime logs have been parsed to extract the relevant data. This step 
    should be enabled for all sessions other than the 'Window checking' session type, which does not generate any log 
    data."""
    suite2p: bool | None = None
    """Tracks whether the Mesoscope-acquired brain activity data has been processed (registered) using sl-suite2p. 
    This step should eb enabled for all experiment sessions that collect brain activity data."""
    deeplabcut: bool | None = None
    """Tracks whether session's videos have been processed using DeepLabCut to extract pose estimation and various 
    animal body part tracking. This step should only be enabled for projects that need to track this data."""