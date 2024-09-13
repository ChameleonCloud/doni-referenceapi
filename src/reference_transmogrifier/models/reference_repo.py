import datetime
from enum import Enum
from typing import Optional

from pydantic import UUID4, BaseModel, field_validator
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated, Self

from reference_transmogrifier.models import blazar, inspector


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

    altera = "Altera"
    amd = "AMD"
    broadcom = "Broadcom"
    cavium = "Cavium"
    dell = "Dell"
    fujitsu = "Fujitsu"
    gigabyte = "Gigabyte"
    intel = "Intel"
    matrox = "Matrox"
    micron = "Micron"
    mellanox = "Mellanox"
    nvidia = "NVIDIA"
    phison = "Phison"
    samsung = "Samsung"
    seagate = "Seagate"
    toshiba = "Toshiba"
    qlogic = "QLogic"
    xilinx = "Xilinx"


def normalize_manufacturer(name: str) -> ManufacturerEnum:
    """Coerce inputs to canonical representation."""
    norm_name = name.strip().lower().split(" ")[0]

    name_mapping = {
        "altera": ManufacturerEnum.altera,
        "broadcom": ManufacturerEnum.broadcom,
        "cavium": ManufacturerEnum.cavium,
        "dell": ManufacturerEnum.dell,
        "fujitsu": ManufacturerEnum.fujitsu,
        "gigabyte": ManufacturerEnum.gigabyte,
        "amd": ManufacturerEnum.amd,
        "intel": ManufacturerEnum.intel,
        "genuineintel": ManufacturerEnum.intel,
        "matrox": ManufacturerEnum.matrox,
        "micron": ManufacturerEnum.micron,
        "mellanox": ManufacturerEnum.mellanox,
        "nvidia": ManufacturerEnum.nvidia,
        "phison": ManufacturerEnum.phison,
        "samsung": ManufacturerEnum.samsung,
        "seagate": ManufacturerEnum.seagate,
        "toshiba": ManufacturerEnum.toshiba,
        "qlogic": ManufacturerEnum.qlogic,
        "xilinx": ManufacturerEnum.xilinx,
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
    release_date: datetime.date
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
    name: ChassisModelEnum
    serial: str

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
    humanized_ram_size: str
    ram_size: int


class Monitoring(BaseModel):
    wattmeter: bool = False


class NetworkAdapter(BaseModel):
    bridged: bool = False
    device: str
    driver: Optional[str] = None
    enabled: bool = False
    interface: Optional[str] = None
    mac: str
    management: bool = False
    model: Optional[str] = None
    mounted: bool = False
    rate: Optional[int] = None
    vendor: Optional[NormalizedManufacturer] = None

    def __lt__(self: Self, other: Self):
        return self.mac < other.mac

    def __le__(self: Self, other: Self):
        return self.mac <= other.mac

    def __gt__(self: Self, other: Self):
        return self.mac > other.mac

    def __ge__(self: Self, other: Self):
        return self.mac >= other.mac


class Placement(BaseModel):
    node: Optional[str] = None
    rack: Optional[str] = None

    @field_validator("node", "rack", mode="before")
    @classmethod
    def _ensure_str(cls, v) -> str:
        if not v:
            return

        if isinstance(v, int):
            return str(v)

        assert isinstance(v, str)
        return v


class Processor(BaseModel):
    cache_l1d: Optional[int] = None
    cache_l1i: Optional[int] = None
    cache_l2: Optional[int] = None
    cache_l3: Optional[int] = None
    clock_speed: int
    instruction_set: str
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
    humanized_size: str
    interface: StorageInterfaceEnum
    media_type: Optional[StorageMediaTypeEnum] = None
    model: str
    serial: Optional[str] = None
    rev: Optional[str] = None
    size: int
    vendor: Optional[NormalizedManufacturer] = None

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


class FPGA(BaseModel):
    board_model: str
    board_vendor: NormalizedManufacturer


class GPU(BaseModel):
    gpu_count: int
    gpu_model: str
    gpu_vendor: NormalizedManufacturer


class Node(BaseModel):
    architecture: Architecture
    bios: Bios
    chassis: Chassis
    gpu: Optional[GPU] = None
    fpga: Optional[FPGA] = None
    infiniband: bool = False
    main_memory: MainMemory
    monitoring: Monitoring
    network_adapters: list[NetworkAdapter]
    node_name: str
    node_type: NodeTypeEnum
    placement: Optional[Placement] = None
    processor: Processor
    storage_devices: list[StorageDevice]
    supported_job_types: SupportedJobTypes
    type: str = "node"
    uid: UUID4

    @classmethod
    def find_gpu_from_pci(cls, data: list[inspector.pci.PciDevice]) -> GPU:
        """Find all PCIe devices of the "display" class type, and exclude matrox integrated GPU."""
        pci_class = inspector.pci.KnownPciClassEnum.display_controller
        matrox_vendor_id = "102b"
        gpus = [
            d
            for d in data
            if d.pci_class_enum == pci_class and d.vendor_id != matrox_vendor_id
        ]
        if not gpus:
            return

        return GPU(
            gpu_count=len(gpus),
            gpu_model=gpus[0].product_name,
            gpu_vendor=gpus[0].vendor_name,
        )

    @classmethod
    def find_fpga_from_pci(cls, data: list[inspector.pci.PciDevice]) -> FPGA:
        pci_class = inspector.pci.KnownPciClassEnum.processing_accelerator
        fpgas = [d for d in data if d.pci_class_enum == pci_class]
        if fpgas:
            return FPGA(
                board_model=fpgas[0].product_name,
                board_vendor=fpgas[0].vendor_name,
            )

    @classmethod
    def find_processor_info(
        cls, dmi_cpus: inspector.dmi.CPU, extra_cpus: inspector.extra_hardware.CPU
    ) -> Processor:
        dmi = dmi_cpus[0]
        extra = extra_cpus.physical_0
        return Processor(
            cache_l1d=extra.l1d_cache,
            cache_l1i=extra.l1i_cache,
            cache_l2=extra.l2_cache,
            cache_l3=extra.l3_cache,
            instruction_set=extra.architecture,
            clock_speed=dmi.current_speed,
            model=dmi.version,
            vendor=dmi.manufacturer,
            version=None,
        )

    @classmethod
    def find_network_adapters(
        cls, extra_nics: list[inspector.extra_hardware.NetworkAdapter]
    ) -> list[NetworkAdapter]:
        output_list = []
        for nic in extra_nics:
            nic_model = NetworkAdapter(
                device=nic.name,
                driver=nic.driver,
                enabled=nic.link,
                interface=nic.interface,
                mac=nic.serial,
                model=nic.product,
                rate=nic.capacity,
                vendor=nic.vendor,
            )
            output_list.append(nic_model)
        output_list.sort()
        return output_list

    @classmethod
    def find_storage_devices(
        cls,
        inventory_disks: list[inspector.inventory.Disk],
        extra_disks: list[inspector.extra_hardware.Disk],
    ) -> list[inspector.extra_hardware.Disk]:
        if len(inventory_disks) != len(extra_disks):
            raise ValueError("different # of disks in inventory and extra data.")

        input_values = {}
        for d in inventory_disks:
            input_values.setdefault(d.wwn, {})
            input_values[d.wwn]["inv"] = d
        for d in extra_disks:
            if d.wwn:
                input_values[d.wwn]["extra"] = d
            elif d.serial:
                matching_inv_wwn = [
                    input_wwn
                    for input_wwn, input_values in input_values.items()
                    if input_values["inv"].serial == d.serial
                ][0]
                input_values[matching_inv_wwn]["extra"] = d

        output_list = []

        for wwn, d in input_values.items():
            inv = d["inv"]
            assert isinstance(inv, inspector.inventory.Disk)
            extra = d["extra"]
            assert isinstance(extra, inspector.extra_hardware.Disk)

            rev = extra.smart_firmware_version
            if not rev:
                rev = extra.rev

            size_bytes = extra.size_gb * 10**9

            disk_model = StorageDevice(
                device=extra.name,
                humanized_size=inv.humanized_size,
                interface=inv.interface,
                media_type=extra.media_type,
                model=extra.model,
                rev=rev,
                serial=extra.serial,
                size=size_bytes,
                vendor=inv.vendor,
            )
            output_list.append(disk_model)
        return output_list

    @classmethod
    def from_inspector_result(
        cls, blazar_data: blazar.Host, idata: inspector.InspectorResult
    ) -> Self:
        """Generate Node object from ironic inspector data and known external data."""

        socket_count = len(idata.dmi.cpu)
        core_count = sum([c.core_count for c in idata.dmi.cpu])
        thread_count = sum([c.thread_count for c in idata.dmi.cpu])
        arch = Architecture(
            platform_type=idata.cpu_arch,
            smp_size=socket_count,
            smt_size=thread_count,
        )
        bios = Bios(
            vendor=idata.dmi.bios.vendor,
            version=idata.dmi.bios.version,
            release_date=idata.dmi.bios.release_date,
        )
        chassis = Chassis(
            name=idata.inventory.system_vendor.product_name,
            manufacturer=idata.inventory.system_vendor.manufacturer,
            serial=idata.inventory.system_vendor.serial_number,
        )
        fpga = cls.find_fpga_from_pci(idata.pci_devices)
        gpu = cls.find_gpu_from_pci(idata.pci_devices)
        main_memory = MainMemory(
            ram_size=idata.extra.memory.total_size_bytes,
            humanized_ram_size=f"{idata.extra.memory.total_size_gib} GiB",
        )
        monitoring = Monitoring(wattmeter=False)

        network_adapters = cls.find_network_adapters(idata.extra.network)
        processor = cls.find_processor_info(idata.dmi.cpu, idata.extra.cpu)
        storage_devices = cls.find_storage_devices(
            idata.inventory.disks, idata.extra.disk
        )
        placement = Placement(
            node=blazar_data.placement_node,
            rack=blazar_data.placement_rack,
        )

        supported_job_types = SupportedJobTypes(
            besteffort=False, deploy=True, virtual="ivt"
        )

        return cls(
            architecture=arch,
            bios=bios,
            chassis=chassis,
            fpga=fpga,
            gpu=gpu,
            main_memory=main_memory,
            monitoring=monitoring,
            network_adapters=network_adapters,
            node_name=blazar_data.node_name,
            node_type=blazar_data.node_type,
            placement=placement,
            processor=processor,
            supported_job_types=supported_job_types,
            storage_devices=storage_devices,
            uid=blazar_data.hypervisor_hostname,
            type="node",
        )
