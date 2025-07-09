"""This package provides the classes used to store data acquired at various stages of the data workflow and to
configure various pipelines used in the Sun lab. These classes are used across all stages of data acquisition,
preprocessing, and processing in the lab that run on multiple machines (PCs). Many classes in this package are designed
to be saved to disk as .yaml files and restored from the .yaml files as needed."""

from .runtime_data import (
    ZaberPositions,
    MesoscopePositions,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    MesoscopeExperimentDescriptor,
)
from .session_data import RawData, SessionData, ProcessedData, ProcessingTracker
from .surgery_data import (
    DrugData,
    ImplantData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
)
from .configuration_data import (
    MesoscopePaths,
    ExperimentState,
    MesoscopeCameras,
    TrialCueSequence,
    MesoscopeMicroControllers,
    MesoscopeAdditionalFirmware,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_system_configuration_data,
    set_system_configuration_file,
)

__all__ = [
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
    "MesoscopeHardwareState",
    "RunTrainingDescriptor",
    "LickTrainingDescriptor",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeSystemConfiguration",
    "set_system_configuration_file",
    "get_system_configuration_data",
    "MesoscopePaths",
    "MesoscopeCameras",
    "MesoscopeMicroControllers",
    "MesoscopeAdditionalFirmware",
    "ProcessingTracker",
    "TrialCueSequence",
]
