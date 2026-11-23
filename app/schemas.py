"""Pydantic models for validating requests and serializing API responses."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class BoxInfo(BaseModel):
    """Box dimensions and weight limit returned by the box catalogue endpoint."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str
    width: float
    height: float
    length: float
    max_weight: float = Field(alias="maxWeight")


PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]


class PackageInput(BaseModel):
    """A package submitted for box-count calculation."""

    model_config = ConfigDict(extra="forbid")

    id: StrictInt
    width: PositiveNumber
    height: PositiveNumber
    length: PositiveNumber
    weight: PositiveNumber


PackageList = Annotated[list[PackageInput], Field(min_length=1, max_length=1000)]


class PackedBoxResult(BaseModel):
    """The packages and total weight assigned to one box."""

    type: str
    packageIds: list[int]
    totalWeight: float


class PackingResponse(BaseModel):
    """The number of boxes and their package assignments."""

    boxCount: int
    boxes: list[PackedBoxResult]
