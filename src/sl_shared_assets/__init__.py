"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .tools import (
    ProjectManifest,
    resolve_p53_marker,
    transfer_directory,
    generate_project_manifest,
    calculate_directory_checksum,
)
from .server import Job, Server, JupyterJob, ServerCredentials
from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    InjectionData,
    ProcedureData,
    ProcessedData,
    MesoscopePaths,
    ZaberPositions,
    ExperimentState,
    ExperimentTrial,
    MesoscopeCameras,
    TrackerFileNames,
    ProcessingTracker,
    AcquisitionSystems,
    MesoscopePositions,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeMicroControllers,
    MesoscopeAdditionalFirmware,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
    generate_manager_id,
    get_processing_tracker,
    get_system_configuration_data,
    set_system_configuration_file,
)

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    "AcquisitionSystems",
    "DrugData",
    "ExperimentState",
    "ExperimentTrial",
    "ImplantData",
    "InjectionData",
    "Job",
    "JupyterJob",
    "LickTrainingDescriptor",
    "MesoscopeAdditionalFirmware",
    "MesoscopeCameras",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeHardwareState",
    "MesoscopeMicroControllers",
    "MesoscopePaths",
    "MesoscopePositions",
    "MesoscopeSystemConfiguration",
    "ProcedureData",
    "ProcessedData",
    "ProcessingTracker",
    "ProjectManifest",
    "RawData",
    "RunTrainingDescriptor",
    "Server",
    "ServerCredentials",
    "SessionData",
    "SessionTypes",
    "SubjectData",
    "SurgeryData",
    "TrackerFileNames",
    "WindowCheckingDescriptor",
    "ZaberPositions",
    "calculate_directory_checksum",
    "generate_manager_id",
    "generate_project_manifest",
    "get_processing_tracker",
    "get_system_configuration_data",
    "resolve_p53_marker",
    "set_system_configuration_file",
    "transfer_directory",
]
