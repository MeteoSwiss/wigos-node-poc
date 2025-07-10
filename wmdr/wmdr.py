from dataclasses import dataclass, field
from typing import Optional, List, Union
import json
import yaml
from acdd import ACDD
import xmltodict
from pathlib import Path
import warnings

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