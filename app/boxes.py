import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Box:
    name: str
    width: float
    height: float
    length: float
    max_weight: float


BOXES = [
    Box("A", 150, 150, 150, 1000),
    Box("B", 100, 200, 100, 1000),
    Box("C", 300, 400, 300, 3000),
]
