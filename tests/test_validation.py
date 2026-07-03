from node.validation import normalize_record, validate_record


CORE = "http://wigos.wmo.int/spec/wmdr/2/conf/core"


def minimal_record():
    return {
        "type": "Feature",
        "id": "facility:0-20000-0-TEST",
        "geometry": {"type": "Point", "coordinates": [7.0, 46.0, 500.0]},
        "time": {"interval": ["2024-01-01", ".."]},
        "conformsTo": [CORE],
        "properties": {
            "type": "facility",
            "title": "Test facility",
            "observationSeries": [
                {
                    "id": "observationSeries:12006",
                    "title": "domain: atmosphere; geometry: point; variable: 12006",
                    "observedProperty": 12006,
                    "observedFeature": {"domain": "atmosphere"},
                    "observedGeometry": "point",
                    "programAffiliation": ["GOSGeneral"],
                    "observingConfigurations": [
                        {
                            "date": "2024-01-01",
                            "deployment": "deployment:test",
                            "observingMethod": 266,
                        }
                    ],
                }
            ],
            "deployments": [
                {"id": "deployment:test", "instrument": "instrument:test"}
            ],
            "instruments": [
                {"id": "instrument:test", "manufacturer": "Example", "model": "A", "observingMethods": [266]}
            ],
            "contacts": [
                {"roles": ["owner"], "emails": ["x@example.invalid"], "phones": ["+41 00 000 00 00"]}
            ],
            "reporting": [],
            "schedules": [],
        },
    }


def test_current_record_shape_is_valid():
    report = validate_record(minimal_record())
    assert report.valid, report.as_dict()
    assert report.errors == []


def test_legacy_observations_property_is_rejected_without_normalization():
    record = minimal_record()
    record["properties"]["observations"] = record["properties"].pop("observationSeries")
    report = validate_record(record)
    assert not report.valid
    assert any("should not be valid" in error.message for error in report.errors)


def test_broken_references_are_warnings_not_schema_errors():
    record = minimal_record()
    record["properties"]["observationSeries"][0]["observingConfigurations"][0]["deployment"] = "deployment:missing"
    report = validate_record(record)
    assert report.valid
    assert report.warnings
    assert "deployment:missing" in report.warnings[0].message


def test_normalize_adds_poc_shell_defaults_and_current_names():
    record = normalize_record({"id": "facility:x", "properties": {"title": "X"}})
    assert record["type"] == "Feature"
    assert record["conformsTo"] == [CORE]
    assert record["time"] == {"interval": ["..", ".."]}
    assert record["properties"]["observationSeries"] == []


def test_normalize_migrates_old_poc_observation_names():
    record = normalize_record(
        {
            "id": "facility:x",
            "properties": {
                "title": "X",
                "observations": [
                    {
                        "id": "observation:12006",
                        "observedVariable": 12006,
                        "observedDomain": {"domain": "atmosphere"},
                        "programAffiliations": ["GOSGeneral"],
                        "deployments": ["deployment:x"],
                    }
                ],
            },
        }
    )
    obs = record["properties"]["observationSeries"][0]
    assert obs["id"] == "observationSeries:12006"
    assert obs["observedProperty"] == 12006
    assert obs["observedFeature"] == {"domain": "atmosphere"}
    assert obs["programAffiliation"] == ["GOSGeneral"]
    assert obs["observingConfigurations"][0]["deployment"] == "deployment:x"
