"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Yuantao Deng
"""

from ataraxis_base_utilities import console

from .tools import transfer_directory, calculate_directory_checksum
from .server import Server, ServerCredentials
from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
    ProcessedData,
    ZaberPositions,
    ExperimentState,
    MesoscopePositions,
    ProjectConfiguration,
    MesoscopeHardwareState,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
)

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    # Server module
    "Server",
    "ServerCredentials",
    # Data classes module
    "DrugData",
    "ImplantData",
    "SessionData",
    "RawData",
    "ProcessedData",
    "SubjectData",
    "SurgeryData",
    "InjectionData",
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
    # Transfer tools module
    "transfer_directory",
    # Packaging tools module
    "calculate_directory_checksum",
]
