from typing import List, Optional

from pydantic import BaseModel, ByteSize, Field, computed_field


class Bios(BaseModel):
    pass


class CPU(BaseModel):
    handle: str = Field(alias="Handle")
    socket: str = Field(alias="Socket Designation")
    type: str = Field(alias="Type")
    family: str = Field(alias="Family")
    manufacturer: str = Field(alias="Manufacturer")
    id: str = Field(alias="ID")
    signature: str = Field(alias="Signature")
    flags: List[str] = Field(alias="Flags")
    version: str = Field(alias="Version")
    voltage: str = Field(alias="Voltage")
    current_speed: str = Field(alias="Current Speed")
    status: str = Field(alias="Status")
    serial: str = Field(alias="Serial Number")

    @computed_field
    def current_speed_hz(self) -> int:
        """Return current speed in unit of hz"""
        speed, unit = self.current_speed.split(" ")
        speed = int(speed)
        if unit == "MHz":
            return speed * 1000 * 1000


class Memory(BaseModel):
    pass


class DMI(BaseModel):
    bios: Bios
    cpu: List[CPU]
    memory: Memory
