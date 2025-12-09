"""A Python library that provides data acquisition and processing assets shared between Sun (NeuroAI) lab libraries.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    TrackingData,
    InjectionData,
    ProcedureData,
    ProcessedData,
    ZaberPositions,
    DatasetTrackers,
    ManagingTrackers,
    MesoscopeCameras,
    ProcessingStatus,
    ProcessingTracker,
    AcquisitionSystems,
    MesoscopePositions,
    ProcessingTrackers,
    MesoscopeFileSystem,
    ProcessingPipelines,
    ServerConfiguration,
    MesoscopeGoogleSheets,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    MesoscopeExternalAssets,
    MesoscopeExperimentState,
    MesoscopeExperimentTrial,
    WindowCheckingDescriptor,
    MesoscopeMicroControllers,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    get_system_configuration_data,
)
from .data_transfer import (
    delete_directory,
    transfer_directory,
    calculate_directory_checksum,
)

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    "AcquisitionSystems",
    "DatasetTrackers",
    "DrugData",
    "ImplantData",
    "InjectionData",
    "LickTrainingDescriptor",
    "ManagingTrackers",
    "MesoscopeCameras",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeExperimentState",
    "MesoscopeExperimentTrial",
    "MesoscopeExternalAssets",
    "MesoscopeFileSystem",
    "MesoscopeGoogleSheets",
    "MesoscopeHardwareState",
    "MesoscopeMicroControllers",
    "MesoscopePositions",
    "MesoscopeSystemConfiguration",
    "ProcedureData",
    "ProcessedData",
    "ProcessingPipelines",
    "ProcessingStatus",
    "ProcessingTracker",
    "ProcessingTrackers",
    "RawData",
    "RunTrainingDescriptor",
    "ServerConfiguration",
    "SessionData",
    "SessionTypes",
    "SubjectData",
    "SurgeryData",
    "TrackingData",
    "WindowCheckingDescriptor",
    "ZaberPositions",
    "calculate_directory_checksum",
    "delete_directory",
    "get_google_credentials_path",
    "get_server_configuration",
    "get_system_configuration_data",
    "get_working_directory",
    "transfer_directory",
]
