from node.validation import normalize_record, validate_record


CORE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"


def concept(value: str, register: str | None = None):
    result = {"id": value}
    if register:
        result["url"] = f"http://codes.wmo.int/wmdr/{register}/{value}"
    return result


def minimal_record():
    return {
        "type": "Feature",
        "id": "0-20000-0-TEST",
        "geometry": {"type": "Point", "coordinates": [7.0, 46.0, 500.0]},
        "time": {"interval": ["2024-01-01", ".."], "resolution": "P1D"},
        "conformsTo": [CORE],
        "properties": {
            "type": "facility",
            "title": "Test facility",
            "facilityType": concept("landFixed", "FacilityType"),
            "observations": [
                {
                    "id": "12006-point",
                    "title": "domain: atmosphere; geometry: point; variable: 12006",
                    "observedProperty": concept("12006", "ObservedVariableAtmosphere"),
                    "observedFeature": {"domain": concept("atmosphere", "Domain")},
                    "observedGeometry": concept("point", "Geometry"),
                    "programAffiliations": [
                        {"programAffiliation": concept("GOSGeneral", "ProgramAffiliation")}
                    ],
                    "configurations": [
                        {
                            "id": "12006-point-configuration-1",
                            "time": {"interval": ["2024-01-01", ".."]},
                            "verticalDistance": {
                                "distances": [2.0],
                                "unit": concept("m", "unit"),
                                "referenceSurface": concept("localGround", "ReferenceSurfaceType"),
                            },
                            "observingMethod": concept("266", "ObservingMethodAtmosphere"),
                            "sourceOfObservation": concept("automaticReading", "SourceOfObservation"),
                            "instrument": "instrument:test",
                        }
                    ],
                    "reportingProcedures": [
                        {
                            "internationalExchange": True,
                            "dataPolicy": concept("noLimitation", "DataPolicy"),
                            "uom": concept("K", "unit"),
                            "temporalReportingInterval": "PT1H",
                        }
                    ],
                }
            ],
            "instruments": [
                {"id": "instrument:test", "manufacturer": "Example", "model": "A", "observingMethods": [concept("266", "ObservingMethodAtmosphere")]}
            ],
            "contacts": [
                {"identifier": "contact:owner", "organization": "Example", "emails": [{"value": "x@example.invalid"}], "roles": ["owner"]}
            ],
            "schedules": [],
        },
    }


def test_current_record_shape_is_valid():
    report = validate_record(minimal_record())
    assert report.valid, report.as_dict()
    assert report.errors == []


def test_bare_wsi_id_is_valid():
    record = minimal_record()
    record["id"] = "0-410-0-22184"
    report = validate_record(record)
    assert report.valid, report.as_dict()


def test_observations_require_non_empty_configurations_in_v04():
    record = minimal_record()
    record["properties"]["observations"] = [
        {
            "id": "314-totalcolumn",
            "observedProperty": concept("314"),
            "observedGeometry": concept("totalColumn"),
            "observedFeature": {"domain": concept("atmosphere")},
            "programAffiliations": [{"programAffiliation": concept("AERONET")}],
            "configurations": [],
        }
    ]
    report = validate_record(record)
    assert not report.valid
    assert any("should be non-empty" in error.message for error in report.errors)


def test_legacy_deployments_property_is_rejected_without_normalization():
    record = minimal_record()
    record["properties"]["deployments"] = [{"id": "deployment:test"}]
    report = validate_record(record)
    assert not report.valid
    assert any("False schema" in error.message or "should not be valid" in error.message for error in report.errors)


def test_open_start_in_time_interval_is_valid_with_warning():
    record = minimal_record()
    record["properties"]["observations"][0]["configurations"][0]["time"]["interval"][0] = ".."
    report = validate_record(record)
    assert report.valid, report.as_dict()
    assert any("explicitly unknown/open" in warning.message for warning in report.warnings)


