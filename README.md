# WIGOS Node PoC

Version: 0.2.0

WIGOS Node PoC is a browser-based editor for WMDR2 full-record JSON documents. It is intended to support early testing of an WIGOS “Node”: users can create, upload, review, edit, validate, save, reopen, and download WMDR2 records through a lightweight FastAPI application.

The application is a proof of concept. It is useful for testing the editing workflow and the current WMDR2 JSON examples, but it is not yet a production OSCAR service.

## Current capabilities

### Start or load a record

The application supports three entry points:

- **Start new facility**: create a new minimal WMDR2 facility record from scratch.
- **Choose JSON file**: upload an existing WMDR2 full-record JSON file.
- **Paste record**: paste a complete JSON record into the text area.

Uploaded or newly created records are stored in the Node data directory and appear in the **Saved records** selector, so they can be reopened during later local testing.

### Facility editing

The **Facility** section is opened by default when a record is loaded. It supports editing of the main facility fields:

- Facility ID / WSI
- Title
- WMO region
- Begin date
- End date

The Begin and End date controls use native browser date pickers. Values are written as ISO-style `YYYY-MM-DD` dates; empty date controls are stored as `..`.

The Facility section also contains a collapsible **Geolocation history** table for top-level `temporalGeometry`. Each row represents one historical geolocation and edits the parallel `coordinates`, `dates`, and `methods` arrays. The current top-level `geometry` is updated automatically from the latest complete geolocation-history row.

Facility owner contacts can be assigned from existing contacts or created as new contacts. If no owner is assigned, the button reads **Add owner contact**. If an owner exists, the button reads **Edit owner contact**.

### ObservationSeries editing

The **ObservationSeries** section presents one collapsible card per series. The card header shows the series identity and a compact summary, for example:

```text
observationSeries:216 [domain: atmosphere; geometry: point; variable: 216]
```

Each card has **Edit JSON** and **Delete** actions on the right. The main form focuses on commonly edited fields:

- Row 1: observed property, observed geometry
- Row 2: domain, domain feature, feature name
- Row 3: program affiliations, application areas

Program affiliations and application areas are edited as comma-separated lists with helper drop-downs for adding known vocabulary values.

ObservationSeries cards also include links to related observing configurations, linked instruments, and assigned contacts. Cross-section navigation collapses the current top-level section, opens the target section, scrolls to the target item, and highlights it.

### Observing configurations

The **Observing configurations** section is derived from `observationSeries[*].observingConfigurations[*]`. It supports editing the key time-bound observing metadata, including:

- Begin and End dates
- observing method
- operating status
- source of observation
- linked instrument
- serial number
- exposure
- reference surface
- vertical distance from reference surface

Optional nested quantity fields are cleaned up during validation/storage so empty shells such as `verticalDistanceFromReferenceSurface: {}` are not introduced by the form.

### Instruments

The **Instruments** section supports a reusable instrument catalogue. Instruments can be created from an ObservationSeries card and linked through an observing configuration. Instrument cards link back to the observing configurations and ObservationSeries that use them.

### Contacts

The **Contacts** section supports reusable contacts and contact assignments. Facility owner assignments and ObservationSeries role assignments are shown as actionable links. Contact cards link back to the Facility or ObservationSeries entries where they are used.

### Vocabulary-assisted fields

The backend exposes vocabulary endpoints:

- `GET /api/vocabularies`
- `GET /api/vocabularies/{name}`

The application attempts to fetch selected WMDR-related vocabulary registers and cache them. If live fetching fails, it falls back to small static lists. The frontend uses real `<select>` controls for single-value vocabulary fields and “Add from list…” controls for multi-value fields.

Examples of vocabulary-assisted fields include:

- WMO region
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

### Validation, saving, and download

The **Validate** button sends the current form state to the backend and reports whether the record is valid according to the PoC validator/schema fragment.

The **Save changes** button opens a save dialog. It suggests the Node data directory and the current filename, and allows both to be edited. Saved files remain accessible through the **Saved records** selector.

The **Download valid WMDR2** link provides a browser download of the current record.

## User-interface behavior

The page is designed to reduce scrolling:

- Top-level sections are collapsible.
- When a record is loaded, only **Facility** is expanded.
- Each top-level section has its **Edit JSON** button in the section header, visible even when the section is collapsed.
- Links between sections collapse the current section and expand the target section.

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
python -m uvicorn node.app:app --host 0.0.0.0 --port 8888 --root-path "${BASE_URL_PATH:-}"
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

## Docker note

The repository may include a Dockerfile for later deployment experiments. The current local development workflow does not require Docker.

## Development checks

Run these checks before committing UI/backend changes:

```bash
node --check node/static/app.js
python -m py_compile node/app.py node/validation.py node/vocabularies.py
pytest -q
```

## Versioning note

The current consolidated PoC version is **0.2.0**.
