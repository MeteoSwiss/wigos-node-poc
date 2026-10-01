from pathlib import Path

from fastapi.testclient import TestClient

import node.app as node_app
from node.app import app
from node.storage import RecordStore


def test_upload_and_download_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("OSCAR_NODE_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        record = {
            "type": "Feature",
            "id": "0-20000-0-ROUNDTRIP",
            "conformsTo": ["http://wigos.wmo.int/spec/wmdr/2/conf/core"],
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"type": "facility", "title": "Roundtrip"},
        }
        created = client.post("/api/records", json=record)
        assert created.status_code == 200
        assert created.json()["id"] == "0-20000-0-ROUNDTRIP"
        downloaded = client.get("/api/records/0-20000-0-ROUNDTRIP/download")
        assert downloaded.status_code == 200
        assert downloaded.json()["id"] == "0-20000-0-ROUNDTRIP"


def test_patch_rejects_non_array_section(tmp_path, monkeypatch):
    monkeypatch.setenv("OSCAR_NODE_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        client.post(
            "/api/records",
            json={"id": "0-20000-0-X", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"title": "X"}},
        )
        response = client.patch("/api/records/0-20000-0-X/sections/contacts", json={"bad": "shape"})
        assert response.status_code == 400


def test_patch_observations_legacy_section_name(tmp_path, monkeypatch):
    monkeypatch.setenv("OSCAR_NODE_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        client.post(
            "/api/records",
            json={"id": "0-20000-0-X", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {"title": "X"}},
        )
        response = client.patch(
            "/api/records/0-20000-0-X/sections/observations",
            json=[
                {
                    "id": "observation:1",
                    "observedProperty": 1,
                    "observedFeature": {"domain": "atmosphere"},
                    "configurations": [
                        {
                            "time": {"interval": ["2024-01-01", ".."]},
                            "observingMethod": 1,
                        }
                    ],
                }
            ],
        )
        assert response.status_code == 200
        assert response.json()["record"]["properties"]["observations"][0]["id"] == "observation:1"


def test_save_as_writes_named_file_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(node_app, "store", RecordStore(tmp_path))
    with TestClient(app) as client:
        record = {
            "type": "Feature",
            "id": "0-20000-0-SAVEAS",
            "conformsTo": ["http://wigos.wmo.int/spec/wmdr/2/conf/core"],
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"type": "facility", "title": "Save As"},
        }
        response = client.post(
            "/api/records/0-20000-0-SAVEAS/save-as",
            json={"record": record, "location": "exports", "filename": "custom-name.json"},
        )
        assert response.status_code == 200
        assert (tmp_path / "exports" / "custom-name.json").exists()
        assert response.json()["filename"] == "custom-name.json"


def test_save_as_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(node_app, "store", RecordStore(tmp_path))
    with TestClient(app) as client:
        record = {
            "type": "Feature",
            "id": "0-20000-0-SAVEAS",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"type": "facility", "title": "Save As"},
        }
        response = client.post(
            "/api/records/0-20000-0-SAVEAS/save-as",
            json={"record": record, "location": "../outside", "filename": "custom-name.json"},
        )
        assert response.status_code == 400
