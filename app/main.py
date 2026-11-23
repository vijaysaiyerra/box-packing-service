import logging

from fastapi import FastAPI

from .boxes import BOXES
from .schemas import BoxInfo

logger = logging.getLogger(__name__)
app = FastAPI(title="Box Packing Service")


@app.get("/v1/get_boxes", response_model=list[BoxInfo])
def get_boxes() -> list[BoxInfo]:
    logger.info("get_boxes : Returning available box types")
    return BOXES
