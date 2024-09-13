from typing import Optional

from pydantic import UUID4, BaseModel, Field


class Host(BaseModel):
    hypervisor_hostname: UUID4
    node_name: str
    node_type: str
    placement_rack: Optional[str] = Field(alias="placement.rack", default=None)
    placement_node: Optional[str] = Field(alias="placement.node", default=None)
