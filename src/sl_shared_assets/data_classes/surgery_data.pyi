from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

@dataclass()
class SubjectData:
    """Stores information about the subject of the surgical intervention (animal)."""

    id: int
    ear_punch: str
    sex: str
    genotype: str
    date_of_birth_us: int
    weight_g: float
    cage: int
    location_housed: str
    status: str

@dataclass()
class ProcedureData:
    """Stores general information about the surgical intervention."""

    surgery_start_us: int
    surgery_end_us: int
    surgeon: str
    protocol: str
    surgery_notes: str
    post_op_notes: str
    surgery_quality: int = ...

@dataclass
class ImplantData:
    """Stores information about a single implantation procedure performed during the surgical intervention.

    Multiple ImplantData instances can be used at the same time if the surgery involves multiple implants.
    """

    implant: str
    implant_target: str
    implant_code: str
    implant_ap_coordinate_mm: float
    implant_ml_coordinate_mm: float
    implant_dv_coordinate_mm: float

@dataclass
class InjectionData:
    """Stores information about a single injection performed during the surgical intervention.

    Multiple InjectionData instances can be used at the same time if the surgery involves multiple injections.
    """

    injection: str
    injection_target: str
    injection_volume_nl: float
    injection_code: str
    injection_ap_coordinate_mm: float
    injection_ml_coordinate_mm: float
    injection_dv_coordinate_mm: float

@dataclass
class DrugData:
    """Stores the information about all medical substances (drugs) administered to the subject before, during, and
    immediately after the surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    lactated_ringers_solution_code: str
    ketoprofen_volume_ml: float
    ketoprofen_code: str
    buprenorphine_volume_ml: float
    buprenorphine_code: str
    dexamethasone_volume_ml: float
    dexamethasone_code: str

@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about the surgical intervention performed on an animal before data acquisition session(s).

    Primarily, this class is used to ensure that each data acquisition session contains a copy of the surgical
    intervention data as a .yaml file. In turn, this improves the experimenter's experience during data analysis by
    allowing quickly referencing the surgical intervention data.
    """

    subject: SubjectData
    procedure: ProcedureData
    drugs: DrugData
    implants: list[ImplantData]
    injections: list[InjectionData]
