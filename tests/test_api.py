import tempfile

from fastapi.testclient import TestClient as FastAPITestClient

from node import app as app_module
from node.storage import RecordStore


CORE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"


def test_upload_validate_download_roundtrip(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(app_module, "store", RecordStore(tmp))
        client = FastAPITestClient(app_module.app)
        record = {
            "type": "Feature",
            "id": "facility:roundtrip",
            "geometry": {"type": "Point", "coordinates": [7.0, 46.0]},
            "time": {"interval": ["..", ".."]},
            "conformsTo": [CORE],
            "properties": {
                "type": "facility",
                "title": "Roundtrip",
                "observationSeries": [],
                "deployments": [],
                "instruments": [],
                "contacts": [],
                "reporting": [],
                "schedules": [],
            },
        }

        created = client.post("/api/records", json=record)
        assert created.status_code == 200
        assert created.json()["validation"]["valid"] is True

        downloaded = client.get("/api/records/facility:roundtrip/download")
        assert downloaded.status_code == 200
        assert downloaded.json()["id"] == "facility:roundtrip"


def test_section_patch_rejects_non_array(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(app_module, "store", RecordStore(tmp))
        client = FastAPITestClient(app_module.app)
        client.post(
            "/api/records",
            json={"id": "facility:x", "geometry": None, "properties": {"title": "X"}},
        )
        response = client.patch("/api/records/facility:x/sections/contacts", json={"bad": "shape"})
        assert response.status_code == 400


def test_legacy_observations_section_alias_is_saved_as_observation_series(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(app_module, "store", RecordStore(tmp))
        client = FastAPITestClient(app_module.app)
        client.post(
            "/api/records",
            json={"id": "facility:x", "geometry": None, "properties": {"title": "X"}},
        )
        response = client.patch(
            "/api/records/facility:x/sections/observations",
            json=[{"id": "observationSeries:1", "observedProperty": 1}],
        )
        assert response.status_code == 200
        assert "observationSeries" in response.json()["record"]["properties"]
        assert "observations" not in response.json()["record"]["properties"]
