from graphviz import Digraph
from pathlib import Path

# Create a directed graph with top-to-bottom layout
dot = Digraph("ACDD_UML", format="png")
dot.attr(rankdir="TB", fontsize="12", labelloc="t", label="ACDD UML Class Diagram")

# Define a clean table for the ACDD class
dot.node("ACDD", '''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="lightgray"><B>ACDD</B></TD></TR>
  <TR><TD ALIGN="LEFT">+ attributes: dict</TD><TD></TD></TR>
  <TR><TD ALIGN="LEFT">+ template: pl.DataFrame</TD><TD></TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2"><I>Class Methods</I></TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ from_dict(d: dict)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ from_json_file(path: str)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ from_yaml_file(path: str)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ from_geojson_file(path: str)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2"><I>Instance Methods</I></TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ to_json() → str</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ to_yaml() → str</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ to_geojson() → dict</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ to_feature_collection() → dict</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ export(path: str, format: str)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ export_bundle(path: str)</TD></TR>
  <TR><TD ALIGN="LEFT" COLSPAN="2">+ _validate_keys() → dict</TD></TR>
</TABLE>>''', shape="none")

# Render and save the diagram
output_path = Path("figures") / "acdd_uml_class"
dot.render(filename=str(output_path), format="png", cleanup=True)
