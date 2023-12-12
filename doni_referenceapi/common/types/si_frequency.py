import re
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema

# from pydantic.types import ByteSize

HZ_SIZES = {
    "hz": 1,
    "khz": 10**3,
    "mhz": 10**6,
    "ghz": 10**9,
    "thz": 10**12,
    "phz": 10**15,
    "ehz": 10**18,
}

hz_string_re = re.compile(r"^\s*(\d*\.?\d+)\s*(\w+)?", re.IGNORECASE)


class SiFrequency(int):
    """Converts a string representing a Si Frequency with units of Hertz into an integer."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(
        cls, __input_value: Any, _: core_schema.ValidationInfo
    ) -> "SiFrequency":
        # if it's an int already, don't bother parsing
        try:
            return cls(int(__input_value))
        except ValueError:
            pass

        # use regex to extract value and unit
        str_match = hz_string_re.match(str(__input_value))
        if str_match is None:
            raise PydanticCustomError(
                "si_frequency", "could not parse value and unit from frequency string"
            )

        scalar, unit = str_match.groups()
        if unit is None:
            unit = "hz"

        try:
            unit_mult = HZ_SIZES[unit.lower()]
        except KeyError:
            raise PydanticCustomError(
                "byte_size_unit",
                "could not interpret byte unit: {unit}",
                {"unit": unit},
            )

        return cls(int(float(scalar) * unit_mult))
