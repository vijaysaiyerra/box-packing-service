"""Save API request details and payloads to an Excel workbook."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter
from uuid import uuid4
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import IllegalCharacterError, InvalidFileException
from openpyxl.worksheet.worksheet import Worksheet
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)
WORKBOOK_PATH = Path(__file__).resolve().parent.parent / "pass_fail_api_requests.xlsx"
CELL_CHUNK_SIZE = 32000
workbook_lock = Lock()

BASE_HEADERS = [
    "request_id",
    "timestamp_utc",
    "method",
    "path",
    "status_code",
    "result",
    "duration_ms",
]


class ExcelRequestLoggingMiddleware:
    """Capture each versioned API request and write it to the workbook."""

    def __init__(self, app: ASGIApp) -> None:
        """Store the FastAPI application wrapped by this middleware."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Capture request and response bodies, then append them to Excel."""
        if scope["type"] != "http" or not scope["path"].startswith("/v1/"):
            await self.app(scope, receive, send)
            return

        started = perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        request_messages: list[Message] = []
        request_body = bytearray()
        while True:
            message = await receive()
            request_messages.append(message)
            if message["type"] == "http.request":
                request_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        async def replay_request() -> Message:
            if request_messages:
                return request_messages.pop(0)
            return await receive()

        response_status = 0
        response_body = bytearray()

        async def capture_response(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                duration_ms = (perf_counter() - started) * 1000
                try:
                    await run_in_threadpool(
                        append_request,
                        scope["method"],
                        scope["path"],
                        response_status,
                        timestamp,
                        duration_ms,
                        request_body.decode("utf-8", errors="replace"),
                        response_body.decode("utf-8", errors="replace"),
                    )
                except (
                    OSError,
                    BadZipFile,
                    IllegalCharacterError,
                    InvalidFileException,
                ):
                    logger.exception("Could not save API request to %s", WORKBOOK_PATH)

        await self.app(scope, replay_request, capture_response)


def append_request(
    method: str,
    path: str,
    status_code: int,
    timestamp: str,
    duration_ms: float,
    request_payload: str,
    response_payload: str,
) -> None:
    """Append request details and complete payloads to the Excel workbook."""
    with workbook_lock:
        if WORKBOOK_PATH.exists():
            workbook = load_workbook(WORKBOOK_PATH)
        else:
            workbook = Workbook()

        requests_sheet = _get_requests_sheet(workbook)
        _migrate_legacy_workbook(workbook, requests_sheet)
        request_chunks = _payload_chunks(request_payload)
        response_chunks = _payload_chunks(response_payload)
        payload_part_count = max(len(request_chunks), len(response_chunks))
        _ensure_payload_columns(requests_sheet, payload_part_count)

        request_id = str(uuid4())
        row = [
            request_id,
            timestamp,
            method,
            path,
            status_code,
            "PASS" if 200 <= status_code < 400 else "FAIL",
            round(duration_ms, 2),
        ]
        for part in range(payload_part_count):
            row.extend(
                [
                    request_chunks[part] if part < len(request_chunks) else "",
                    response_chunks[part] if part < len(response_chunks) else "",
                ]
            )
        requests_sheet.append(row)
        for column, value in enumerate(row, start=1):
            if isinstance(value, str):
                requests_sheet.cell(requests_sheet.max_row, column).data_type = "s"
        try:
            workbook.save(WORKBOOK_PATH)
        finally:
            workbook.close()


def _get_requests_sheet(workbook: Workbook) -> Worksheet:
    """Return the single requests sheet, creating it when needed."""
    if "Requests" in workbook.sheetnames:
        return workbook["Requests"]
    if (
        len(workbook.sheetnames) == 1
        and workbook.active.max_row == 1
        and workbook.active["A1"].value is None
    ):
        sheet = workbook.active
        sheet.title = "Requests"
    else:
        sheet = workbook.create_sheet("Requests")
    sheet.append(BASE_HEADERS)
    return sheet


def _migrate_legacy_workbook(workbook: Workbook, sheet: Worksheet) -> None:
    """Combine the older Requests and Payloads sheets into one row per request."""
    if "Payloads" not in workbook.sheetnames:
        _ensure_payload_columns(sheet, 0)
        _remove_empty_default_sheet(workbook, sheet)
        return

    headers = [cell.value for cell in sheet[1]]
    header_indexes = {header: index for index, header in enumerate(headers)}
    legacy_payloads: dict[str, dict[str, list[tuple[int, str]]]] = {}
    payload_sheet = workbook["Payloads"]
    for request_id, direction, chunk_number, payload in payload_sheet.iter_rows(
        min_row=2, values_only=True
    ):
        if request_id is not None and direction in ("request", "response"):
            legacy_payloads.setdefault(request_id, {}).setdefault(direction, []).append(
                (chunk_number, payload or "")
            )

    old_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    combined_rows: list[tuple[list, list[str], list[str]]] = []
    max_parts = 0
    for old_row in old_rows:
        values = list(old_row[: len(headers)])
        request_id = values[header_indexes["request_id"]]
        payloads = legacy_payloads.get(request_id, {})
        request_chunks = _join_legacy_chunks(payloads.get("request", []))
        response_chunks = _join_legacy_chunks(payloads.get("response", []))
        max_parts = max(max_parts, len(request_chunks), len(response_chunks))
        combined_rows.append((values, request_chunks, response_chunks))

    sheet.delete_rows(1, sheet.max_row)
    sheet.append(headers)
    _ensure_payload_columns(sheet, max_parts)
    for values, request_chunks, response_chunks in combined_rows:
        row = values[: len(BASE_HEADERS)]
        for part in range(max_parts):
            row.extend(
                [
                    request_chunks[part] if part < len(request_chunks) else "",
                    response_chunks[part] if part < len(response_chunks) else "",
                ]
            )
        sheet.append(row)
        for column, value in enumerate(row, start=1):
            if isinstance(value, str):
                sheet.cell(sheet.max_row, column).data_type = "s"

    workbook.remove(payload_sheet)
    _remove_empty_default_sheet(workbook, sheet)


def _ensure_payload_columns(sheet: Worksheet, part_count: int) -> None:
    """Add paired request/response payload columns as needed."""
    if sheet.max_row == 1 and sheet["A1"].value is None:
        sheet.append(BASE_HEADERS)
    headers = [cell.value for cell in sheet[1]]
    for part in range(1, part_count + 1):
        for header in (
            f"request_payload_part_{part}",
            f"response_payload_part_{part}",
        ):
            if header not in headers:
                sheet.cell(row=1, column=sheet.max_column + 1, value=header)
                headers.append(header)


def _remove_empty_default_sheet(workbook: Workbook, requests_sheet: Worksheet) -> None:
    """Remove only the blank default sheet created by openpyxl."""
    for sheet in tuple(workbook.worksheets):
        if (
            sheet is not requests_sheet
            and sheet.title == "Sheet"
            and sheet.max_row == 1
            and sheet.max_column == 1
            and sheet["A1"].value is None
        ):
            workbook.remove(sheet)


def _join_legacy_chunks(chunks: list[tuple[int, str]]) -> list[str]:
    """Join old payload chunks and split the result for the one-row format."""
    payload = "".join(chunk for _, chunk in sorted(chunks))
    return _payload_chunks(payload)


def _payload_chunks(payload: str) -> list[str]:
    """Split payload text into Excel-safe cell sizes."""
    return [
        payload[index : index + CELL_CHUNK_SIZE]
        for index in range(0, len(payload), CELL_CHUNK_SIZE)
    ] or [""]


