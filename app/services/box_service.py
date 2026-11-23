"""Business operations for listing boxes and packing submitted packages."""

import logging
from collections import Counter

from ..errors import APIError
from ..schemas import PackageList, PackedBoxResult, PackingResponse
from .boxes import BOXES, Box
from .packing import Package, UnpackablePackagesError, pack

logger = logging.getLogger(__name__)


def get_boxes() -> list[Box]:
    """Return the configured box catalogue."""
    logger.info("Returning %d available box types", len(BOXES))
    return BOXES


def count_boxes(packages: PackageList) -> PackingResponse:
    """Validate package IDs, pack packages, and build the API response."""
    logger.info("Checking %d package IDs for duplicates", len(packages))
    ids = Counter(package.id for package in packages)
    duplicates = sorted(package_id for package_id, count in ids.items() if count > 1)
    if duplicates:
        logger.warning("Duplicate package IDs: %s", duplicates)
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
    logger.info("Packing %d packages using the available box types", len(items))
    try:
        packed = pack(items, BOXES)
    except UnpackablePackagesError as error:
        logger.warning(
            "Packages do not fit any available box: %s",
            [package.id for package in error.packages],
        )
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
    logger.info("Packed %d packages into %d boxes", len(items), len(boxes))
    return PackingResponse(boxCount=len(boxes), boxes=boxes)
