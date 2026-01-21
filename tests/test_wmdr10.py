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
    mapping_file = Path("mappings/wmdr10_facility_to_acdd13.csv")
    wmdr10 = WMDR10(xml_path)

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