def test_normalize_converts_legacy_v03_names_to_v04_names():
    record = normalize_record({
        "id": "wsi:0-20000-0-X",
        "geometry": {"type": "Point", "coordinates": [7, 46]},
        "properties": {
            "title": "X",
            "facilityType": "landFixed",
            "observationSeries": [
                {
                    "id": "observationSeries:12006",
                    "observedProperty": 12006,
                    "observedFeature": {"domain": "atmosphere"},
                    "observedGeometry": "point",
                    "programAffiliations": ["GOSGeneral"],
                    "observingConfigurations": [
                        {"validFrom": "", "observingMethod": {"nilReason": "unknown"}},
                        {"time": {"interval": ["2024-01-01", ".."]}, "observingMethod": 266},
                    ],
                }
            ],
        },
    })
    obs = record["properties"]["observations"][0]
    configs = obs["configurations"]
    assert record["id"] == "0-20000-0-X"
    assert "observationSeries" not in record["properties"]
    assert obs["id"] == "observation:12006"
    assert configs[0]["time"]["interval"] == ["..", ".."]
    assert configs[0]["id"] == "observation:12006-configuration-1"
    assert configs[1]["time"]["interval"] == ["2024-01-01", ".."]
    assert validate_record(record).valid, validate_record(record).as_dict()


def test_normalize_flattens_obsolete_observing_location_and_vertical_distance():
    record = normalize_record({
        "id": "0-20000-0-X",
        "geometry": {"type": "Point", "coordinates": [7, 46]},
        "properties": {
            "title": "X",
            "facilityType": "landFixed",
            "observationSeries": [
                {
                    "id": "observationSeries:12006",
                    "observedProperty": 12006,
                    "observedGeometry": "point",
                    "observedFeature": {"domain": "atmosphere"},
                    "programAffiliations": ["GOSGeneral"],
                    "observingConfigurations": [
                        {
                            "time": {"interval": ["2024-01-01", ".."]},
                            "observingMethod": 266,
                            "observingLocation": {"referenceSurface": "localGround", "verticalDistanceFromReferenceSurface": {"value": 2, "uom": "m"}},
                        }
                    ],
                }
            ],
        },
    })
    config = record["properties"]["observations"][0]["configurations"][0]
    assert config["verticalDistance"]["referenceSurface"]["id"] == "localGround"
    assert config["verticalDistance"]["distances"] == [2]
    assert "observingLocation" not in config
    assert "referenceSurface" not in config
    assert validate_record(record).valid, validate_record(record).as_dict()


def test_missing_instrument_is_warning_not_schema_error():
    record = minimal_record()
    record["properties"]["observations"][0]["configurations"][0]["instrument"] = "instrument:missing"
    report = validate_record(record)
    assert report.valid
    assert report.warnings
    assert "instrument:missing" in report.warnings[0].message


def test_normalize_adds_poc_shell_defaults_and_current_names():
    record = normalize_record({"id": "wsi:0-20000-0-X", "properties": {"title": "X"}})
    assert record["type"] == "Feature"
    assert record["id"] == "0-20000-0-X"
    assert record["conformsTo"] == [CORE]
    assert record["time"] == {"interval": ["..", ".."], "resolution": "P1D"}
    assert record["properties"]["observations"] == []
    assert "observationSeries" not in record["properties"]


