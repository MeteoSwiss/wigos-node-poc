from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union

import xmltodict
import yaml

from acdd.acdd import ACDD
from utils.utils import (load_mapping_csv,
                         parse_geolocation_to_acdd_fields, 
                         resolve_path_recursive
                         )


@dataclass
class WMDR20:
    """
    WMDR 2.0 metadata wrapper to manage ACDD-based records with hierarchical structure.

    - `record`: an ACDD-compliant metadata record
    - `parent_id`: reference to parent metadata record
    - `children`: list of subordinate records or file paths
    """
    record: ACDD
    parent_id: Optional[str] = None
    children: List[Union[str, 'WMDR20']] = field(default_factory=list)

    def add_child(self, child: Union[str, 'WMDR20']) -> None:
        """Attach a subordinate record or reference."""
        self.children.append(child)

    def set_parent(self, parent_id: str) -> None:
        """Link to a parent record by ID or path."""
        self.parent_id = parent_id

    def to_dict(self) -> dict:
        """Convert to nested dictionary representation."""
        return {
            "record": self.record.to_dict(),
            "parent_id": self.parent_id,
            "children": [
                c if isinstance(c, str) else c.to_dict() for c in self.children
            ]
        }

    def to_json(self) -> str:
        """Export full hierarchy as JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_yaml(self) -> str:
        """Export full hierarchy as YAML string."""
        return yaml.dump(self.to_dict(), sort_keys=False)

    @classmethod
    def from_dict(cls, d: dict) -> 'WMDR20':
        """Reconstruct hierarchy from dictionary."""
        children = d.get("children", [])
        parsed_children = [
            c if isinstance(c, str) else WMDR20.from_dict(c)
            for c in children
        ]
        return cls(
            record=ACDD.from_dict(d["record"]),
            parent_id=d.get("parent_id"),
            children=parsed_children
        )

    @classmethod
    def from_json_file(cls, path: str) -> 'WMDR20':
        """Load a WMDR20 record from a JSON file."""
        with open(path) as f:
            d = json.load(f)
        return cls.from_dict(d)

    @classmethod
    def from_yaml_file(cls, path: str) -> 'WMDR20':
        """Load a WMDR20 record from a YAML file."""
        with open(path) as f:
            d = yaml.safe_load(f)
        return cls.from_dict(d)

    @staticmethod
    def parse_wmdr10_xml(xml_path: Union[str, Path]) -> dict:
        """
        Parse a WMDR 1.0 XML file into a dictionary using xmltodict.

        Args:
            xml_path (Union[str, Path]): Path to the WMDR XML file.

        Returns:
            dict: Parsed WMDR XML content.
        """
        with open(xml_path, "rb") as f:
            parsed = xmltodict.parse(f, process_namespaces=True)
        return parsed

    @staticmethod
    def strip_ns_keys(d: dict) -> dict:
        """
        Recursively remove XML namespaces from dictionary keys.

        Args:
            d (dict): Input dictionary.

        Returns:
            dict: Dictionary with stripped keys.
        """
        if isinstance(d, dict):
            return {k.split(":")[-1]: WMDR20.strip_ns_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [WMDR20.strip_ns_keys(i) for i in d]
        else:
            return d

    @classmethod
    def from_wmdr10(cls, xml_path: Union[str, Path]) -> 'WMDR20':
        """
        Convert WMDR 1.0 XML to WMDR20 instance with ACDD record.

        Args:
            xml_path (Union[str, Path]): Path to the WMDR 1.0 XML file.

        Returns:
            WMDR20: WMDR20 instance containing mapped ACDD metadata.
        """
        raw_data = cls.parse_wmdr10_xml(xml_path)
        data = cls.strip_ns_keys(raw_data)
        rec = data.get("WIGOSMetadataRecord", {})
        facility = rec.get("facility", {})

        acdd_attrs = {
            "title": facility.get("name"),
            "summary": facility.get("description"),
            "geospatial_lat_min": facility.get("geoLocation", {}).get("latitude"),
            "geospatial_lat_max": facility.get("geoLocation", {}).get("latitude"),
            "geospatial_lon_min": facility.get("geoLocation", {}).get("longitude"),
            "geospatial_lon_max": facility.get("geoLocation", {}).get("longitude"),
        }

        # Remove None values and warn
        acdd_clean = {}
        for k, v in acdd_attrs.items():
            if v is not None:
                acdd_clean[k] = v
            else:
                warnings.warn(f"Missing value for '{k}' in WMDR10 -> ACDD mapping")

        acdd = ACDD.from_dict(acdd_clean)
        return cls(record=acdd)


class WMDR10:
    """
    WMDR10 provides a parser and serializer for WMO WMDR 1.0 metadata records.

    This implementation uses the `xmltodict` package to convert XML to a dictionary.
    The metadata can then be exported to JSON and YAML formats.
    The facility section of WMDR1.0 records can be converted to ACDD1.3 objects.
    The observations section of a WMDR1.0 record can be converted to ACDD1.3 objects.
    
    Attributes:
        data (dict): Parsed metadata as a nested dictionary.
    """

    def __init__(self, data: dict):
        """
        Initialize a WMDR10 instance from a parsed dictionary.

        Args:
            data (dict): Dictionary representation of the WMDR XML document.
        """
        self.data = data

    @classmethod
    def from_xml(cls, xml_path: str | Path) -> "WMDR10":
        """
        Parse a WMDR 1.0 XML metadata file into a WMDR10 object.

        Args:
            xml_path (str | Path): Path to the XML file containing WMDR metadata.

        Returns:
            WMDR10: An instance containing the parsed metadata.
        """
        xml_path = Path(xml_path)
        with xml_path.open("r", encoding="utf-8") as f:
            data = xmltodict.parse(f.read(), process_namespaces=True)
        return cls(data)

    def strip_namespaces(self, delimiter: str = ":") -> dict:
        """
        Recursively strip namespace prefixes from all keys in the metadata.

        Args:
            delimiter (str): Character used to split namespace prefix. Defaults to ':'.

        Returns:
            dict: Metadata with stripped keys.
        """
        def _strip(d):
            if isinstance(d, dict):
                return {
                    k.split(delimiter)[-1] if delimiter in k else k: _strip(v)
                    for k, v in d.items()
                }
            elif isinstance(d, list):
                return [_strip(i) for i in d]
            else:
                return d

        return _strip(self.data)

    def to_json(self) -> str:
        """
        Convert the WMDR metadata to a JSON-formatted string.

        Returns:
            str: JSON string representation of the metadata.
        """
        return json.dumps(self.data, indent=2)

    def to_yaml(self) -> str:
        """
        Convert the WMDR metadata to a YAML-formatted string.

        Returns:
            str: YAML string representation of the metadata.
        """
        return yaml.dump(self.data, allow_unicode=True, sort_keys=False)

    def export(self, base_path: str | Path, formats: list[str] = ["json", "yaml"]) -> list[Path]:
        """
        Export the WMDR metadata to one or more file formats (json, yaml).

        Args:
            base_path (str | Path): Base output path without extension.
            formats (list[str]): List of formats to export ('json', 'yaml').

        Returns:
            list[Path]: Paths to the generated files.

        Raises:
            ValueError: If unsupported format is requested.
        """
        base_path = Path(base_path)
        exported_files = []

        for fmt in formats:
            if fmt == "json":
                path = base_path.with_suffix(".json")
                path.write_text(self.to_json(), encoding="utf-8")
            elif fmt == "yaml":
                path = base_path.with_suffix(".yaml")
                path.write_text(self.to_yaml(), encoding="utf-8")
            else:
                raise ValueError(f"Unsupported format: {fmt}")
            exported_files.append(path)

        return exported_files

    def facility_to_acdd(self, mapping: str | Path = "wmdr10_facility_to_acdd13.csv") -> ACDD:
        """
        Extract the ObservingFacility part from a WMDR10 record and map it to an ACDD object.

        Args:
            mapping (str | Path): Mapping file name or path to CSV.

        Returns:
            ACDD: ACDD metadata record representing the facility.
        """
        raw = self.strip_namespaces()
        attributes = self._map_wmdr10_to_acdd(raw, mapping)
        return ACDD(attributes=attributes)

    # def observations_to_acdd(self, mapping: str | Path = "wmdr10_facility_to_acdd13") -> list[ACDD]:
    #     """
    #     Convert the observation metadata in WMDR10 to a list of ACDD records.

    #     Args:
    #         mapping (str | Path): Mapping file name or path to CSV.

    #     Returns:
    #         list[ACDD]: One ACDD record per observed variable (derived from ObservingCapability).
    #     """
    #     stripped = self.strip_namespaces()
    #     caps = (
    #         stripped.get("WIGOSMetadataRecord", {})
    #         .get("facility", {})
    #         .get("ObservingFacility", {})
    #         .get("observingCapability", [])
    #     )
    #     if not isinstance(caps, list):
    #         caps = [caps]

    #     acdd_records = []
    #     for cap in caps:
    #         raw = cap.get("ObservingCapability", {})
    #         attributes = self._map_wmdr10_to_acdd(raw, mapping)
    #         acdd_records.append(ACDD(attributes=attributes))

    #     return acdd_records

    def _map_wmdr10_to_acdd(self, raw: dict[str, Any], mapping: str | Path) -> dict[str, Any]:
        """
        Apply a mapping from WMDR10 attributes to ACDD attributes.

        Args:
            raw (dict): Dictionary of extracted WMDR10 values.
            mapping_file (str | Path): Path to mapping CSV file.

        Returns:
            dict[str, Any]: Dictionary of ACDD attributes.
        """
        df = load_mapping_csv(mapping)
        result: dict[str, Any] = {}
        unmapped: dict[str, Any] = {}

        for row in df.iter_rows(named=True):
            acdd_key = row["acdd_attribute"]
            wmdr_path = row["wmdr10_path"]
            default = row["default"] if row["default"] != "" else None

            # Navigate WMDR10 path if provided
            if wmdr_path:
                parts = wmdr_path.split("/")
                val = resolve_path_recursive(raw, parts)

                if val is None:
                    if default:
                        result[acdd_key] = default
                    else:
                        unmapped[acdd_key] = f"Missing: {wmdr_path}"
                else:
                    # Special case for gml:pos
                    if wmdr_path.endswith("pos") and isinstance(val, str):
                        result.update(parse_geolocation_to_acdd_fields(val))
                    else:
                        result[acdd_key] = val

            elif default:
                result[acdd_key] = default

        # Add keywords derived from observed variables
        result["keywords"] = self._collect_observed_variables_keywords()
        # if keywords:
        #     result["keywords"] = ", ".join(keywords)

        # Add comments derived from known mapping rows
        comment_dict = self._collect_facility_comments(mapping)
        result["comment"] = self._collect_facility_comments(mapping)
        # if comment_dict:
        #     result["comments"] = json.dumps(comment_dict, indent=2)

            # Add all unmapped entries to comment
        if unmapped:
            result["unmapped"] = self._collect_unmapped_fields(unmapped)

        return result

    def _collect_facility_comments(self, mapping_file: str | Path) -> dict[str, str | list[str]]:
        """
        Extract all WMDR10 values designated for inclusion in the ACDD 'comments' field.

        This looks for rows in the mapping CSV where:
        - `acdd_attribute` == "comments"
        - `wmdr10_path` ends with 'href'

        For each such path:
        - The second-to-last path segment becomes the comment key
        - The resolved value is added to the result

        Returns:
            dict[str, str | list[str]]: Dictionary of clean comment entries.
        """
        df = load_mapping_csv(mapping_file)
        raw = self.strip_namespaces()

        comments: dict[str, list[str]] = {}

        for row in df.iter_rows(named=True):
            acdd_key = row["acdd_attribute"]
            wmdr_path = row["wmdr10_path"]

            if acdd_key == "comment" and wmdr_path.endswith("href"):
                path_parts = wmdr_path.split("/")
                if len(path_parts) < 2:
                    continue  # malformed

                comment_key = path_parts[-2]
                val = resolve_path_recursive(raw, path_parts)

                if val:
                    if isinstance(val, str):
                        comments.setdefault(comment_key, []).append(val)
                    elif isinstance(val, list):
                        comments.setdefault(comment_key, []).extend(
                            v for v in val if isinstance(v, str)
                        )
                    elif isinstance(val, dict):
                        href_val = val.get("href") or val.get("@xlink:href") or val.get("@href")
                        if href_val:
                            comments.setdefault(comment_key, []).append(href_val)

        # Flatten single-element lists to just the string
        for key, values in comments.items():
            if isinstance(values, list) and len(values) == 1:
                comments[key] = values[0]

        return comments

    def _collect_observed_variables_keywords(self) -> list[str]:
        """
        Extract observed variable hrefs from:
        WIGOSMetadataRecord/facility/ObservingFacility/observation/ObservingCapability/observation/OM_Observation/observedProperty/href

        Returns:
            list[str]: List of observed variable hrefs to use as ACDD keywords.
        """
        try:
            xml_dict = self.strip_namespaces()
            keywords = []

            facility = (
                xml_dict.get("WIGOSMetadataRecord", {})
                        .get("facility", {})
                        .get("ObservingFacility", {})
            )

            observations = facility.get("observation", [])
            if not isinstance(observations, list):
                observations = [observations]

            for obs in observations:
                capabilities = obs.get("ObservingCapability", [])
                if not isinstance(capabilities, list):
                    capabilities = [capabilities]

                for cap in capabilities:
                    obs_struct = cap.get("observation", {})
                    if not isinstance(obs_struct, list):
                        obs_struct = [obs_struct]

                    for o in obs_struct:
                        href = (
                            o.get("OM_Observation", {})
                             .get("observedProperty", {})
                             .get("href")
                        )
                        if href:
                            keywords.append(href)

            return keywords
        except Exception as e:
            raise ValueError(f"Error extracting observed variables from XML: {e}")

    def _collect_unmapped_fields(self, comment_data: dict[str, str]) -> str:
        """
        Build a JSON-encoded comment field containing information on missing or fallback values.

        Args:
            comment_data (dict): Dictionary mapping ACDD attribute names to notes or fallback info.

        Returns:
            str: JSON string to be used as ACDD 'comment' attribute.
        """
        try:
            return json.dumps(comment_data, indent=2, sort_keys=True, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Failed to encode ACDD comment data: {e}")
