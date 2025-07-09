import xmltodict
import json
import yaml
from pathlib import Path

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