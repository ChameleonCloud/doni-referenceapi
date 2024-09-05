import datetime
from enum import Enum
from typing import List, Optional

from pydantic import UUID4, BaseModel, field_validator
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated


class NodeTypeEnum(str, Enum):
    arm_thunder = "arm_thunder"
    compute_arm64 = "compute_arm64"
    compute_cascadelake = "compute_cascadelake"
    compute_cascadelake_r = "compute_cascadelake_r"
    compute_cascadelake_r_ib = "compute_cascadelake_r_ib"
    compute_gigaio = "compute_gigaio"
    compute_haswell = "compute_haswell"
    compute_haswell_ib = "compute_haswell_ib"
    compute_icelake_r650 = "compute_icelake_r650"
    compute_icelake_r750 = "compute_icelake_r750"
    compute_liqid = "compute_liqid"
    compute_nvdimm = "compute_nvdimm"
    compute_skylake = "compute_skylake"
    compute_zen3 = "compute_zen3"
    fpga = "fpga"
    gpu_a100_nvlink = "gpu_a100_nvlink"
    gpu_a100_pcie = "gpu_a100_pcie"
    gpu_k80 = "gpu_k80"
    gpu_mi100 = "gpu_mi100"
    gpu_m40 = "gpu_m40"
    gpu_p100 = "gpu_p100"
    gpu_p100_nvlink = "gpu_p100_nvlink"
    gpu_p100_v100 = "gpu_p100_v100"
    gpu_rtx_6000 = "gpu_rtx_6000"
    gpu_v100 = "gpu_v100"
    gpu_v100_nvlink = "gpu_v100_nvlink"
    storage = "storage"
    storage_hierarchy = "storage_hierarchy"
    storage_nvme = "storage_nvme"


class InstructionSetEnum(str, Enum):
    x86_64 = "x86_64"
    aarch64 = "aarch64"


class ManufacturerEnum(str, Enum):
    """Canonical representation for each manufacturer."""

    amd = "AMD"
    broadcom = "Broadcom"
    cavium = "Cavium"
    dell = "Dell"
    fujitsu = "Fujitsu"
    gigabyte = "Gigabyte"
    intel = "Intel"
    micron = "Micron"
    mellanox = "Mellanox"
    phison = "Phison"
    samsung = "Samsung"
    seagate = "Seagate"
    toshiba = "Toshiba"
    qlogic = "QLogic"


def normalize_manufacturer(name: str) -> ManufacturerEnum:
    """Coerce inputs to canonical representation."""
    norm_name = name.strip().lower().split(" ")[0]

    name_mapping = {
        "broadcom": ManufacturerEnum.broadcom,
        "cavium": ManufacturerEnum.cavium,
        "dell": ManufacturerEnum.dell,
        "fujitsu": ManufacturerEnum.fujitsu,
        "gigabyte": ManufacturerEnum.gigabyte,
        "amd": ManufacturerEnum.amd,
        "intel": ManufacturerEnum.intel,
        "micron": ManufacturerEnum.micron,
        "mellanox": ManufacturerEnum.mellanox,
        "phison": ManufacturerEnum.phison,
        "samsung": ManufacturerEnum.samsung,
        "seagate": ManufacturerEnum.seagate,
        "toshiba": ManufacturerEnum.toshiba,
        "qlogic": ManufacturerEnum.qlogic,
    }
    try:
        assert norm_name in name_mapping
    except Exception as exc:
        print(f"got {norm_name} from {name}")
        raise (exc)

    return name_mapping[norm_name]


# type alias to make calling it easy
NormalizedManufacturer = Annotated[
    ManufacturerEnum, BeforeValidator(normalize_manufacturer)
]


class Architecture(BaseModel):
    platform_type: InstructionSetEnum
    smp_size: int
    smt_size: int


class Bios(BaseModel):
    release_date: Optional[datetime.date] = None
    vendor: NormalizedManufacturer
    version: str

    @field_validator("release_date", mode="before")
    @classmethod
    def _convert_datestring(cls, v) -> datetime.date:
        if not v:
            return v

        try:
            # 2023-12-12
            return datetime.datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            pass

        # 05/17/2018
        # 005/17/2018
        initial_str = v.strip().lower().lstrip("0")
        try:
            return datetime.datetime.strptime(initial_str, "%m/%d/%Y").date()
        except ValueError:
            pass

        try:
            # Jan 13 2022
            return datetime.datetime.strptime(initial_str, "%b %d %Y").date()
        except ValueError:
            pass

        raise ValueError

    @field_validator("version", mode="before")
    @classmethod
    def _ensure_str(cls, v) -> str:
        if type(v) in [float]:
            return str(int(v))

        assert isinstance(v, str)
        return v


class ChassisModelEnum(str, Enum):
    dell_c4130 = "PowerEdge C4130"
    dell_c4140 = "PowerEdge C4140"
    dell_fc430 = "PowerEdge FC430"
    dell_fx700 = "PowerEdge FX700"
    dell_r630 = "PowerEdge R630"
    dell_r650 = "PowerEdge R650"
    dell_r730 = "PowerEdge R730"
    dell_r740 = "PowerEdge R740"
    dell_r740xd = "PowerEdge R740xd"
    dell_r740xa = "PowerEdge R740xa"
    dell_r750 = "PowerEdge R750"
    dell_r750xa = "PowerEdge R750xa"
    dell_r6525 = "PowerEdge R6525"
    dell_r7525 = "PowerEdge R7525"
    dell_r840 = "PowerEdge R840"
    dell_xe8545 = "PowerEdge XE8545"

    gigabyte_r181_t92 = "R181-T92-00"


