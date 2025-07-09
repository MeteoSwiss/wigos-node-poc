import pytest
from pathlib import Path
from acdd.acdd import ACDD
import json
import yaml

def test_load_templates():
    csv_path = Path(__file__).parent / "data" / "acdd_attributes.csv"
    ACDD.load_templates_from_csv(csv_path)
    assert "title" in ACDD.highly_recommended_template

def test_highly_recommended_variable_template_loaded():
    csv_path = Path(__file__).parent / "data" / "acdd_attributes.csv"
    ACDD.load_templates_from_csv(csv_path)
    assert "standard_name" in ACDD.highly_recommended_variable_template

def test_valid_export(tmp_path):
    acdd = ACDD(attributes={"title": "Example", "Conventions": "ACDD-1.3"})
    path = tmp_path / "metadata"
    out_json = acdd.export(path, fmt="json")
    assert out_json.exists()
    assert json.loads(out_json.read_text())["title"] == "Example"

def test_export_bundle(tmp_path):
    acdd = ACDD(attributes={"title": "Example", "geospatial_lat_min": "-10", "geospatial_lat_max": "10",
                            "geospatial_lon_min": "20", "geospatial_lon_max": "30"})
    bundle_path = tmp_path / "bundle.zip"
    out = acdd.export_bundle(bundle_path)
    assert out.exists()
    assert out.suffix == ".zip"

def test_geojson_export():
    acdd = ACDD(attributes={
        "geospatial_lat_min": "-10",
        "geospatial_lat_max": "10",
        "geospatial_lon_min": "20",
        "geospatial_lon_max": "30"
    })
    geojson = acdd.to_geojson()
    assert geojson["geometry"]["type"] == "Point"
    assert geojson["properties"]["geospatial_lat_min"] == "-10"

def test_from_geojson():
    acdd = ACDD()
    geo = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {"title": "FromGeo"}
    }
    acdd.from_geojson(geo)
    assert acdd.attributes["title"] == "FromGeo"

def test_to_feature_collection():
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"title": "A"}
        }
    ]
    fc = ACDD.to_feature_collection(features)
    assert fc["type"] == "FeatureCollection"
    assert fc["features"][0]["properties"]["title"] == "A"

def test_warns_on_invalid_keys():
    with pytest.warns(UserWarning):
        acdd = ACDD(attributes={"foo": "bar"})
    assert "foo" in acdd._invalid_keys

def test_from_dict():
    acdd = ACDD.from_dict({"title": "FromDict", "Conventions": "ACDD-1.3"})
    assert acdd.attributes["title"] == "FromDict"

def test_from_yaml():
    yaml_str = "title: FromYAML\nConventions: ACDD-1.3"
    acdd = ACDD.from_yaml(yaml_str)
    assert acdd.attributes["title"] == "FromYAML"

def test_from_json():
        json_str = '{ "title": "FromJSON", "Conventions": "ACDD-1.3" }'
        acdd = ACDD.from_json(json_str)
        assert acdd.attributes["title"] == "FromJSON"

def test_from_yaml_roundtrip():
        original = {"title": "YAML Roundtrip", "Conventions": "ACDD-1.3"}
        yaml_str = yaml.dump(original)
        acdd = ACDD.from_yaml(yaml_str)
        assert acdd.attributes == original

def test_from_json_roundtrip():
    original = {"title": "JSON Roundtrip", "Conventions": "ACDD-1.3"}
    json_str = json.dumps(original)
    acdd = ACDD.from_json(json_str)
    assert acdd.attributes == original



def test_from_geojson_roundtrip():
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [10.0, 5.0]},
        "properties": {
            "title": "GeoJSON Roundtrip",
            "geospatial_lat_min": "4.0",
            "geospatial_lat_max": "6.0",
            "geospatial_lon_min": "9.0",
            "geospatial_lon_max": "11.0",
            "Conventions": "ACDD-1.3"
        }
    }
    acdd = ACDD()
    acdd.from_geojson(feature)
    assert acdd.attributes["title"] == "GeoJSON Roundtrip"
    assert acdd.attributes["Conventions"] == "ACDD-1.3"

def test_from_dict_roundtrip():
    original = {"title": "Dict Roundtrip", "Conventions": "ACDD-1.3"}
    acdd = ACDD.from_dict(original)
    assert acdd.attributes == original



def test_to_yaml_output_type():
    acdd = ACDD.from_dict({"title": "YAML Type Test"})
    yaml_str = acdd.to_yaml()
    assert isinstance(yaml_str, str)
    assert "title: YAML Type Test" in yaml_str



def test_to_json_output_type():
    acdd = ACDD.from_dict({"title": "JSON Type Test"})
    json_str = acdd.to_json()
    assert isinstance(json_str, str)
    assert '"title": "JSON Type Test"' in json_str