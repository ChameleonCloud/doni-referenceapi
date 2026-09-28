from enum import Enum
from typing import Optional

from pydantic import UUID4, BaseModel, Field


class LeaseModeEnum(str, Enum):
    baremetal = "baremetal"
    flavor = "flavor"


class Host(BaseModel):
    hypervisor_hostname: UUID4
    node_name: str
    node_type: str
    placement_rack: Optional[str] = Field(alias="placement.rack", default=None)
    placement_node: Optional[str] = Field(alias="placement.node", default=None)
    lease_mode: LeaseModeEnum = LeaseModeEnum.baremetal
