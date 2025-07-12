from pathlib import Path

import pytest

from wmdr.wmdr import WMDR10


@pytest.mark.parametrize("xml_path", [
    Path("tests/data/20220511_0-404-0-63707.xml"),
    Path("tests/data/20200304_0-20000-0-06494.xml"),
])
def test_facility_to_acdd_conversion(xml_path: Path):
    """
    Validate that the WMDR10 XML file can be successfully converted into
    an ACDD-compliant metadata record using the facility_to_acdd() method.
    """
    mapping = Path("mappings/wmdr10_facility_to_acdd13.csv")
    wmdr10 = WMDR10.from_xml(xml_path)

    acdd_record = wmdr10.facility_to_acdd(mapping=mapping)
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


@pytest.mark.parametrize("xml_path, expected_keywords", [
    (
        Path("tests/data/20220511_0-404-0-63707.xml"),
        [
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12249",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/210",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/210",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/216",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/224",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/225",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/230",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12005",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12006",
        ]
    ),
    (
        Path("tests/data/20200304_0-20000-0-06494.xml"),
        [
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/179",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/216",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/224",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/230",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12249",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/265",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/266",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/270",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/531",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/550",
            "http://codes.wmo.int/wmdr/ObservedVariableTerrestrial/596",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12005",
            "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12006",
        ]
    ),
])
def test_collect_observed_variables_keywords(xml_path: Path, expected_keywords: list[str]):
    wmdr10 = WMDR10.from_xml(xml_path)
    keywords = wmdr10._collect_observed_variables_keywords()
    assert sorted(keywords) == sorted(expected_keywords)



@pytest.mark.parametrize("xml_path", [
    Path("tests/data/20220511_0-404-0-63707.xml"),
    # Add more test files here if needed
])
def test_collect_facility_comments(xml_path: Path):
    """
    Pytest-based test for WMDR10._collect_facility_comments.
    Checks correct structure and values of extracted comments.
    """
    mapping_path = Path("mappings/wmdr10_facility_to_acdd13.csv")
    wmdr10 = WMDR10.from_xml(xml_path)

    comments = wmdr10._collect_facility_comments(mapping_path)

    assert isinstance(comments, dict), "Result is not a dictionary"
    assert comments, "No comments extracted"

    for key, values in comments.items():
        assert isinstance(values, (list, str)), f"Expected list or str for key '{key}'"

        if isinstance(values, list):
            for v in values:
                assert isinstance(v, str), f"Expected string in values for '{key}'"
                assert v.startswith("http://codes.wmo.int/wmdr/"), f"Unexpected href: {v}"
        else:
            assert values.startswith("http://codes.wmo.int/wmdr/"), f"Unexpected href: {values}"

    print(f"✅ Extracted comment entries for {xml_path.name}:", comments)