from pydantic import BaseModel, ConfigDict, Field


class BoxInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str
    width: float
    height: float
    length: float
    max_weight: float = Field(alias="maxWeight")
