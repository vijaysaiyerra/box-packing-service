"""FastAPI application and HTTP endpoint definitions."""

import logging

from fastapi import FastAPI

from .excel_logging import ExcelRequestLoggingMiddleware
from .errors import register_error_handlers
from .schemas import BoxInfo, PackageList, PackingResponse
from .services.box_service import count_boxes, get_boxes as get_box_catalogue


DEBUG = False  # Set to False to show INFO logs only.
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
logging.getLogger().setLevel(log_level)
logger = logging.getLogger(__name__)
app = FastAPI(title="Box Packing Service")
app.add_middleware(ExcelRequestLoggingMiddleware)
register_error_handlers(app)


@app.get("/v1/boxes", response_model=list[BoxInfo])
def get_boxes() -> list[BoxInfo]:
    """Return the available box types."""
    logger.info("Request received: GET /v1/boxes")
    boxes = [BoxInfo.model_validate(box) for box in get_box_catalogue()]
    logger.info("Response sent: GET /v1/boxes returned %d box types", len(boxes))
    logger.debug(
        "Response payload: GET /v1/boxes %s",
        [box.model_dump(by_alias=True) for box in boxes],
    )
    return boxes


@app.post("/v1/packages/box-count", response_model=PackingResponse)
def box_count(packages: PackageList) -> PackingResponse:
    """Calculate how many boxes are needed for the submitted packages."""
    logger.info("Request received: POST /v1/packages/box-count package_count=%d", len(packages))
    logger.debug(
        "Request payload: POST /v1/packages/box-count %s",
        [package.model_dump() for package in packages],
    )
    response = count_boxes(packages)
    logger.info(
        "Response sent: POST /v1/packages/box-count box_count=%d",
        response.boxCount,
    )
    logger.debug("Response payload: POST /v1/packages/box-count %s", response.model_dump())
    return response
