"""A Python library that stores assets shared between multiple Sun (NeuroAI) lab data pipelines.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Yuantao Deng
"""

from ataraxis_base_utilities import console

from .server import Server, ServerCredentials
from .suite2p import (
    Suite2PConfiguration,
)
from .data_classes import (
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
    ZaberPositions,
    ExperimentState,
    ProcessingTracker,
    MesoscopePositions,
    ProjectConfiguration,
    HardwareConfiguration,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    ExperimentConfiguration,
    MesoscopeExperimentDescriptor,
)
from .transfer_tools import transfer_directory
from .packaging_tools import calculate_directory_checksum

# Ensures console is enabled when this library is imported
if not console.enabled:
    console.enable()

__all__ = [
    # Server module
    "Server",
    "ServerCredentials",
    # Suite2p module
    "Suite2PConfiguration",
    # Data classes module
    "DrugData",
    "ImplantData",
    "SessionData",
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
    "ProcessingTracker",
    # Transfer tools module
    "transfer_directory",
    # Packaging tools module
    "calculate_directory_checksum",
]
