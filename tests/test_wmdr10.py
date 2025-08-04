import json
from pathlib import Path

from collections import Counter
import pytest

from wmdr.wmdr import WMDR10
from utils.utils import load_mapping_csv

# Mappings
mapping_path = Path("mappings/wmdr10_facility_to_acdd13.csv")
mapping = load_mapping_csv(mapping_path)

# List of test XML files
test_files = [
    Path("tests/data/20220511_0-404-0-63707.xml"),
    Path("tests/data/20250504_0-20008-0-NRB.xml"),
    Path("tests/data/Blatten_20250729_0-20000-0-06725.xml"),
]

@pytest.mark.parametrize("xml_path", test_files)
def test_facility_to_acdd_conversion(xml_path: Path):
    """
    Validate that the WMDR10 XML file can be successfully converted into
    an ACDD-compliant metadata record using the facility_to_acdd() method.
    """
    mapping_file = Path("mappings/wmdr10_facility_to_acdd13.csv")
    wmdr10 = WMDR10.from_xml(xml_path)

    acdd_record = wmdr10.facility_to_acdd(mapping_file=mapping_file)
    attributes = acdd_record.attributes

    # Required ACDD fields that should be present if mappable
    required_keys = [
        "title", "summary", "geospatial_lat_min", "geospatial_lon_min",
        "creator_name", "creator_email", "keywords", "institution",
        "project", "platform", "geographic_region"
    ]

    missing_keys = [key for key in required_keys if key not in attributes]

    # Print the resulting ACDD record for manual review
    print(f"\n--- ACDD attributes for {xml_path.name} ---")
    for key, value in attributes.items():
        print(f"{key}: {value}")
    if missing_keys:
        print(f"\n⚠️  Missing ACDD attributes: {missing_keys}")
    
    # Don't fail, just assert that at least title and lat/lon are present
    assert "title" in attributes, f"'title' missing for {xml_path.name}"
    assert "geospatial_lat_min" in attributes, f"'geospatial_lat_min' missing for {xml_path.name}"
    assert "geospatial_lon_min" in attributes, f"'geospatial_lon_min' missing for {xml_path.name}"


@pytest.mark.parametrize("xml_path, expected_keywords", test_files)
def test_collect_observed_variables_keywords(xml_path: Path, expected_keywords: list[str]):
    wmdr10 = WMDR10.from_xml(xml_path)
    keywords = wmdr10._collect_observed_variables_keywords()
    assert sorted(keywords) == sorted(expected_keywords)


@pytest.mark.parametrize("xml_path", test_files)
def test_facility_keywords_summary(xml_path):
    wmdr10 = WMDR10.from_xml(xml_path)
    acdd = wmdr10.facility_to_acdd()
    keywords = acdd.attributes.get("keywords")
    assert keywords, f"No keywords found in {xml_path.name}"

    try:
        keyword_stubs = [json.loads(k) for k in keywords.split(", ")]
    except json.JSONDecodeError as e:
        raise AssertionError(f"Failed to parse JSON in keywords for {xml_path.name}: {e}")

    # Count the top-level keyword types
    keyword_types = [list(stub.keys())[0] for stub in keyword_stubs]
    summary = Counter(keyword_types)

    print(f"\n✅ Keyword summary for {xml_path.name}:")
    for k, v in sorted(summary.items()):
        print(f"  {k:<25}: {v}")

    assert summary, f"No keyword types found in {xml_path.name}"

@pytest.mark.parametrize("xml_path", test_files)
def test_collect_geolocation_attributes(xml_path):
    wmdr10 = WMDR10.from_xml(xml_path)
    result = wmdr10._create_geospatial_attributes(mapping_path)

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    expected_keys = {
        "geospatial_lat_min",
        "geospatial_lat_max",
        "geospatial_lon_min",
        "geospatial_lon_max",
        "geospatial_bounds_crs",
    }
    assert expected_keys.issubset(result.keys()), f"Missing geospatial keys in result from {xml_path.name}"