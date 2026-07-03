# OSCAR nextGen Node PoC

This is a small, local proof of concept for an OSCAR nextGen **Node**. It lets a user upload or paste a WMDR2 full record, review and edit the core parts in a browser, save the changed record locally, validate it structurally, and download the resulting WMDR2 JSON record.

The implementation is intentionally modest: one FastAPI backend, one vanilla HTML/CSS/JavaScript UI, JSON-file storage, and a local WMDR2 core schema fragment. That keeps the first development phase easy to run, inspect, and replace later with a stronger backend, workflow engine, identity integration, or an OGC API publication layer.

## What this PoC covers

- Submit a WMDR2 full record as JSON file upload or pasted JSON.
- Review and edit:
  - Facility metadata, root geometry and lifecycle interval.
  - `properties.observationSeries`.
  - `properties.deployments`, as a separate section, because deployments describe instruments in use and are referenced by ObservationSeries.
  - `properties.instruments`, as a separate section, with manufacturer/model and observing-method capability where known.
  - `properties.contacts`, accepting the current simple e-mail and phone string arrays.
- Use collapsible sections for normal editing.
- Navigate relationships with actionable cross-links: ObservationSeries → deployments, deployments → referring ObservationSeries, deployments → instruments, instruments → using deployments, facility → owner contacts, and ObservationSeries → non-owner role contacts.
- Use modal pop-up JSON editors for deeper metadata and fields that do not yet have dedicated form widgets, including raw relationship references that are intentionally hidden from the main cards once represented as links.
- Save the edited record to local JSON-file storage.
- Validate the saved record against a WMDR2 core schema fragment.
- Download the valid WMDR2 full record as JSON.

## Why this shape

The current WMDR2 draft tooling represents a full record as a facility-centric GeoJSON-like `Feature`, with WMDR2-specific content under `properties`. The PoC follows that shape directly. It also keeps the editorial UI separate from any later OGC API publication endpoint: editing needs workflow/state/change management, while public catalogue access can later be backed by pygeoapi or another OGC API implementation.

This version is aligned with the current `wmdr2-devt` v0.2.5.x examples: `observationSeries` rather than `observations`, `observedFeature` rather than `observedDomain`, singular `programAffiliation`, scalar `deployment.instrument`, and simple string arrays for contact `emails` and `phones`.

For usability, raw reference fields such as `observingConfigurations[*].deployment` and `deployment.instrument` are not shown as ordinary text inputs in the main cards. They remain in the JSON record and can still be edited through the item-level or section-level JSON dialogs.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn node.app:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The UI includes a built-in example record. Use **Load example** to test the workflow immediately.

## Run tests

```bash
pip install -e .[dev]
pytest -q
```

## Run with Docker

```bash
docker build -t oscar-nextgen-node-poc .
docker run --rm -p 8000:8000 -v "$PWD/data/records:/app/data/records" oscar-nextgen-node-poc
```

## API overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Browser UI |
| `GET` | `/health` | Health check |
| `GET` | `/api/schema` | PoC validation schema |
| `GET` | `/api/records` | List locally saved record ids |
| `POST` | `/api/records` | Upload or submit a WMDR2 record |
| `GET` | `/api/records/{record_id}` | Read saved record plus validation report |
| `PUT` | `/api/records/{record_id}` | Replace full saved record |
| `PATCH` | `/api/records/{record_id}/sections/{section}` | Replace one editable section |
| `POST` | `/api/records/{record_id}/validate` | Validate saved record |
| `GET` | `/api/records/{record_id}/download` | Download only if structurally valid |

Supported section names are `facility`, `observationSeries`, `deployments`, `instruments`, `contacts`, `reporting`, and `schedules`. The older PoC alias `observations` is still accepted and saved as `observationSeries`.

## Storage

Records are stored as JSON files under:

```text
data/records/
```

Override with:

```bash
export OSCAR_NODE_DATA_DIR=/path/to/records
```

This is deliberately simple. The next step would normally be a repository layer backed by PostgreSQL JSONB, object storage, or Git-like versioned JSON artifacts.

## Validation notes

The PoC schema catches the core structural problems most likely to arise during editing:

- root `type`, `id`, `geometry`, `time`, `conformsTo`, and `properties`;
- required `properties.type = "facility"` and `properties.title`;
- current names such as `observedProperty`, `observedGeometry`, and `referenceSurface`;
- forbidden legacy names such as `observedVariable`, `observedGeometryType`, `localReferenceSurface`, and top-level `properties.temporalGeometry`;
- structural checks for observation series, deployments, instruments, contacts, and temporal geometry;
- semantic warnings for broken observation → deployment and deployment → instrument references.

It does **not** yet validate WMO code-list membership, authorization, workflow states, approval history, or synchronization with a Global Data Centre/cache.

## Suggested next development slices

1. Replace or augment the local schema fragment with the authoritative schema files from `wmo-im/wmdr2-devt/schemas` as a Git submodule or build-time copy.
2. Add codelist-aware controls for fields such as observed property, observed geometry, facility type, WMO region, reporting status, and program affiliation.
3. Add versioning: draft, submitted, reviewed, approved, published.
4. Add richer referential integrity controls, such as one-click creation of missing deployments/instruments from broken references and dedicated relationship pickers for deployment/instrument/contact links.
5. Add a publication adapter that writes validated records into an OGC API Records/pygeoapi-compatible catalogue view.
6. Add container composition with persistent storage and, later, identity/authentication.
