"""This module provides dataclasses used to store animal surgery data extracted from the Sun lab surgery log. Typically,
this is done as part of every data acquisition session to ensure that runtime and surgical intervention data is always
kept together and available for analysis."""

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig


@dataclass()
class SubjectData:
    """Stores information about the subject of the surgical intervention (animal)."""

    id: int
    """Stores the unique ID (name) of the subject. Assumes all animals are given a numeric ID, rather than a string 
    name."""
    ear_punch: str
    """Stores the location and the number of ear-tags used to distinguish teh animal from its cage-mates."""
    sex: str
    """Stores the gender of the subject."""
    genotype: str
    """Stores the genotype of the subject."""
    date_of_birth_us: int
    """Stores the date of birth of the subject as the number of microseconds elapsed since UTC epoch onset."""
    weight_g: float
    """Stores the pre-surgery weight of the subject, in grams."""
    cage: int
    """Stores the unique identifier (number) for the cage used to house the subject after surgery."""
    location_housed: str
    """Stores the location (room) used to house the subject."""
    status: str
    """Stores the current status of the subject (alive / deceased)."""


@dataclass()
class ProcedureData:
    """Stores general information about the surgical intervention."""

    surgery_start_us: int
    """Stores the surgery's start date and time as microseconds elapsed since UTC epoch onset."""
    surgery_end_us: int
    """Stores the surgery's stop date and time as microseconds elapsed since UTC epoch onset."""
    surgeon: str
    """Stores the name or ID of the surgeon. If the intervention was carried out by multiple surgeons, the data 
    for all participants is stored as part of the same string."""
    protocol: str
    """Stores the experiment protocol number (ID) used during the surgery."""
    surgery_notes: str
    """Stores surgeon's notes taken during the surgery."""
    post_op_notes: str
    """Stores surgeon's notes taken during the post-surgery recovery period."""
    surgery_quality: int = 0
    """Stores the quality of the surgical intervention as a numeric level. 0 indicates unusable (bad) result, 1 
    indicates usable result that does not meet the publication threshold, 2 indicates publication-grade 
    result, 3 indicates high-tier publication grade result."""


@dataclass
class ImplantData:
    """Stores information about a single implantation procedure performed during the surgical intervention.

    Multiple ImplantData instances can be used at the same time if the surgery involves multiple implants.
    """

    implant: str
    """Stores the descriptive name of the implant."""
    implant_target: str
    """Stores the name of the brain region or cranium section targeted by the implant."""
    implant_code: str
    """Stores the manufacturer code or internal reference code for the implant. This code is used to identify the 
    implant in additional datasheets and lab ordering documents."""
    implant_ap_coordinate_mm: float
    """Stores the implant's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    implant_ml_coordinate_mm: float
    """Stores the implant's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    implant_dv_coordinate_mm: float
    """Stores the implant's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class InjectionData:
    """Stores information about a single injection performed during the surgical intervention.

    Multiple InjectionData instances can be used at the same time if the surgery involves multiple injections.
    """

    injection: str
    """Stores the descriptive name of the injection."""
    injection_target: str
    """Stores the name of the brain region targeted by the injection."""
    injection_volume_nl: float
    """Stores the volume of substance, in nanoliters, delivered during the injection."""
    injection_code: str
    """Stores the manufacturer code or internal reference code for the injected substance. This code is used to 
    identify the substance in additional datasheets and lab ordering documents."""
    injection_ap_coordinate_mm: float
    """Stores the injection's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    injection_ml_coordinate_mm: float
    """Stores the injection's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    injection_dv_coordinate_mm: float
    """Stores the injection's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class DrugData:
    """Stores the information about all medical substances (drugs) administered to the subject before, during, and
    immediately after the surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    """Stores the volume of Lactated Ringer's Solution (LRS) administered during surgery, in ml."""
    lactated_ringers_solution_code: str
    """Stores the manufacturer code or internal reference code for Lactated Ringer's Solution (LRS). This code is used 
    to identify the LRS batch in additional datasheets and lab ordering documents."""
    ketoprofen_volume_ml: float
    """Stores the volume of ketoprofen diluted with saline administered during surgery, in ml."""
    ketoprofen_code: str
    """Stores the manufacturer code or internal reference code for ketoprofen. This code is used to identify the 
    ketoprofen batch in additional datasheets and lab ordering documents."""
    buprenorphine_volume_ml: float
    """Stores the volume of buprenorphine diluted with saline administered during surgery, in ml."""
    buprenorphine_code: str
    """Stores the manufacturer code or internal reference code for buprenorphine. This code is used to identify the 
    buprenorphine batch in additional datasheets and lab ordering documents."""
    dexamethasone_volume_ml: float
    """Stores the volume of dexamethasone diluted with saline administered during surgery, in ml."""
    dexamethasone_code: str
    """Stores the manufacturer code or internal reference code for dexamethasone. This code is used to identify the 
    dexamethasone batch in additional datasheets and lab ordering documents."""


@dataclass
class SurgeryData(YamlConfig):
    """Stores the data about the surgical intervention performed on an animal before data acquisition session(s).

    Primarily, this class is used to ensure that each data acquisition session contains a copy of the surgical
    intervention data as a .yaml file. In turn, this improves the experimenter's experience during data analysis by
    allowing quickly referencing the surgical intervention data.
    """

    subject: SubjectData
    """Stores information about the subject (mouse)."""
    procedure: ProcedureData
    """Stores general information about the surgical intervention."""
    drugs: DrugData
    """Stores information about the medical substances administered to the subject before, during, and immediately 
    after the surgical intervention."""
    implants: list[ImplantData]
    """Stores information about cranial and transcranial implants introduced to the subject as part of the surgical 
    intervention."""
    injections: list[InjectionData]
    """Stores information about substances infused into the brain of the subject as part the surgical intervention."""
