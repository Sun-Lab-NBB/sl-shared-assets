"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Yuantao Deng
"""

from ataraxis_base_utilities import console

from .tools import transfer_directory, calculate_directory_checksum
from .server import Server, ServerCredentials
from .suite2p import MultiDayS2PConfiguration, SingleDayS2PConfiguration
from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    InjectionData,
    MesoscopeData,
    ProcedureData,
    ProcessedData,
    DeepLabCutData,
    ZaberPositions,
    ExperimentState,
    VRPCDestinations,
    ConfigurationData,
    MesoscopePositions,
    VRPCPersistentData,
    ProjectConfiguration,
    HardwareConfiguration,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    ExperimentConfiguration,
    ScanImagePCPersistentData,
    MesoscopeExperimentDescriptor,
)

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    # Server module
    "Server",
    "ServerCredentials",
    # Suite2p package
    "SingleDayS2PConfiguration",
    "MultiDayS2PConfiguration",
    # Data classes module
    "DrugData",
    "ImplantData",
    "SessionData",
    "RawData",
    "ProcessedData",
    "ConfigurationData",
    "DeepLabCutData",
    "VRPCPersistentData",
    "ScanImagePCPersistentData",
    "MesoscopeData",
    "VRPCDestinations",
    "SubjectData",
    "SurgeryData",
    "InjectionData",
    "ProcedureData",
    "ZaberPositions",
    "ExperimentState",
    "MesoscopePositions",
    "ProjectConfiguration",
    "HardwareConfiguration",
    "RunTrainingDescriptor",
    "LickTrainingDescriptor",
    "ExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    # Transfer tools module
    "transfer_directory",
    # Packaging tools module
    "calculate_directory_checksum",
]
