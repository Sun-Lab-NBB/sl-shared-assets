from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

@dataclass()
class SubjectData:
    """Stores the ID information of the surgical intervention's subject (animal)."""

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
    """Stores the general information about the surgical intervention."""

    surgery_start_us: int
    surgery_end_us: int
    surgeon: str
    protocol: str
    surgery_notes: str
    post_op_notes: str
    surgery_quality: int = ...

@dataclass
class ImplantData:
    """Stores the information about a single implantation performed during the surgical intervention.

    Multiple ImplantData instances are used at the same time if the surgery involved multiple implants.
    """

    implant: str
    implant_target: str
    implant_code: int
    implant_ap_coordinate_mm: float
    implant_ml_coordinate_mm: float
    implant_dv_coordinate_mm: float

@dataclass
class InjectionData:
    """Stores the information about a single injection performed during surgical intervention.

    Multiple InjectionData instances are used at the same time if the surgery involved multiple injections.
    """

    injection: str
    injection_target: str
    injection_volume_nl: float
    injection_code: int
    injection_ap_coordinate_mm: float
    injection_ml_coordinate_mm: float
    injection_dv_coordinate_mm: float

@dataclass
class DrugData:
    """Stores the information about all drugs administered to the subject before, during, and immediately after the
    surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    lactated_ringers_solution_code: int
    ketoprofen_volume_ml: float
    ketoprofen_code: int
    buprenorphine_volume_ml: float
    buprenorphine_code: int
    dexamethasone_volume_ml: float
    dexamethasone_code: int

@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about a single animal surgical intervention.

    This class aggregates other dataclass instances that store specific data about the surgical procedure. Primarily, it
    is used to save the data as a .yaml file to every session's 'raw_data' directory of each animal used in every lab
    project. This way, the surgery data is always stored alongside the behavior and brain activity data collected
    during the session.
    """

    subject: SubjectData
    procedure: ProcedureData
    drugs: DrugData
    implants: list[ImplantData]
    injections: list[InjectionData]