class Chassis(BaseModel):
    manufacturer: NormalizedManufacturer
    name: Optional[ChassisModelEnum] = None
    serial: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def _get_model_name(cls, v) -> ChassisModelEnum:
        if not v:
            return None

        model_map = {
            "PowerEdge C4130": ChassisModelEnum.dell_c4130,
            "PowerEdge C4140": ChassisModelEnum.dell_c4140,
            "PowerEdge FC430": ChassisModelEnum.dell_fc430,
            "FX700": ChassisModelEnum.dell_fx700,
            "PowerEdge FX700": ChassisModelEnum.dell_fx700,
            "PowerEdge R630": ChassisModelEnum.dell_r630,
            "PowerEdge R650": ChassisModelEnum.dell_r650,
            "PowerEdge R730": ChassisModelEnum.dell_r730,
            "PowerEdge R740": ChassisModelEnum.dell_r740,
            "PowerEdge R740xd": ChassisModelEnum.dell_r740xd,
            "PowerEdge R740xa": ChassisModelEnum.dell_r740xa,
            "PowerEdge R750": ChassisModelEnum.dell_r750,
            "PowerEdge R750xa": ChassisModelEnum.dell_r750xa,
            "PowerEdge R6525": ChassisModelEnum.dell_r6525,
            "PowerEdge R7525": ChassisModelEnum.dell_r7525,
            "PowerEdge R840": ChassisModelEnum.dell_r840,
            "PowerEdge XE8545": ChassisModelEnum.dell_xe8545,
            "R181-T92-00": ChassisModelEnum.gigabyte_r181_t92,
        }

        model = v.split("(")[0].strip()
        # PowerEdge R630 (SKU=NotP...delName=PowerEdge R630)
        try:
            assert model in model_map
        except ValueError as exc:
            print(repr(model))
            raise (exc)

        return model_map[model]


#
class MainMemory(BaseModel):
    humanized_ram_size: Optional[str] = None
    ram_size: Optional[int]


class Monitoring(BaseModel):
    wattmeter: bool = False


class NetworkAdapter(BaseModel):
    bridged: bool = False
    device: Optional[str] = None
    driver: Optional[str] = None
    enabled: bool = False
    interface: Optional[str] = None
    mac: Optional[str] = None
    management: Optional[bool] = False
    model: Optional[str] = None
    mounted: Optional[bool] = None
    name: Optional[str] = None
    rate: Optional[int] = None
    vendor: Optional[NormalizedManufacturer] = None


class Placement(BaseModel):
    node: Optional[str] = None
    rack: Optional[str] = None

    @field_validator("node", "rack", mode="before")
    @classmethod
    def _ensure_str(cls, v) -> str:
        if isinstance(v, int):
            return str(v)

        assert isinstance(v, str)
        return v


class Processor(BaseModel):
    cache_l1: Optional[int] = None
    cache_l2: Optional[int] = None
    cache_l3: Optional[int] = None
    clock_speed: Optional[int] = None
    instruction_set: Optional[str] = None
    model: str
    vendor: NormalizedManufacturer
    version: Optional[str] = None


class StorageInterfaceEnum(str, Enum):
    sata = "SATA"
    sas = "SAS"
    pcie = "PCIe"


class StorageMediaTypeEnum(str, Enum):
    ssd = "SSD"
    rotational = "Rotational"


class StorageDevice(BaseModel):
    device: str
    humanized_size: Optional[str] = None
    interface: Optional[StorageInterfaceEnum] = None
    media_type: Optional[StorageMediaTypeEnum] = None
    model: str
    rev: Optional[str] = None
    size: Optional[int] = None
    vendor: NormalizedManufacturer = None

    @field_validator("media_type", mode="before")
    @classmethod
    def _coerce_mediatype(cls, v) -> StorageMediaTypeEnum:
        mediatype_map = {
            "HDD": StorageMediaTypeEnum.rotational,
            "Rotational": StorageMediaTypeEnum.rotational,
            "SSD": StorageMediaTypeEnum.ssd,
        }

        assert v in mediatype_map
        return mediatype_map[v]


class SupportedJobTypes(BaseModel):
    besteffort: bool = False
    deploy: bool = True
    virtual: str = "ivt"


class Node(BaseModel):
    architecture: Architecture
    bios: Optional[Bios] = None
    chassis: Optional[Chassis] = None
    infiniband: Optional[bool] = None
    main_memory: Optional[MainMemory] = None
    monitoring: Optional[Monitoring] = None
    network_adapters: List[NetworkAdapter]
    node_name: str
    node_type: NodeTypeEnum
    placement: Optional[Placement] = None
    processor: Processor
    storage_devices: List[StorageDevice]
    supported_job_types: Optional[SupportedJobTypes] = None
    type: str = "node"
    uid: UUID4