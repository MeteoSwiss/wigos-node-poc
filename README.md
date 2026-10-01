# WIGOS Node PoC

Version: 0.4.0

WIGOS Node PoC is a lightweight browser-based editor for WMDR2 full-record JSON documents. It supports early testing of an OSCAR nextGen / WIGOS “Node”: users can create, upload, review, edit, validate, save, reopen, and download WMDR2 records through a FastAPI application.

The application targets the current **WMDR2 v0.4.0** UML model and JSON schema direction. It is intended to help test the WMDR2 model, schema, and editing workflow, and to generate sample JSON records documenting already known use cases and additional use cases discovered during testing.

## Important limitations

This is a **proof of concept**, not a production OSCAR service.

- Field coverage is intentionally incomplete. Many WMDR2 elements are still available only through the **Edit JSON** dialogs or the full-record JSON editor.
- Field-level validation is not complete. The app performs structural validation and highlights many actionable errors, but it does not yet provide complete domain-aware validation for every WMDR2 field.
- There is no built-in authentication or authorization. A deployed instance should be protected by the hosting platform if access control is required.
- Saved records are stored in the configured Node data directory. For hosted deployments, use a writable and persistent storage location if records need to survive restarts.
- Publication of new or edited records to a future global catalogue is not implemented yet, but can be added once a catalogue publication API becomes available.


## WMDR2 v0.4.0 alignment

The app targets the current `wmdr2-devt` v0.4.0 JSON shape, which builds on wmdr2 1.99.dev1. The most visible structural changes compared with the earlier PoC are:

- `properties.observationSeries` is now `properties.observations`;
- `observations[*].observingConfigurations` is now `observations[*].configurations`;
- each configuration has an `id` and a `time.interval`;
- controlled values are represented as Concept-like objects, for example `{"id": "point", "url": "http://codes.wmo.int/wmdr/Geometry/point"}`;
- facility territories are stored in `properties.territories` with `dates`;
- record links are top-level `links`, not `properties.links`;
- configuration serial numbers are stored as `instrumentSerialNumber`;
- vertical distance is stored as `verticalDistance` with `distances`, `unit`, and `referenceSurface`.

The importer remains tolerant of selected earlier PoC names and converts them to the v0.4.0 names on save/validation. Exported JSON is intended to follow the v0.4.0 shape.

## Current capabilities

### Start or load a record

The application supports three entry points:

- **Start new facility**: create a new minimal WMDR2 facility record from scratch.
- **Choose JSON file**: upload an existing WMDR2 full-record JSON file.
- **Paste record**: paste a complete JSON record into the text area.

Uploaded or newly created records are stored in the Node data directory and appear in the **Saved records** selector, so they can be reopened during later local or hosted testing.

### Facility editing

The **Facility** section is opened by default when a record is loaded. It supports editing of the main facility fields:

- Facility ID / WSI
- Title
- WMO region
- Begin and End date
- Facility type
- Additional titles and WSI identifiers
- Keywords and facility sets
- Description

The Begin and End date controls use native browser date pickers. Values are written as ISO-style `YYYY-MM-DD` dates; empty date controls are stored as `..`.

The Facility form is arranged to keep the most important metadata visible first:

1. Facility identity
2. Begin and End date
3. **Geolocation**
4. **Territory**
5. **Description**
6. collapsed **Additional facility metadata**

Facility sub-sections include:

- **Geolocation**, editing top-level `temporalGeometry` as parallel `coordinates`, `dates`, and `methods` arrays. The current top-level `geometry` is updated automatically from the latest complete geolocation row.
- **Territory**, editing `properties.territories` as dated territory assignments.
- **Facility links**, editing `top-level links` entries such as an `about` URL.
- **Environment**, editing `properties.environment` with date interval, climate zone, surface-cover classification and dependent surface-cover code, Davenport roughness, compound topography/bathymetry, and paired population/perimeter values.

Population values in Environment are stored as paired arrays with `perimeter_km`, for example:

```json
{
  "population": [12345, 67890],
  "perimeter_km": [10, 50]
}
```

The default perimeter radii are 10 km and 50 km. When a record already contains population and perimeter values, the form labels use the perimeters from the record.

Surface-cover classification choices are loaded from `SurfaceCoverClassification`. The surface-cover code dropdown depends on the selected classification scheme and uses the corresponding WMDR surface-cover register, for example `SurfaceCoverIGBP`, `SurfaceCoverGlobCover2009`, `SurfaceCoverLCCS`, `SurfaceCoverPFT`, `SurfaceCoverUMD`, `SurfaceCoverLAIFPAR`, or `SurfaceCoverNPP`. The selected classification scheme is stored together with the selected surface-cover value and URI. Surface roughness is loaded from `SurfaceRoughnessDavenport`. The app does not invent fallback options for these WMDR registers.

Topography/bathymetry is represented as a compound object with four code-list-backed fields on one row:

- `localTopography`
- `relativeElevation`
- `topographicContext`
- `altitudeOrDepth`

Facility owner contacts can be assigned from existing contacts or created as new contacts. If no owner is assigned, the button reads **Add owner contact**. If an owner exists, the button reads **Edit owner contact**.

### Observations editing

The **Observations** section presents one collapsible card per series. The card header shows the series identity and a compact summary, for example:

```text
216-point [domain: atmosphere; geometry: point; variable: 216]
```

Each card has **Edit JSON** and **Delete** actions on the right. The main form focuses on commonly edited fields:

- Row 1: observed property, observed geometry
- Row 2: domain, domain feature, feature name
- Row 3: program affiliations, application areas

