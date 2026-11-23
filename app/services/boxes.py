"""Box definitions and the catalogue used by the packing service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """A box with its dimensions and maximum supported weight."""

    name: str
    width: float
    height: float
    length: float
    max_weight: float

    @property
    def size(self) -> tuple[float, float, float]:
        """Return the box dimensions as a width-height-length tuple."""
        return self.width, self.height, self.length

    @property
    def volume(self) -> float:
        """Return the box's volume."""
        return self.width * self.height * self.length


BOXES = [
    Box("A", 150, 150, 150, 1000),
    Box("B", 100, 200, 100, 1000),
    Box("C", 300, 400, 300, 3000),
]