def test_normalize_migrates_old_poc_observation_names_and_deployment_context():
    record = normalize_record(
        {
            "id": "facility:0-20000-0-X",
            "geometry": {"type": "Point", "coordinates": [7, 46]},
            "properties": {
                "title": "X",
                "facilityType": "landFixed",
                "territory": [{"time": {"interval": ["2024-01-01", ".."]}, "territory": "CHE"}],
                "observations": [
                    {
                        "id": "observation:12006",
                        "observedVariable": 12006,
                        "observedGeometry": "point",
                        "observedDomain": {"domain": "atmosphere"},
                        "programAffiliation": ["GOSGeneral"],
                        "deployments": ["deployment:x"],
                    }
                ],
                "deployments": [
                    {
                        "id": "deployment:x",
                        "instrument": "instrument:x",
                        "sourceOfObservation": "automaticReading",
                        "referenceSurface": "localGround",
                        "verticalDistanceFromReferenceSurface": {"value": 2, "uom": "m"},
                    }
                ],
                "instruments": [{"id": "instrument:x"}],
            },
        }
    )
    obs = record["properties"]["observations"][0]
    config = obs["configurations"][0]
    assert "deployments" not in record["properties"]
    assert obs["id"] == "observation:12006"
    assert obs["observedProperty"]["id"] == "12006"
    assert obs["observedFeature"]["domain"]["id"] == "atmosphere"
    assert obs["programAffiliations"][0]["programAffiliation"]["id"] == "GOSGeneral"
    assert config["instrument"] == "instrument:x"
    assert config["sourceOfObservation"]["id"] == "automaticReading"
    assert config["verticalDistance"]["referenceSurface"]["id"] == "localGround"
    assert record["properties"]["territories"][0]["territory"]["id"] == "CHE"
    assert record["properties"]["territories"][0]["dates"] == ["2024-01-01", ".."]


def test_facility_temporal_geometry_history_is_valid():
    record = minimal_record()
    record["id"] = "0-840-11502-KominkoSlade"
    record["geometry"] = {"type": "Point", "coordinates": [-112.106, -79.466, 1801]}
    record["temporalGeometry"] = {
        "type": "MovingPoint",
        "coordinates": [[-112.086, -79.468, 1833], [-112.106, -79.466, 1801]],
        "dates": ["2006-01-13", "2009-01-26"],
        "methods": [[], [{"id": "gps", "url": "http://codes.wmo.int/wmdr/GeopositioningMethod/gps"}]],
    }
    report = validate_record(record)
    assert report.valid, report.as_dict()
    assert not any("temporalGeometry" in warning.path for warning in report.warnings)


def test_temporal_geometry_parallel_array_mismatch_is_warning_only():
    record = minimal_record()
    record["geometry"] = {"type": "Point", "coordinates": [8, 47]}
    record["temporalGeometry"] = {"type": "MovingPoint", "coordinates": [[7, 46], [8, 47]], "dates": ["2024-01-01"], "methods": [[]]}
    report = validate_record(record)
    assert report.valid, report.as_dict()
    assert any("coordinates and dates" in warning.message for warning in report.warnings)
    assert any("methods should be parallel" in warning.message for warning in report.warnings)


def test_normalize_migrates_application_area_to_application_areas():
    record = normalize_record({
        "id": "0-20000-0-X",
        "geometry": {"type": "Point", "coordinates": [7, 46]},
        "properties": {
            "title": "X",
            "facilityType": "landFixed",
            "observationSeries": [
                {
                    "id": "observationSeries:216",
                    "title": "domain: atmosphere; geometry: point; variable: 216",
                    "observedProperty": 216,
                    "observedGeometry": "point",
                    "observedDomain": {"domain": "atmosphere", "domainFeature": "air", "featureName": "near surface"},
                    "programAffiliations": ["GOSGeneral"],
                    "applicationArea": ["weatherForecasting", "climateMonitoring"],
                    "observingConfigurations": [{"time": {"interval": ["2024-01-01", ".."]}}],
                }
            ],
        },
    })
    obs = record["properties"]["observations"][0]
    assert obs["observedFeature"]["domain"]["id"] == "atmosphere"
    assert obs["applicationAreas"][0]["id"] == "weatherForecasting"
    assert "applicationArea" not in obs
    assert validate_record(record).valid, validate_record(record).as_dict()


def test_normalize_prefixes_bare_instrument_ids_and_references():
    record = minimal_record()
    record["properties"]["instruments"] = [{"id": "RS41", "manufacturer": "Vaisala"}]
    record["properties"]["observations"][0]["configurations"][0]["instrument"] = "RS41"
    normalized = normalize_record(record)
    inst = normalized["properties"]["instruments"][0]
    config = normalized["properties"]["observations"][0]["configurations"][0]
    assert inst["id"] == "instrument:RS41"
    assert config["instrument"] == "instrument:RS41"
    report = validate_record(normalized)
    assert report.valid, report.as_dict()
