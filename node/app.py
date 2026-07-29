from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .schemas import WMDR2_RECORD_SCHEMA
from .storage import RecordStore
from .validation import normalize_record, validate_record

app = FastAPI(
    title="OSCAR nextGen Node PoC",
    version="0.15.0",
    description="Local PoC node for upload, review/edit, validation, and export of WMDR2 v0.3.x full records.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = RecordStore()
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/schema")
def schema() -> dict[str, Any]:
    return WMDR2_RECORD_SCHEMA


@app.get("/api/records")
def list_records() -> dict[str, list[str]]:
    return {"records": store.list_ids()}


@app.post("/api/records")
async def create_record(request: Request) -> dict[str, Any]:
    record = await _read_record_payload(request)
    normalized = store.save(record)
    report = validate_record(normalized)
    return {"id": normalized["id"], "record": normalized, "validation": report.as_dict()}


@app.get("/api/records/{record_id}")
def get_record(record_id: str) -> dict[str, Any]:
    try:
        record = store.get(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    return {"id": record["id"], "record": record, "validation": validate_record(record).as_dict()}


@app.put("/api/records/{record_id}")
def replace_record(record_id: str, record: dict[str, Any]) -> dict[str, Any]:
    record = normalize_record(record)
    if not record.get("id"):
        record["id"] = record_id
    saved = store.save(record)
    report = validate_record(saved)
    return {"id": saved["id"], "record": saved, "validation": report.as_dict()}




@app.post("/api/records/{record_id}/save-as")
def save_record_as(record_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    record = payload.get("record")
    if not isinstance(record, dict):
        raise HTTPException(status_code=400, detail="Payload must include a WMDR2 record object")
    filename = payload.get("filename") or f"{record_id}.json"
    location = payload.get("location") or "data/records"
    try:
        saved, path = store.save_as(record, filename=str(filename), location=str(location))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = validate_record(saved)
    return {
        "id": saved["id"],
        "record": saved,
        "validation": report.as_dict(),
        "saved_as": str(path),
        "location": str(location),
        "filename": Path(str(filename)).name,
    }


@app.patch("/api/records/{record_id}/sections/{section}")
def replace_section(record_id: str, section: str, value: Any = Body(...)) -> dict[str, Any]:
    try:
        saved = store.replace_section(record_id, section, value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = validate_record(saved)
    return {"id": saved["id"], "record": saved, "validation": report.as_dict()}


@app.post("/api/records/{record_id}/validate")
def validate_existing_record(record_id: str) -> dict[str, Any]:
    try:
        record = store.get(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    return validate_record(record).as_dict()


@app.get("/api/records/{record_id}/download")
def download_record(record_id: str, allow_invalid: bool = False) -> FileResponse:
    try:
        record = store.get(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    report = validate_record(record)
    if not report.valid and not allow_invalid:
        raise HTTPException(status_code=422, detail=report.as_dict())
    path = store.export_path(record_id)
    filename = f"{record_id.replace(':', '_').replace('/', '_')}.wmdr2.json"
    return FileResponse(path, media_type="application/json", filename=filename)


async def _read_record_payload(request: Request) -> dict[str, Any]:
    import json

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is None or not hasattr(uploaded, "read"):
            raise HTTPException(status_code=400, detail="Multipart request must include a file field")
        raw = await uploaded.read()
        try:
            return normalize_record(json.loads(raw.decode("utf-8")))
        except Exception as exc:  # noqa: BLE001 - return HTTP validation error
            raise HTTPException(status_code=400, detail=f"Invalid JSON upload: {exc}") from exc

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    if isinstance(payload, dict) and "record" in payload and isinstance(payload["record"], dict):
        payload = payload["record"]
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a WMDR2 JSON object")
    return normalize_record(payload)

