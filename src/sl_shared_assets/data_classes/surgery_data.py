"""This module provides classes to store animal surgery data. This is used to store the data extracted from the Sun lab
surgery log, so that subject surgery data is always kept together with training and experiment data."""

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig


@dataclass()
class SubjectData:
    """Stores the ID information of the surgical intervention's subject (animal)."""

    id: int
    """Stores the unique ID (name) of the subject. Assumes all animals are given a numeric ID, rather than a string 
    name."""
    ear_punch: str
    """Stores the ear tag location of the subject."""
    sex: str
    """Stores the gender of the subject."""
    genotype: str
    """Stores the genotype of the subject."""
    date_of_birth_us: int
    """Stores the date of birth of the subject as the number of microseconds elapsed since UTC epoch onset."""
    weight_g: float
    """Stores the weight of the subject pre-surgery, in grams."""
    cage: int
    """Stores the number of the cage used to house the subject after surgery."""
    location_housed: str
    """Stores the location used to house the subject after the surgery."""
    status: str
    """Stores the current status of the subject (alive / deceased)."""


@dataclass()
class ProcedureData:
    """Stores the general information about the surgical intervention."""

    surgery_start_us: int
    """Stores the date and time when the surgery has started as microseconds elapsed since UTC epoch onset."""
    surgery_end_us: int
    """Stores the date and time when the surgery has ended as microseconds elapsed since UTC epoch onset."""
    surgeon: str
    """Stores the name or ID of the surgeon. If the intervention was carried out by multiple surgeons, all participating
    surgeon names and IDs are stored as part of the same string."""
    protocol: str
    """Stores the experiment protocol number (ID) used during the surgery."""
    surgery_notes: str
    """Stores surgeon's notes taken during the surgery."""
    post_op_notes: str
    """Stores surgeon's notes taken during the post-surgery recovery period."""
    surgery_quality: int = 0
    """Stores the quality of the surgical intervention as a numeric level. 0 indicates unusable (bad) result, 1 
    indicates usable result that is not good enough to be included in a publication, 2 indicates publication-grade 
    result."""


@dataclass
class ImplantData:
    """Stores the information about a single implantation performed during the surgical intervention.

    Multiple ImplantData instances are used at the same time if the surgery involved multiple implants.
    """

    implant: str
    """The descriptive name of the implant."""
    implant_target: str
    """The name of the brain region or cranium section targeted by the implant."""
    implant_code: int
    """The manufacturer code or internal reference code for the implant. This code is used to identify the implant in 
    additional datasheets and lab ordering documents."""
    implant_ap_coordinate_mm: float
    """Stores implant's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    implant_ml_coordinate_mm: float
    """Stores implant's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    implant_dv_coordinate_mm: float
    """Stores implant's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class InjectionData:
    """Stores the information about a single injection performed during surgical intervention.

    Multiple InjectionData instances are used at the same time if the surgery involved multiple injections.
    """

    injection: str
    """The descriptive name of the injection."""
    injection_target: str
    """The name of the brain region targeted by the injection."""
    injection_volume_nl: float
    """The volume of substance, in nanoliters, delivered during the injection."""
    injection_code: int
    """The manufacturer code or internal reference code for the injected substance. This code is used to identify the 
    substance in additional datasheets and lab ordering documents."""
    injection_ap_coordinate_mm: float
    """Stores injection's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    injection_ml_coordinate_mm: float
    """Stores injection's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    injection_dv_coordinate_mm: float
    """Stores injection's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class DrugData:
    """Stores the information about all drugs administered to the subject before, during, and immediately after the
    surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    """Stores the volume of Lactated Ringer's Solution (LRS) administered during surgery, in ml."""
    lactated_ringers_solution_code: int
    """Stores the manufacturer code or internal reference code for Lactated Ringer's Solution (LRS). This code is used 
    to identify the LRS batch in additional datasheets and lab ordering documents."""
    ketoprofen_volume_ml: float
    """Stores the volume of ketoprofen diluted with saline administered during surgery, in ml."""
    ketoprofen_code: int
    """Stores the manufacturer code or internal reference code for ketoprofen. This code is used to identify the 
    ketoprofen batch in additional datasheets and lab ordering documents."""
    buprenorphine_volume_ml: float
    """Stores the volume of buprenorphine diluted with saline administered during surgery, in ml."""
    buprenorphine_code: int
    """Stores the manufacturer code or internal reference code for buprenorphine. This code is used to identify the 
    buprenorphine batch in additional datasheets and lab ordering documents."""
    dexamethasone_volume_ml: float
    """Stores the volume of dexamethasone diluted with saline administered during surgery, in ml."""
    dexamethasone_code: int
    """Stores the manufacturer code or internal reference code for dexamethasone. This code is used to identify the 
    dexamethasone batch in additional datasheets and lab ordering documents."""


@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about a single mouse surgical intervention.

    This class aggregates other dataclass instances that store specific data about the surgical procedure. Primarily, it
    is used to save the data as a .yaml file to every session's raw_data directory of each animal used in every lab
    project. This way, the surgery data is always stored alongside the behavior and brain activity data collected
    during the session.
    """

    subject: SubjectData
    """Stores the ID information about the subject (mouse)."""
    procedure: ProcedureData
    """Stores general data about the surgical intervention."""
    drugs: DrugData
    """Stores the data about the substances subcutaneously injected into the subject before, during and immediately 
    after the surgical intervention."""
    implants: list[ImplantData]
    """Stores the data for all cranial and transcranial implants introduced to the subject during the surgical 
    intervention."""
    injections: list[InjectionData]
    """Stores the data about all substances infused into the brain of the subject during the surgical intervention."""
