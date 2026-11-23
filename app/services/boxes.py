from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    name: str
    width: float
    height: float
    length: float
    max_weight: float

    @property
    def size(self) -> tuple[float, float, float]:
        return self.width, self.height, self.length

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length


BOXES = [
    Box("A", 150, 150, 150, 1000),
    Box("B", 100, 200, 100, 1000),
    Box("C", 300, 400, 300, 3000),
]
