import xml.etree.ElementTree as ET
from collections import defaultdict
import json
import yaml
from pathlib import Path

class WMDR10:
    """
    Class to represent and convert WMDR 1.0 metadata records from XML to structured formats.
    Provides methods to load an XML file, parse it into a nested dictionary, and export the
    content to JSON or YAML.

    This version uses Python's built-in xml.etree.ElementTree and preserves all tag names,
    including those with namespaces.
    """

    def __init__(self, data: dict):
        """
        Initialize WMDR10 instance with parsed metadata content.

        Args:
            data (dict): Parsed XML data structure as dictionary.
        """
        self.data = data

    @classmethod
    def from_xml(cls, xml_path: str | Path) -> "WMDR10":
        """
        Parse an XML file and create a WMDR10 instance.

        Args:
            xml_path (str | Path): Path to the WMDR XML file.

        Returns:
            WMDR10: Instance with parsed metadata.
        """
        def etree_to_dict(elem):
            """
            Recursively convert an ElementTree element into a nested dictionary.

            Args:
                elem (xml.etree.ElementTree.Element): Root XML element.

            Returns:
                dict: Dictionary representation of the XML content.
            """
            def inner(e):
                d = {e.tag: {} if e.attrib else None}
                children = list(e)
                if children:
                    dd = defaultdict(list)
                    for child in children:
                        child_dict = inner(child)
                        for k, v in child_dict.items():
                            dd[k].append(v)
                    d[e.tag] = {k: v[0] if len(v) == 1 else v for k, v in dd.items()}
                if e.attrib:
                    d[e.tag].update(('@' + k, v) for k, v in e.attrib.items())
                if e.text and e.text.strip():
                    text = e.text.strip()
                    if children or e.attrib:
                        d[e.tag]['#text'] = text
                    else:
                        d[e.tag] = text
                return d
            return inner(elem)

        xml_path = Path(xml_path)
        tree = ET.parse(xml_path)
        root = tree.getroot()
        data = etree_to_dict(root)
        return cls(data)

    def export(self, format: str = "json") -> str:
        """
        Export the WMDR metadata to the specified format.

        Args:
            format (str): Output format, either 'json' or 'yaml'.

        Returns:
            str: Serialized string in the specified format.

        Raises:
            ValueError: If the requested format is unsupported.
        """
        if format == "json":
            return json.dumps(self.data, indent=2)
        elif format == "yaml":
            return yaml.dump(self.data, allow_unicode=True, sort_keys=False)
        else:
            raise ValueError("Format must be 'json' or 'yaml'")