Observations cards also include links to related configurations, linked instruments, ObservingProcedures, ReportingProcedures, and assigned contacts. Cross-section navigation collapses the current top-level section, opens the target section, scrolls to the target item, and highlights it.

### Configurations

The **Configurations** section is derived from `observations[*].configurations[*]`. It supports editing the key time-bound observing metadata, including:

- Begin and End date
- observing method
- operating status
- source of observation
- linked instrument
- instrument serial number
- exposure
- vertical distance (distances, unit, reference surface)

Optional nested quantity fields are cleaned up during validation/storage so empty shells such as `verticalDistance: {}` are not introduced by the form.

### Procedures and schedules

The **Procedures and schedules** section is a first, compact representation of `observingProcedures`, `reportingProcedures`, and reusable `properties.schedules`:

- observing procedures are edited per Observations with time interval, strategy, and references to observing schedules;
- reporting procedures are edited per Observations with international exchange, data policy, level of data, unit, timeliness, number of observations in the reporting interval, and references to reporting schedules;
- each procedure card is clearly labelled with the Observations it belongs to;
- schedules are edited once in the reusable schedules table and referenced by UID from observing/reporting procedures;
- selected observing/reporting schedule references are actionable links that jump to the corresponding reusable schedule row;
- reusable schedules show reverse **Used by** links where possible.

The representation of **Reusable schedules** is deliberately bare-bones at this stage. The current table is enough to test references and produce sample JSON, but a more user-friendly schedule editor will be implemented later.

### Instruments

The **Instruments** section supports a reusable instrument catalogue. Instruments can be created from an Observations card and linked through an observing configuration. Instrument cards link back to the configurations and Observations that use them.

### Contacts

The **Contacts** section supports reusable contacts and contact assignments. Facility owner assignments and Observations role assignments are shown as actionable links. Contact cards link back to the Facility or Observations entries where they are used.

### Vocabulary-assisted fields

The backend exposes vocabulary endpoints:

- `GET /api/vocabularies`
- `GET /api/vocabularies/{name}`

The application attempts to fetch selected WMDR-related vocabulary registers and cache them. The frontend uses real `<select>` controls for single-value vocabulary fields and compact chip controls with a `+` selector for multi-value fields and reference lists.

Some core lists retain small static fallbacks for usability. WMDR-specific lists where invented values would be misleading, such as surface cover and topography/bathymetry, should be populated from the relevant WMDR registers or preserve current record values only.

Examples of vocabulary-assisted fields include:

- WMO region
- facility type
- territory
- climate zone, surface-cover classification, surface-cover value, Davenport surface roughness
- topography/bathymetry fields
- observed property
- observed geometry
- domain
- observing method
- operating status
- source of observation
- exposure
- reference surface
- unit
- program affiliations
- application areas
- observing/reporting strategy and reporting metadata

### Validation, saving, and download

The **Validate** button sends the current form state to the backend and reports whether the record is valid according to the PoC validator/schema fragment. Where possible, validation errors are clickable and highlight the corresponding form card, row, or field.

The **Save changes** button opens a save dialog. It suggests the Node data directory and the current filename, and allows both to be edited. Saved files remain accessible through the **Saved records** selector.

The **Download valid WMDR2** link provides a browser download of the current record.

## User-interface behavior

The page is designed to reduce scrolling:

- Top-level sections are collapsible.
- When a record is loaded, only **Facility** is expanded.
- Top-level cards behave as an accordion: opening one main section collapses the others.
- Each top-level section has its **Edit JSON** button in the section header, visible even when the section is collapsed.
- Links between sections collapse the current section and expand the target section.
- Reference lists use chips plus a compact `+` control. The selector appears only when the user chooses to add another value or reference.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn node.app:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

For cloud environments or reverse proxies, bind to all interfaces:

```bash
python -m uvicorn node.app:app --host 0.0.0.0 --port 8888 --root-path "${RENKU_BASE_URL_PATH:-}"
```

## Data storage

By default, saved records are stored under the application data directory. For deployment or testing, the directory can be controlled with:

```bash
export OSCAR_NODE_DATA_DIR=/path/to/records
```

For container or hosted deployments, use a writable location such as `/tmp/oscar-node/records` unless persistent storage is explicitly configured.

## Render.com deployment note

The application can be deployed as a simple Python web service. A typical start command is:

```bash
python -m uvicorn node.app:app --host 0.0.0.0 --port $PORT
```

Because the frontend uses relative `static/...` and API URLs resolved from the loaded script path, it should work behind a hosted base URL or reverse proxy without hard-coded `/api/...` paths.

## Docker and Renku note

The repository may include a Dockerfile for later deployment experiments. Renku and similar platforms usually consume a built container image from a registry, not the Dockerfile directly. The current local development workflow does not require Docker.

## Future catalogue publication

The PoC currently edits, validates, saves, reopens, and downloads WMDR2 JSON records. Publication of new or edited records to the global catalogue can be added once a suitable catalogue publication API becomes available. The current save/download workflow is intended to keep that future integration straightforward.

## Development checks

Run these checks before committing UI/backend changes:

```bash
node --check node/static/app.js
python -m py_compile node/app.py node/schemas.py node/storage.py node/validation.py node/vocabularies.py
pytest -q
```

## Versioning note

The current consolidated PoC version is **0.4.0**. This release updates the Node to the WMDR2-devt v0.4.0 record shape: `properties.observations`, `configurations`, concept-object controlled values, `territories`, root `links`, `instrumentSerialNumber`, and compound `verticalDistance`. Earlier internal drop-in packages used incremental labels such as `0.17.0`, `0.18.0`, `0.19.0`, and `0.20.0` while the PoC was being developed interactively.
