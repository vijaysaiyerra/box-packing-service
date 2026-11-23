from dataclasses import dataclass, field
from itertools import permutations

from .boxes import BOXES, Box

Dimensions = tuple[float, float, float]


@dataclass(frozen=True)
class Package:
    id: int
    width: float
    height: float
    length: float
    weight: float

    @property
    def size(self) -> Dimensions:
        return self.width, self.height, self.length

    @property
    def volume(self) -> float:
        return self.width * self.height * self.length

    @property
    def rotations(self) -> list[Dimensions]:
        return sorted(set(permutations(self.size)))


@dataclass
class PackedBox:
    box: Box
    packages: list[Package] = field(default_factory=list)
    spaces: list[Dimensions] = field(default_factory=list)

    def total_weight(self) -> float:
        return sum(package.weight for package in self.packages)

    def package_ids(self) -> list[int]:
        return sorted(package.id for package in self.packages)


class UnpackablePackagesError(ValueError):
    def __init__(self, packages: list[Package]) -> None:
        self.packages = packages
        super().__init__("Packages do not fit in any available box")


def fits(size: Dimensions, space: Dimensions) -> bool:
    return all(dimension <= available for dimension, available in zip(size, space))


def fits_in_box(package: Package, box: Box) -> bool:
    return package.weight <= box.max_weight and any(
        fits(rotation, box.size) for rotation in package.rotations
    )


def place(packed_box: PackedBox, package: Package) -> bool:
    if packed_box.total_weight() + package.weight > packed_box.box.max_weight:
        return False

    for space in packed_box.spaces:
        for width, height, length in package.rotations:
            if not fits((width, height, length), space):
                continue

            space_width, space_height, space_length = space
            packed_box.spaces.remove(space)
            packed_box.spaces.extend(
                remaining
                for remaining in (
                    (space_width - width, space_height, space_length),
                    (width, space_height - height, space_length),
                    (width, height, space_length - length),
                )
                if min(remaining) > 0
            )
            packed_box.packages.append(package)
            return True

    return False


def pack(packages: list[Package], boxes: list[Box] = BOXES) -> list[PackedBox]:
    unpackable = [
        package
        for package in packages
        if not any(fits_in_box(package, box) for box in boxes)
    ]
    if unpackable:
        raise UnpackablePackagesError(unpackable)

    packages = sorted(packages, key=lambda package: (-package.volume, -package.weight, package.id))

    def attempt(box_order: list[Box]) -> list[PackedBox]:
        result: list[PackedBox] = []
        for package in packages:
            if any(place(packed_box, package) for packed_box in result):
                continue

            for box in box_order:
                packed_box = PackedBox(box, spaces=[box.size])
                if place(packed_box, package):
                    result.append(packed_box)
                    break
            else:
                raise RuntimeError(f"Package {package.id} unexpectedly did not fit")

        return result

    small_first = sorted(boxes, key=lambda box: box.volume)
    results = (attempt(small_first), attempt(small_first[::-1]))
    return min(results, key=lambda result: (len(result), sum(box.box.volume for box in result)))
