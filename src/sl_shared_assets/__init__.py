"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Yuantao Deng, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .tools import transfer_directory, verify_session_checksum, generate_project_manifest, calculate_directory_checksum
from .server import Job, Server, ServerCredentials
from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    VersionData,
    InjectionData,
    ProcedureData,
    ProcessedData,
    MesoscopePaths,
    ZaberPositions,
    ExperimentState,
    MesoscopeCameras,
    ProcessingTracker,
    MesoscopePositions,
    ProjectConfiguration,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    MesoscopeMicroControllers,
    MesoscopeAdditionalFirmware,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
    get_system_configuration_data,
    set_system_configuration_file,
)

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    # Server package
    "Server",
    "ServerCredentials",
    "Job",
    # Data classes package
    "DrugData",
    "ImplantData",
    "SessionData",
    "RawData",
    "VersionData",
    "ProcessedData",
    "SubjectData",
    "SurgeryData",
    "InjectionData",
    "ProcessingTracker",
    "ProcedureData",
    "ZaberPositions",
    "ExperimentState",
    "MesoscopePositions",
    "ProjectConfiguration",
    "MesoscopeHardwareState",
    "RunTrainingDescriptor",
    "LickTrainingDescriptor",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeSystemConfiguration",
    "MesoscopePaths",
    "MesoscopeCameras",
    "MesoscopeMicroControllers",
    "MesoscopeAdditionalFirmware",
    "get_system_configuration_data",
    "set_system_configuration_file",
    # Tools package
    "transfer_directory",
    "generate_project_manifest",
    "verify_session_checksum",
    "calculate_directory_checksum",
]
