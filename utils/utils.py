from pathlib import Path
from typing import Any

import polars as pl


def load_mapping_csv(name: str | Path) -> pl.DataFrame:
    """
    Load a mapping CSV file either from the `mappings/` directory (if given as string)
    or from an absolute/relative file path (if given as Path).

    Args:
        name (str | Path): File name (e.g., 'wmdr10_facility_to_acdd13') or a full path.

    Returns:
        pl.DataFrame: Loaded mapping definitions.

    Raises:
        FileNotFoundError: If the mapping file does not exist.
    """
    if isinstance(name, str):
        mapping_path = Path(__file__).parents[1] / "mappings" / f"{name}"
    else:
        mapping_path = name

    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    return pl.read_csv(mapping_path)


def parse_geolocation_to_acdd_fields(pos_value: str) -> dict:
    """
    Parse a gml:pos value into ACDD geospatial bounding box and vertical range fields.

    Args:
        pos_value (str): A space-separated string like "lat lon elev"

    Returns:
        dict: Dictionary with keys: geospatial_lat_min, geospatial_lat_max,
              geospatial_lon_min, geospatial_lon_max,
              geospatial_vertical_min, geospatial_vertical_max

    Raises:
        ValueError: If the position string does not contain exactly 3 numeric components.
    """
    try:
        lat_str, lon_str, elev_str = pos_value.strip().split()
        lat = float(lat_str)
        lon = float(lon_str)
        elev = float(elev_str)
    except Exception as e:
        raise ValueError(f"Invalid gml:pos value '{pos_value}': {e}")

    delta = 0.001
    return {
        "geospatial_lat_min": lat - delta,
        "geospatial_lat_max": lat + delta,
        "geospatial_lon_min": lon - delta,
        "geospatial_lon_max": lon + delta,
        "geospatial_vertical_min": elev,
        "geospatial_vertical_max": elev,
    }


def resolve_path_recursive(obj: Any, path_parts: list[str]) -> Any:
    """
    Recursively resolve a path in a nested structure of dicts and lists.

    Args:
        obj (Any): The current node in the structure.
        path_parts (list[str]): Remaining path elements to resolve.

    Returns:
        Any: The resolved value or None if not found.
    """
    if not path_parts:
        return obj

    current_key = path_parts[0]
    rest = path_parts[1:]

    if isinstance(obj, dict):
        if current_key in obj:
            return resolve_path_recursive(obj[current_key], rest)

    elif isinstance(obj, list):
        for item in obj:
            result = resolve_path_recursive(item, path_parts)
            if result is not None:
                return result

    return None


# def build_acdd_comment_field(comment_data: dict) -> str:
#     """
#     Serialize a dictionary of extra WMDR fields to be embedded in the ACDD comment field.

#     Args:
#         comment_data (dict): Dictionary of unmapped WMDR10 attributes.

#     Returns:
#         str: A compact JSON string for embedding in the 'comment' ACDD field.
#     """
#     import json
#     return json.dumps(comment_data, indent=2, ensure_ascii=False)


# def collect_observed_variables_keywords(xml_dict: dict) -> list[str]:
#     """
#     Extract observed variable hrefs from:
#     WIGOSMetadataRecord/facility/ObservingFacility/observation/ObservingCapability/observation/OM_Observation/observedProperty/href

#     Args:
#         xml_dict (dict): Parsed WMDR10 XML with stripped namespaces.

#     Returns:
#         list[str]: List of observed variable hrefs to use as ACDD keywords.
#     """
#     try:
#         keywords = []

#         facility = (
#             xml_dict.get("WIGOSMetadataRecord", {})
#                     .get("facility", {})
#                     .get("ObservingFacility", {})
#         )

#         observations = facility.get("observation", [])
#         if not isinstance(observations, list):
#             observations = [observations]

#         for obs in observations:
#             capabilities = obs.get("ObservingCapability", [])
#             if not isinstance(capabilities, list):
#                 capabilities = [capabilities]

#             for cap in capabilities:
#                 obs_struct = cap.get("observation", {})
#                 if not isinstance(obs_struct, list):
#                     obs_struct = [obs_struct]

#                 for o in obs_struct:
#                     href = (
#                         o.get("OM_Observation", {})
#                          .get("observedProperty", {})
#                          .get("href")
#                     )
#                     if href:
#                         keywords.append(href)

#         return keywords
#     except Exception as e:
#         raise ValueError(f"Error extracting observed variables from XML: {e}")


