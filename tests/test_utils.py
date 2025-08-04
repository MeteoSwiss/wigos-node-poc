import json
from pathlib import Path

import pytest

from utils.utils import (load_mapping_csv,
                         parse_geolocation_to_acdd_fields)


@pytest.mark.parametrize("mapping_file_path", [
    "mappings/wmdr10_facility_to_acdd13.csv",
    # Add additional mappings here as needed
])
def test_load_real_mapping_csv(mapping_file_path):
    """
    Test that the specified mapping CSV can be loaded and contains required columns.
    """
    try:
        mappings = load_mapping_csv(mapping_file_path)
    except FileNotFoundError as e:
        raise AssertionError(
            f"\n❌ Mapping file not found: '{mapping_file_path}'\n"
            f"🔍 Expected under 'mappings/' directory.\n"
            f"💡 Make sure the file exists and is correctly named.\n"
            f"Original error: {e}"
        )

    if mappings == list() or mappings is None:
        raise AssertionError(
            f"\n❌ Mapping file '{mapping_file_path}' is empty.\n"
            f"💡 Add at least one mapping row with valid WMDR1.0 and ACDD13 keys."
        )

    required_keys = ["acdd_attribute", "wmdr10_path", "wmdr10_subpath", "default"]
    missing = [k for k in required_keys if any(k not in row for row in mappings)]
    if missing:
        raise AssertionError(
            f"\n❌ Mapping file '{mapping_file_path}' is missing required columns: {missing}\n"
            f"💡 Ensure the CSV includes these columns exactly: {required_keys}"
        )


def test_parse_geolocation_to_acdd_fields_valid():
    pos = "1.23 4.56 789"
    result = parse_geolocation_to_acdd_fields(pos)
    assert result["geospatial_lat_min"] == pytest.approx(1.229)
    assert result["geospatial_lat_max"] == pytest.approx(1.231)
    assert result["geospatial_lon_min"] == pytest.approx(4.559)
    assert result["geospatial_lon_max"] == pytest.approx(4.561)
    assert result["geospatial_vertical_min"] == 789
    assert result["geospatial_vertical_max"] == 789


def test_parse_geolocation_to_acdd_fields_invalid():
    with pytest.raises(ValueError) as e:
        parse_geolocation_to_acdd_fields("1.0 2.0")  # Missing third value
    assert "Invalid gml:pos value" in str(e.value)




# def test_build_acdd_comment_field():
#     data = {"id": "abc", "note": "xyz"}
#     result = build_acdd_comment_field(data)
#     parsed = json.loads(result)
#     assert parsed["id"] == "abc"
#     assert parsed["note"] == "xyz"
