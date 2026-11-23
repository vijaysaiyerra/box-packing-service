from collections import Counter

from ..errors import APIError
from ..schemas import PackageList, PackedBoxResult, PackingResponse
from .boxes import BOXES, Box
from .packing import Package, UnpackablePackagesError, pack


def get_boxes() -> list[Box]:
    return BOXES


def count_boxes(packages: PackageList) -> PackingResponse:
    ids = Counter(package.id for package in packages)
    duplicates = sorted(package_id for package_id, count in ids.items() if count > 1)
    if duplicates:
        raise APIError(
            422,
            "duplicate_package_ids",
            "Package ids must be unique in a request.",
            [
                {"package_id": package_id, "message": "id appears more than once"}
                for package_id in duplicates
            ],
        )

    items = [Package(**package.model_dump()) for package in packages]
    try:
        packed = pack(items, BOXES)
    except UnpackablePackagesError as error:
        raise APIError(
            422,
            "unpackable_packages",
            "Some packages cannot be shipped in any box.",
            [
                {"package_id": package.id, "message": "does not fit any available box"}
                for package in error.packages
            ],
        ) from error

    boxes = [
        PackedBoxResult(
            type=box.box.name,
            packageIds=box.package_ids(),
            totalWeight=box.total_weight(),
        )
        for box in packed
    ]
    return PackingResponse(boxCount=len(boxes), boxes=boxes)
