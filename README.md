# WIGOS Node PoC

Version: v0.14.0 v0.14.0

Local proof-of-concept editor for WMDR2 v0.3.x full records.

## What changed in v0.14.0

This release focuses on reducing page clutter and making navigation/save behavior explicit.

- Top-level sections now keep their **Edit JSON** button in the summary row, so it remains available even when the section is collapsed.
- On initial record load, only **Facility** is expanded; all other sections are collapsed.
- Cross-section navigation now opens the target section and collapses the other top-level sections.
- The Facility geolocation editor is now named **Geolocation history** and remains a collapsible table under Facility.
- The ObservationSeries form has been rearranged:
  - row 1: ID and title, shown read-only in the form;
  - row 2: observed property and observed geometry;
  - row 3: domain, domain feature, feature name.
- **Save changes** now opens a save dialog instead of silently saving:
  - it suggests the original uploaded file name when available;
  - it suggests the Node data folder as the location;
  - both folder and file name can be edited before saving.
- Added a backend `/save-as` endpoint that writes a named JSON file under the Node data directory and rejects path traversal.

Note: browsers do not expose the original local upload folder to the web app. The save dialog therefore works with a server-side folder under the Node data directory. The normal browser download flow is still available through **Download valid WMDR2**.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn node.app:app --reload
```

Open <http://127.0.0.1:8000/>.

## Checks

```bash
node --check node/static/app.js
pytest -q
```


## v0.14.0 notes

- ObservationSeries item headers now show `id [title]`, keeping read-only ID/title out of the editable form.
- ObservationSeries item buttons now use the clearer label **Edit JSON**.
- ObservationSeries forms now emphasize: observed property/geometry, observed feature domain fields, program affiliations, and application areas.
- Legacy `applicationArea` is normalized to current `applicationAreas`; legacy `observedDomain` is normalized to `observedFeature`.
