from fastapi import FastAPI

from .errors import register_error_handlers
from .schemas import BoxInfo, PackageList, PackingResponse
from .services.box_service import count_boxes, get_boxes as get_box_catalogue


app = FastAPI(title="Box Packing Service")
register_error_handlers(app)


@app.get("/v1/get_boxes", response_model=list[BoxInfo])
def get_boxes() -> list[BoxInfo]:
    return get_box_catalogue()


@app.post("/v1/packages/box-count", response_model=PackingResponse)
def box_count(packages: PackageList) -> PackingResponse:
    return count_boxes(packages)
