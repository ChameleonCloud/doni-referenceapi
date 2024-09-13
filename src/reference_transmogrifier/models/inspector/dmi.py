import re
from typing import List

from pydantic import BaseModel, Field, field_validator


class Bios(BaseModel):
    vendor: str = Field(alias="Vendor")
    version: str = Field(alias="Version")
    release_date: str = Field(alias="Release Date")


class CPU(BaseModel):
    manufacturer: str = Field(alias="Manufacturer")
    version: str = Field(alias="Version")
    current_speed: int = Field(alias="Current Speed")
    core_count: int = Field(alias="Core Count")
    core_enabled: int = Field(alias="Core Enabled")
    thread_count: int = Field(alias="Thread Count")

    @field_validator("current_speed", mode="before")
    @classmethod
    def current_speed_hz(cls, v: str) -> int:
        """Return current speed in unit of hz"""

        hz_sizes = {
            "hz": 1,
            "khz": 10**3,
            "mhz": 10**6,
            "ghz": 10**9,
        }

        speed, unit = v.split(" ")
        multiplier = hz_sizes.get(unit.strip().lower())
        if not multiplier:
            raise ValueError("unit %s not recognized", unit)

        try:
            speed_int = int(speed)
            return speed_int * multiplier
        except ValueError:
            speed_float = float(speed)
            return int(speed_float * multiplier)


class DMI(BaseModel):
    bios: Bios
    cpu: List[CPU]
    memory: dict
