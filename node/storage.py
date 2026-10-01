from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .validation import normalize_record


class RecordStore:
    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root or os.environ.get("OSCAR_NODE_DATA_DIR", "data/records"))
        self.root.mkdir(parents=True, exist_ok=True)

    def list_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_record(record)
        record_id = normalized.get("id")
        if not isinstance(record_id, str) or not record_id:
            title = normalized.get("properties", {}).get("title", "facility")
            normalized["id"] = f"facility:{slugify(str(title))}"
            record_id = normalized["id"]
        path = self._path(record_id)
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return normalized

    def save_as(self, record: dict[str, Any], filename: str, location: str = "data/records") -> tuple[dict[str, Any], Path]:
        normalized = self.save(record)
        destination = self._save_as_path(filename=filename, location=location)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return normalized, destination

    def get(self, record_id: str) -> dict[str, Any]:
        path = self._path(record_id)
        if not path.exists():
            raise KeyError(record_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def replace_section(self, record_id: str, section: str, value: Any) -> dict[str, Any]:
        record = self.get(record_id)
        props = record.setdefault("properties", {})
        if section == "facility":
            if not isinstance(value, dict):
                raise ValueError("facility section must be an object")
            self._merge_facility(record, value)
        elif section in {"observationSeries", "observations", "instruments", "contacts", "schedules"}:
            if not isinstance(value, list):
                raise ValueError(f"{section} section must be an array")
            canonical = "observations" if section in {"observations", "observationSeries"} else section
            props[canonical] = value
        else:
            raise ValueError(f"Unsupported section: {section}")
        return self.save(record)

    def export_path(self, record_id: str) -> Path:
        path = self._path(record_id)
        if not path.exists():
            raise KeyError(record_id)
        return path

    def _save_as_path(self, filename: str, location: str) -> Path:
        filename = Path(filename).name.strip()
        if not filename:
            raise ValueError("File name must not be empty")
        if not filename.lower().endswith(".json"):
            filename = f"{filename}.json"
        filename = safe_filename(filename.removesuffix(".json")) + ".json"

        normalized_location = location.strip() or "data/records"
        if normalized_location in {".", "./", "data/records", "data/records/"}:
            directory = self.root
        else:
            raw_location = Path(normalized_location)
            if raw_location.is_absolute():
                raise ValueError("Location must be relative to the Node data directory")
            directory = self.root / raw_location

        root = self.root.resolve()
        destination = (directory / filename).resolve()
        if not destination.is_relative_to(root):
            raise ValueError("Location must stay inside the Node data directory")
        return destination

    def _path(self, record_id: str) -> Path:
        return self.root / f"{safe_filename(record_id)}.json"

    @staticmethod
    def _merge_facility(record: dict[str, Any], value: dict[str, Any]) -> None:
        props = record.setdefault("properties", {})
        for key in ("id", "geometry", "temporalGeometry", "time", "conformsTo"):
            if key in value:
                record[key] = value[key]
        if "links" in value:
            record["links"] = value["links"]
        for key in (
            "type",
            "title",
            "description",
            "keywords",
            "facilitySets",
            "facilityType",
            "wmoRegion",
            "timeZone",
            "regionOfOrigin",
            "territories",
            "territory",
            "programAffiliations",
            "environment",
        ):
            if key in value:
                props[key] = value[key]


def safe_filename(record_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", record_id).strip("._") or "record"


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    return slug or "record"
