const state = {
  record: null,
  recordId: null,
  validation: null,
  vocabularies: {},
  vocabularyStatus: 'not-loaded',
  modalTarget: null,
  pendingScrollTarget: null,
  selectedTemporalGeometryIndex: null,
  sourceFilename: null,
  saveLocation: 'data/records',
  justLoaded: false,
};

const TOP_LEVEL_SECTION_IDS = [
  'facilitySection',
  'observationsSection',
  'configurationsSection',
  'instrumentsSection',
  'contactsSection',
  'fullRecordSection',
];

const $ = (id) => document.getElementById(id);
const asArray = (value) => Array.isArray(value) ? value : [];
const pretty = (value) => JSON.stringify(value ?? null, null, 2);

// Build browser URLs relative to the directory from which app.js was loaded.
// This is important in hosted environments such as Renku, where the app is
// served below a session-specific prefix instead of directly below /.
const scriptElement = document.querySelector('script[src*="app.js"]');
const appBaseUrl = new URL('..', scriptElement?.src || window.location.href);

function appUrl(path) {
  const value = String(path);
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
    return value;
  }
  return new URL(value.replace(/^\/+/, ''), appBaseUrl).toString();
}


function isoDateOrEmpty(value) {
  const text = String(value ?? '').trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : '';
}

function cssAttrValue(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function dateControlHtml(field, value, label) {
  return `<input class="date-input" type="date" data-field="${escapeAttr(field)}" value="${escapeAttr(isoDateOrEmpty(value))}" aria-label="${escapeAttr(label)}" title="${escapeAttr(label)}; blank is stored as .." />`;
}

function syncDatePickerFromTextInput(input) {
  const formScope = input.closest('[data-kind], #facilityForm');
  if (!formScope) return;
  const linkedName = input.name;
  const linkedField = input.dataset?.field;
  let picker = null;
  if (linkedField) {
    picker = formScope.querySelector(`input[type="date"][data-linked-field="${cssAttrValue(linkedField)}"]`);
  } else if (linkedName) {
    picker = formScope.querySelector(`input[type="date"][data-linked-name="${cssAttrValue(linkedName)}"]`);
  }
  if (picker) picker.value = isoDateOrEmpty(input.value);
}

function syncDatePickers(container) {
  container.querySelectorAll('input[data-date-text], input[data-field="time.interval.0"], input[data-field="time.interval.1"]').forEach(syncDatePickerFromTextInput);
}

function applyDatePickerValue(event) {
  const picker = event.target?.closest?.('input[type="date"][data-linked-name], input[type="date"][data-linked-field]');
  if (!picker) return false;
  const formScope = picker.closest('[data-kind], #facilityForm');
  if (!formScope) return false;
  let linked = null;
  if (picker.dataset.linkedField) {
    linked = formScope.querySelector(`[data-field="${cssAttrValue(picker.dataset.linkedField)}"]`);
  } else if (picker.dataset.linkedName) {
    linked = formScope.querySelector(`[name="${cssAttrValue(picker.dataset.linkedName)}"]`);
  }
  if (!linked) return false;
  linked.value = picker.value || '..';
  return true;
}


function vocabulary(name) {
  return state.vocabularies?.[name] || { options: [], source: 'unavailable' };
}

function vocabularyOptions(name) {
  return asArray(vocabulary(name).options);
}

function vocabularyDatalistId(name) {
  return `vocab-${name}`;
}

function optionValue(option) {
  return inputValue(option?.value ?? '');
}

function optionLabel(option) {
  const value = optionValue(option);
  const label = inputValue(option?.label ?? '').trim();
  if (!label || label === value) return value;
  return `${value} — ${label}`;
}

function selectOptionsHtml(vocabularyName, currentValue, { includeBlank = true, blankLabel = '— Select —' } = {}) {
  const current = inputValue(currentValue).trim();
  const options = vocabularyOptions(vocabularyName);
  const seen = new Set();
  const parts = [];
  if (includeBlank) {
    parts.push(`<option value="">${escapeHtml(blankLabel)}</option>`);
  }
  options.forEach(option => {
    const value = optionValue(option).trim();
    if (!value || seen.has(value)) return;
    seen.add(value);
    const selected = value === current ? ' selected' : '';
    const title = [option?.label, option?.description].filter(Boolean).join(' — ');
    parts.push(`<option value="${escapeAttr(value)}"${selected}${title ? ` title="${escapeAttr(title)}"` : ''}>${escapeHtml(optionLabel(option))}</option>`);
  });
  if (current && !seen.has(current)) {
    parts.unshift(`<option value="${escapeAttr(current)}" selected>${escapeHtml(`${current} — current value`)}</option>`);
  }
  return parts.join('');
}

function setSelectValue(select, value, label = 'current value') {
  if (!select) return;
  const text = inputValue(value).trim();
  if (text && ![...select.options].some(option => option.value === text)) {
    const option = document.createElement('option');
    option.value = text;
    option.textContent = `${text} — ${label}`;
    select.insertBefore(option, select.firstChild);
  }
  select.value = text;
}

function populateStaticVocabularySelects(container = document) {
  container.querySelectorAll('select[data-vocabulary-select]').forEach(select => {
    const current = select.value || select.dataset.currentValue || '';
    const vocabularyName = select.dataset.vocabularySelect;
    select.innerHTML = selectOptionsHtml(vocabularyName, current, { blankLabel: '— Select —' });
    setSelectValue(select, current);
  });
}

function codeInputHtml(field, value, vocabularyName, placeholder = '') {
  const placeholderText = placeholder || '— Select —';
  return `<select class="vocab-select" data-field="${escapeAttr(field)}" data-vocabulary-select="${escapeAttr(vocabularyName)}">${selectOptionsHtml(vocabularyName, value, { blankLabel: placeholderText })}</select>`;
}

function multiCodeInputHtml(field, values, vocabularyName, label) {
  const value = asArray(values).join(', ');
  const selectHtml = selectOptionsHtml(vocabularyName, '', { blankLabel: `Add ${label || 'choice'}…` });
  return `
    <div class="multi-vocab">
      <input data-field="${escapeAttr(field)}" value="${escapeAttr(value)}" placeholder="comma-separated values" />
      <select class="vocab-select add-vocab-select" data-add-vocab-target="${escapeAttr(field)}" aria-label="Add ${escapeAttr(label || field)} from vocabulary">${selectHtml}</select>
    </div>`;
}

function appendVocabularyChoice(select) {
  const value = select.value;
  if (!value) return false;
  const targetField = select.dataset.addVocabTarget;
  const scope = select.closest('[data-kind], #facilityForm') || document;
  const input = scope.querySelector(`input[data-field="${cssAttrValue(targetField)}"]`);
  if (!input) return false;
  const values = splitValues(input.value);
  if (!values.includes(value)) {
    values.push(value);
    input.value = values.join(', ');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  select.value = '';
  return true;
}

function renderVocabularyDatalists() {
  const container = $('vocabularyDatalists');
  if (!container) return;
  const vocabularies = state.vocabularies || {};
  container.innerHTML = Object.entries(vocabularies).map(([name, vocab]) => {
    const options = asArray(vocab.options).map(option => {
      const value = option?.value ?? '';
      const label = option?.label && option.label !== value ? option.label : '';
      const title = [option?.label, option?.description].filter(Boolean).join(' — ');
      return `<option value="${escapeAttr(value)}"${label ? ` label="${escapeAttr(label)}"` : ''}${title ? ` title="${escapeAttr(title)}"` : ''}></option>`;
    }).join('');
    return `<datalist id="${escapeAttr(vocabularyDatalistId(name))}">${options}</datalist>`;
  }).join('');
  populateStaticVocabularySelects();
}

async function loadVocabularies() {
  try {
    const result = await api('/api/vocabularies?live=true');
    state.vocabularies = result.vocabularies || {};
    state.vocabularyStatus = result.source || 'loaded';
    renderVocabularyDatalists();
    if (state.record) renderAll();
  } catch (error) {
    console.warn('Could not load WMDR code lists; using browser-side empty suggestions.', error);
    state.vocabularies = {};
    state.vocabularyStatus = 'unavailable';
    renderVocabularyDatalists();
    if (state.record) renderAll();
  }
}

const exampleRecord = {
  type: 'Feature',
  id: '0-20000-0-06725',
  geometry: { type: 'Point', coordinates: [7.8232, 46.4204, 1540] },
  temporalGeometry: {
    type: 'MovingPoint',
    coordinates: [[7.823197, 46.420453, 1538], [7.8232, 46.4204, 1540]],
    dates: ['2000-08-17', '2024-01-17'],
    methods: [[], ['gps']],
  },
  time: { interval: ['2000-08-17', '..'], resolution: 'P1D' },
  conformsTo: ['http://wigos.wmo.int/spec/wmdr/2/conf/core'],
  properties: {
    type: 'facility',
    title: 'Blatten',
    description: 'Example facility for OSCAR nextGen Node PoC.',
    wmoRegion: 'europe',
    keywords: ['0-20000-0-06725', 'Blatten'],
    contacts: [
      {
        identifier: 'contact:metadata-office',
        organization: 'Example NMHS',
        name: 'Station metadata office',
        roles: ['owner', 'pointOfContact'],
        emails: ['metadata@example.invalid'],
      },
    ],
    programAffiliations: [
      { time: { interval: ['2000-08-17', '..'] }, program: 'GOSGeneral', reportingStatus: 'operational' },
    ],
    territory: [{ time: { interval: ['2000-08-17', '..'] }, territory: 'CHE' }],
    environment: [{ time: { interval: ['2000-08-17', '..'] }, surfaceCover: 'grassland' }],
    observationSeries: [
      {
        id: 'observationSeries:12006',
        title: 'Horizontal wind speed at specified distance from reference surface',
        observedProperty: 12006,
        observedFeature: { domain: 'atmosphere', domainFeature: 'near-surface-air', featureName: '10 m air' },
        observedGeometry: 'point',
        programAffiliations: ['GOSGeneral'],
        applicationAreas: ['weatherForecasting'],
        observingConfigurations: [
          {
            time: { interval: ['2020-01-01', '..'] },
            referenceSurface: 'localGround',
            verticalDistanceFromReferenceSurface: { value: 10, uom: 'm' },
            observingMethod: 266,
            sourceOfObservation: 'automaticReading',
            instrument: 'instrument:wind-sensor-type-a',
          },
        ],
      },
    ],
    instruments: [
      {
        id: 'instrument:wind-sensor-type-a',
        manufacturer: 'Example manufacturer',
        model: 'WindSensor X',
        observingMethods: [266],
      },
    ],
    schedules: [],
  },
};

function props() {
  state.record.properties ??= { type: 'facility', title: '' };
  state.record.properties.observationSeries ??= [];
  state.record.properties.instruments ??= [];
  state.record.properties.contacts ??= [];
  state.record.properties.schedules ??= [];
  delete state.record.properties.deployments;
  delete state.record.properties.reporting;
  return state.record.properties;
}

function setStatus(text, kind = '') {
  const el = $('status');
  el.textContent = text;
  el.className = `status ${kind}`.trim();
}

function parseJson(text, label = 'JSON') {
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
}

async function api(path, options = {}) {
  const response = await fetch(appUrl(path), {
    headers: options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined,
    ...options,
  });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === 'object' ? payload.detail || payload : payload;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2));
  }
  return payload;
}

async function loadRecord(record, sourceFilename = null) {
  const result = await api('/api/records', { method: 'POST', body: JSON.stringify(record) });
  acceptLoadedRecord(result, sourceFilename);
  await refreshSavedRecords(result.id);
}

async function refreshSavedRecords(selectedId = state.recordId || state.record?.id || '') {
  const select = $('savedRecordSelect');
  const status = $('savedRecordsStatus');
  if (!select) return;
  try {
    const result = await api('/api/records');
    const records = asArray(result.records);
    select.innerHTML = records.length
      ? records.map(id => `<option value="${escapeAttr(id)}">${escapeHtml(id)}</option>`).join('')
      : '<option value="">No saved records found</option>';
    if (selectedId && records.includes(selectedId)) select.value = selectedId;
    if (status) status.textContent = records.length ? `${records.length} saved record(s) available.` : 'No saved records in the Node data directory yet.';
    $('openSavedBtn').disabled = records.length === 0;
  } catch (error) {
    select.innerHTML = '<option value="">Could not load saved records</option>';
    if (status) status.textContent = error.message;
    $('openSavedBtn').disabled = true;
  }
}

async function openSavedRecord() {
  const selectedId = $('savedRecordSelect')?.value;
  if (!selectedId) {
    alert('No saved record selected.');
    return;
  }
  try {
    const result = await api(`/api/records/${encodeURIComponent(selectedId)}`);
    acceptLoadedRecord(result, `${selectedId}.json`);
  } catch (error) {
    alert(error.message);
  }
}

function acceptLoadedRecord(result, sourceFilename = null) {
  state.record = result.record;
  state.recordId = result.id;
  state.validation = result.validation;
  state.sourceFilename = sourceFilename || defaultSaveFileName();
  state.justLoaded = true;
  renderAll();
}

async function saveFullRecord() {
  syncFacilityForm();
  syncItemForms();
  const result = await api(`/api/records/${encodeURIComponent(state.recordId)}`, {
    method: 'PUT',
    body: JSON.stringify(state.record),
  });
  state.record = result.record;
  state.recordId = result.id;
  state.validation = result.validation;
  renderAll();
  return result;
}

async function validateRecord() {
  await saveFullRecord();
}

function renderAll() {
  if (!state.record) return;
  $('recordTitle').textContent = props().title || state.record.id || 'Untitled facility';
  $('recordId').textContent = state.record.id || 'No id';
  $('saveBtn').disabled = false;
  $('validateBtn').disabled = false;
  $('downloadLink').classList.remove('disabled');
  $('downloadLink').setAttribute('aria-disabled', 'false');
  $('downloadLink').href = appUrl(`api/records/${encodeURIComponent(state.record.id)}/download`);
  renderFacility();
  renderObservationSeries();
  renderConfigurationsOverview();
  renderInstruments();
  renderContacts();
  $('recordRaw').value = pretty(state.record);
  renderValidation();
  if (state.justLoaded) {
    state.justLoaded = false;
    focusSection('facilitySection', { scroll: false });
  }
  if (state.pendingScrollTarget) {
    const target = state.pendingScrollTarget;
    state.pendingScrollTarget = null;
    window.setTimeout(() => scrollToItem(target), 0);
  }
}

function renderValidation() {
  const panel = $('validationPanel');
  if (!state.validation) {
    panel.className = 'validation empty';
    panel.textContent = 'No validation result yet.';
    setStatus('Not validated');
    return;
  }
  const errors = state.validation.errors || [];
  const warnings = state.validation.warnings || [];
  const valid = state.validation.valid;
  panel.className = `validation ${valid ? (warnings.length ? 'warning' : 'valid') : 'invalid'}`;
  setStatus(valid ? (warnings.length ? 'Valid with warnings' : 'Valid WMDR2 v0.3.x') : 'Invalid WMDR2 v0.3.x', valid ? (warnings.length ? 'warning' : 'valid') : 'invalid');
  const parts = [];
  parts.push(`<strong>${valid ? 'Structurally valid.' : `${errors.length} error(s).`}</strong>`);
  if (errors.length) {
    parts.push('<h3>Errors</h3><ul>' + errors.map(e => `<li><code>${escapeHtml(e.path)}</code>: ${escapeHtml(e.message)}</li>`).join('') + '</ul>');
  }
  if (warnings.length) {
    parts.push('<h3>Warnings</h3><ul>' + warnings.map(w => `<li><code>${escapeHtml(w.path)}</code>: ${escapeHtml(w.message)}</li>`).join('') + '</ul>');
  }
  panel.innerHTML = parts.join('');
}

function renderFacility() {
  const form = $('facilityForm');
  const p = props();
  form.elements.id.value = state.record.id || '';
  form.elements.title.value = p.title || '';
  form.elements.description.value = p.description || '';
  setSelectValue(form.elements.wmoRegion, p.wmoRegion || '');
  const coords = state.record.geometry?.coordinates || [];
  form.elements.lon.value = coords[0] ?? '';
  form.elements.lat.value = coords[1] ?? '';
  form.elements.elev.value = coords[2] ?? '';
  const interval = state.record.time?.interval || [];
  form.elements.begin.value = isoDateOrEmpty(interval[0]);
  form.elements.end.value = isoDateOrEmpty(interval[1]);
  renderTemporalGeometryHistory();
  renderFacilityContactLinks();
}

function syncFacilityForm() {
  if (!state.record) return;
  const form = $('facilityForm');
  const p = props();
  state.record.id = form.elements.id.value.trim() || state.record.id;
  p.type = 'facility';
  p.title = form.elements.title.value.trim() || 'Untitled facility';
  p.description = form.elements.description.value;
  if (form.elements.wmoRegion.value.trim()) p.wmoRegion = form.elements.wmoRegion.value.trim();
  else delete p.wmoRegion;
  const lon = numberOrNull(form.elements.lon.value);
  const lat = numberOrNull(form.elements.lat.value);
  const elev = numberOrNull(form.elements.elev.value);
  if (lon !== null && lat !== null) {
    state.record.geometry = { type: 'Point', coordinates: elev === null ? [lon, lat] : [lon, lat, elev] };
  }
  syncTemporalGeometryForms();
  const begin = form.elements.begin.value.trim() || '..';
  const end = form.elements.end.value.trim() || '..';
  state.record.time = { interval: [begin, end], resolution: state.record.time?.resolution || 'P1D' };
}

function temporalGeometryRows() {
  const tg = state.record?.temporalGeometry;
  if (!tg || tg.type !== 'MovingPoint') return [];
  const coordinates = asArray(tg.coordinates);
  const dates = asArray(tg.dates);
  const methods = asArray(tg.methods);
  const count = Math.max(coordinates.length, dates.length, methods.length);
  return Array.from({ length: count }, (_, index) => ({
    coordinates: asArray(coordinates[index]),
    date: dates[index] ?? '..',
    methods: asArray(methods[index]),
  }));
}

function renderTemporalGeometryHistory() {
  const rows = temporalGeometryRows();
  const count = $('temporalGeometryCount');
  const list = $('temporalGeometryList');
  if (!count || !list) return;
  count.textContent = rows.length;
  if (!rows.length) {
    state.selectedTemporalGeometryIndex = null;
    list.innerHTML = '<p class="muted">No temporalGeometry history yet. Add a row from the current facility geometry.</p>';
    return;
  }
  if (state.selectedTemporalGeometryIndex === null || state.selectedTemporalGeometryIndex >= rows.length) {
    state.selectedTemporalGeometryIndex = 0;
  }
  list.innerHTML = `
    <div class="table-wrap temporal-geometry-table-wrap">
      <table class="data-table temporal-geometry-table">
        <thead>
          <tr>
            <th scope="col">Selected</th>
            <th scope="col">Date</th>
            <th scope="col">Longitude</th>
            <th scope="col">Latitude</th>
            <th scope="col">Elevation</th>
            <th scope="col">Methods</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>${rows.map((row, index) => temporalGeometryRowHtml(row, index)).join('')}</tbody>
      </table>
    </div>
    <p class="muted">Select a row to focus it, edit values directly in the table, or add another row from the current facility coordinates.</p>`;
}

function temporalGeometryRowHtml(row, index) {
  const coordinates = row.coordinates;
  const selected = state.selectedTemporalGeometryIndex === index;
  return `
    <tr class="temporal-geometry-item ${selected ? 'selected' : ''}" id="${temporalGeometryDomId(index)}" data-item-kind="temporalGeometry" data-kind="temporalGeometry" data-index="${index}" data-temporal-geometry-index="${index}">
      <td>
        <button class="small-button" data-select-temporal-geometry="${index}" type="button" aria-pressed="${selected ? 'true' : 'false'}">${selected ? 'Editing' : 'Edit'}</button>
      </td>
      <td><label class="sr-only">Date for geolocation row ${index + 1}</label><input data-field="date" placeholder="YYYY-MM-DD or .." value="${escapeAttr(row.date || '..')}" /></td>
      <td><label class="sr-only">Longitude for geolocation row ${index + 1}</label><input data-field="lon" type="number" step="any" value="${escapeAttr(coordinates[0] ?? '')}" /></td>
      <td><label class="sr-only">Latitude for geolocation row ${index + 1}</label><input data-field="lat" type="number" step="any" value="${escapeAttr(coordinates[1] ?? '')}" /></td>
      <td><label class="sr-only">Elevation for geolocation row ${index + 1}</label><input data-field="elev" type="number" step="any" value="${escapeAttr(coordinates[2] ?? '')}" /></td>
      <td><label class="sr-only">Methods for geolocation row ${index + 1}</label><input data-field="methods" placeholder="gps" value="${escapeAttr(asArray(row.methods).join(', '))}" /></td>
      <td><button class="small-button danger" data-delete-temporal-geometry="${index}" type="button">Delete</button></td>
    </tr>`;
}

function syncTemporalGeometryForms() {
  const list = $('temporalGeometryList');
  if (!state.record || !list) return;
  const forms = [...list.querySelectorAll('[data-kind="temporalGeometry"]')];
  if (!forms.length) {
    delete state.record.temporalGeometry;
    return;
  }
  const coordinates = [];
  const dates = [];
  const methods = [];
  forms.forEach(form => {
    const field = name => form.querySelector(`[data-field="${name}"]`);
    const lon = numberOrOriginal(field('lon')?.value);
    const lat = numberOrOriginal(field('lat')?.value);
    const elevText = field('elev')?.value ?? '';
    const coordinate = [lon, lat];
    if (String(elevText).trim() !== '') coordinate.push(numberOrOriginal(elevText));
    coordinates.push(coordinate);
    dates.push((field('date')?.value || '').trim() || '..');
    methods.push(splitValues(field('methods')?.value || ''));
  });
  state.record.temporalGeometry = { type: 'MovingPoint', coordinates, dates, methods };
  updateCurrentGeometryFromLatestTemporalGeometry();
}

function updateCurrentGeometryFromLatestTemporalGeometry() {
  const rows = temporalGeometryRows();
  const latest = [...rows].reverse().find(row => isCompleteCoordinate(row.coordinates));
  if (!latest) return;
  state.record.geometry = {
    type: 'Point',
    coordinates: latest.coordinates.slice(0, 3).map(value => Number.isFinite(Number(value)) ? Number(value) : value),
  };
}

function isCompleteCoordinate(coordinates) {
  return Array.isArray(coordinates)
    && coordinates.length >= 2
    && coordinates[0] !== null
    && coordinates[0] !== ''
    && coordinates[1] !== null
    && coordinates[1] !== ''
    && Number.isFinite(Number(coordinates[0]))
    && Number.isFinite(Number(coordinates[1]));
}

function temporalGeometryDomId(index) {
  return `temporalGeometry-${index}`;
}

function formatCoordinate(coordinates) {
  if (!coordinates.length) return 'missing coordinates';
  return coordinates.map(value => value ?? '').join(', ');
}

function numberOrOriginal(value) {
  const text = String(value ?? '').trim();
  if (text === '') return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : text;
}

function addTemporalGeometryRow() {
  if (!state.record) {
    alert('Load a WMDR2 record before adding geolocation history.');
    return;
  }
  syncFacilityForm();
  syncItemForms();
  const tg = ensureTemporalGeometry();
  const current = state.record?.geometry?.coordinates;
  const hasCurrent = Array.isArray(current) && current.length >= 2;
  const newCoordinates = hasCurrent
    ? current.slice(0, 3).map(value => Number.isFinite(Number(value)) ? Number(value) : value)
    : [null, null, null];
  tg.coordinates.push(newCoordinates);
  tg.dates.push(state.record.time?.interval?.[0] || '..');
  tg.methods.push([]);
  const newIndex = tg.coordinates.length - 1;
  state.selectedTemporalGeometryIndex = newIndex;
  state.pendingScrollTarget = temporalGeometryDomId(newIndex);
  renderAll();
}

function ensureTemporalGeometry() {
  const existing = state.record.temporalGeometry;
  if (!existing || typeof existing !== 'object' || existing.type !== 'MovingPoint') {
    state.record.temporalGeometry = { type: 'MovingPoint', coordinates: [], dates: [], methods: [] };
  }
  const tg = state.record.temporalGeometry;
  tg.type = 'MovingPoint';
  if (!Array.isArray(tg.coordinates)) tg.coordinates = [];
  if (!Array.isArray(tg.dates)) tg.dates = [];
  if (!Array.isArray(tg.methods)) tg.methods = [];
  return tg;
}

function deleteTemporalGeometryRow(index) {
  syncFacilityForm();
  const tg = state.record.temporalGeometry;
  if (!tg) return;
  tg.coordinates = asArray(tg.coordinates);
  tg.dates = asArray(tg.dates);
  tg.methods = asArray(tg.methods);
  tg.coordinates.splice(index, 1);
  tg.dates.splice(index, 1);
  tg.methods.splice(index, 1);
  if (!tg.coordinates.length && !tg.dates.length && !tg.methods.length) {
    delete state.record.temporalGeometry;
    state.selectedTemporalGeometryIndex = null;
  } else {
    updateCurrentGeometryFromLatestTemporalGeometry();
    if (state.selectedTemporalGeometryIndex !== null) {
      state.selectedTemporalGeometryIndex = Math.min(state.selectedTemporalGeometryIndex, tg.coordinates.length - 1);
    }
  }
  renderAll();
}

function renderObservationSeries() {
  const series = asArray(props().observationSeries);
  $('observationCount').textContent = series.length;
  $('observationsList').innerHTML = series.map((obs, index) => itemHtml(
    observationSeriesHeaderTitle(obs, index),
    observationSeriesFormHtml(obs, index),
    'observationSeries',
    index,
  )).join('') || '<p class="muted">No ObservationSeries yet.</p>';
}

function observationSeriesHeaderTitle(obs, index) {
  const id = entityId(obs) || `observationSeries:${index + 1}`;
  const title = String(obs.title || '').trim();
  return title ? `${id} [${title}]` : id;
}

function observationSeriesFormHtml(obs, index) {
  return `
    <div class="item-form observation-form" data-kind="observationSeries" data-index="${index}">
      <div class="observation-row two">
        <label>Observed property ${codeInputHtml('observedProperty', obs.observedProperty, 'observedVariableAtmosphere')}</label>
        <label>Observed geometry ${codeInputHtml('observedGeometry', obs.observedGeometry, 'observedGeometry')}</label>
      </div>
      <div class="observation-row three">
        <label>Domain ${codeInputHtml('observedFeature.domain', obs.observedFeature?.domain, 'domain')}</label>
        <label>Domain feature <input data-field="observedFeature.domainFeature" value="${escapeAttr(obs.observedFeature?.domainFeature ?? '')}" /></label>
        <label>Feature name <input data-field="observedFeature.featureName" value="${escapeAttr(obs.observedFeature?.featureName ?? '')}" /></label>
      </div>
      <div class="observation-row two">
        <label>Program affiliations ${multiCodeInputHtml('programAffiliations', obs.programAffiliations, 'programAffiliations', 'program affiliation')}</label>
        <label>Application areas ${multiCodeInputHtml('applicationAreas', obs.applicationAreas, 'applicationAreas', 'application area')}</label>
      </div>
    </div>
    ${observationConfigurationLinksHtml(obs, index)}
    ${observationInstrumentLinksHtml(obs)}
    ${observationContactLinksHtml(obs)}
    <div class="actions section-actions">
      <button type="button" data-add-config="${index}">Add observing configuration</button>
      <button type="button" data-add-observation-instrument="${index}">Add linked instrument</button>
    </div>`;
}

function observationConfigurations(obs) {
  return asArray(obs.observingConfigurations);
}

function flattenConfigurations() {
  return asArray(props().observationSeries).flatMap((obs, seriesIndex) =>
    observationConfigurations(obs).map((config, configIndex) => ({ obs, config, seriesIndex, configIndex }))
  );
}

function configurationDomId(seriesIndex, configIndex) {
  return `configuration-${seriesIndex}-${configIndex}`;
}

function observationInstrumentRefs(obs) {
  return [...new Set(observationConfigurations(obs).map(c => c?.instrument).filter(Boolean))];
}

function observationConfigurationLinksHtml(obs, index) {
  const links = observationConfigurations(obs).map((config, configIndex) => {
    const label = configLabel(config, configIndex);
    return `<a class="xref" href="#${configurationDomId(index, configIndex)}" data-scroll-target="${configurationDomId(index, configIndex)}">${escapeHtml(label)}</a>`;
  });
  return xrefRow('Observing configurations', links, 'No observingConfigurations');
}

function observationInstrumentLinksHtml(obs) {
  const instrumentIndex = indexByUid('instrument');
  const links = observationInstrumentRefs(obs).map(ref => linkToItem('instrument', instrumentIndex.get(ref), ref));
  return xrefRow('Linked instruments', links, 'No instrument refs in observingConfigurations');
}

function renderConfigurationsOverview() {
  const configs = flattenConfigurations();
  $('configurationCount').textContent = configs.length;
  $('configurationsList').innerHTML = configs.map(({ obs, config, seriesIndex, configIndex }) => configurationItemHtml(obs, config, seriesIndex, configIndex)).join('') || '<p class="muted">No observing configurations yet.</p>';
}

function configurationItemHtml(obs, config, seriesIndex, configIndex) {
  const domId = configurationDomId(seriesIndex, configIndex);
  return `
    <article class="item" id="${domId}" data-item-kind="observingConfiguration" data-series-index="${seriesIndex}" data-config-index="${configIndex}">
      <div class="item-header">
        <div class="item-title">${escapeHtml(configLabel(config, configIndex))}</div>
        <div class="actions">
          <button data-json-config="${seriesIndex}:${configIndex}" type="button">Edit JSON</button>
          <button data-delete-config="${seriesIndex}:${configIndex}" type="button">Delete</button>
        </div>
      </div>
      ${configurationFormHtml(config, seriesIndex, configIndex)}
      ${configurationCrossLinksHtml(obs, config, seriesIndex)}
    </article>`;
}

function configLabel(config, index) {
  const method = displayCompact(config.observingMethod);
  const instr = config.instrument ? `; ${config.instrument}` : '';
  return `${configStart(config) || 'missing start'}; method ${method || '?'}${instr}` || `Configuration ${index + 1}`;
}

function configurationFormHtml(config, seriesIndex, configIndex) {
  return `
    <div class="item-form" data-kind="observingConfiguration" data-series-index="${seriesIndex}" data-config-index="${configIndex}">
      <label>Begin ${dateControlHtml('time.interval.0', configStart(config), 'configuration begin date')}</label>
      <label>End ${dateControlHtml('time.interval.1', configEnd(config), 'configuration end date')}</label>
      <label>Observing method ${codeInputHtml('observingMethod', config.observingMethod, 'observingMethodAtmosphere')}</label>
      <label>Operating status ${codeInputHtml('operatingStatus', config.operatingStatus, 'operatingStatus')}</label>
      <label>Source of observation ${codeInputHtml('sourceOfObservation', config.sourceOfObservation, 'sourceOfObservation')}</label>
      <label>Instrument ID <input data-field="instrument" value="${escapeAttr(config.instrument || '')}" /></label>
      <label>Serial number <input data-field="serialNumber" value="${escapeAttr(config.serialNumber || '')}" /></label>
      <label>Exposure ${codeInputHtml('exposure', config.exposure, 'exposure')}</label>
      <label>Reference surface ${codeInputHtml('referenceSurface', config.referenceSurface, 'referenceSurface')}</label>
      <label>Relative location <input data-field="relativeLocation" value="${escapeAttr(config.relativeLocation ?? '')}" /></label>
      <label>Vertical distance value <input data-field="verticalDistanceFromReferenceSurface.value" value="${escapeAttr(config.verticalDistanceFromReferenceSurface?.value ?? '')}" /></label>
      <label>Vertical distance uom ${codeInputHtml('verticalDistanceFromReferenceSurface.uom', config.verticalDistanceFromReferenceSurface?.uom, 'unit')}</label>
    </div>`;
}

function configurationCrossLinksHtml(obs, config, seriesIndex) {
  const instrumentIndex = indexByUid('instrument');
  const obsLink = linkToItem('observationSeries', seriesIndex, entityId(obs) || obs.title || `ObservationSeries ${seriesIndex + 1}`);
  const instrumentLinks = config.instrument ? [linkToItem('instrument', instrumentIndex.get(config.instrument), config.instrument)] : [];
  return `${xrefRow('Belongs to', [obsLink], 'No ObservationSeries')}${xrefRow('Linked instrument', instrumentLinks, 'No instrument ref')}`;
}

function renderInstruments() {
  const instruments = asArray(props().instruments);
  $('instrumentCount').textContent = instruments.length;
  $('instrumentsList').innerHTML = instruments.map((inst, index) => itemHtml(
    entityId(inst) || `instrument:${index + 1}`,
    instrumentFormHtml(inst, index),
    'instrument',
    index,
  )).join('') || '<p class="muted">No instruments yet.</p>';
}

function instrumentFormHtml(inst, index) {
  return `
    <div class="item-form" data-kind="instrument" data-index="${index}">
      <label>ID <input data-field="id" value="${escapeAttr(entityId(inst))}" /></label>
      <label>Title <input data-field="title" value="${escapeAttr(inst.title || '')}" /></label>
      <label>Manufacturer <input data-field="manufacturer" value="${escapeAttr(inst.manufacturer || '')}" /></label>
      <label>Model <input data-field="model" value="${escapeAttr(inst.model || '')}" /></label>
      <label>Observing methods ${multiCodeInputHtml('observingMethods', inst.observingMethods, 'observingMethodAtmosphere', 'observing method')}</label>
      <label class="wide">Description <textarea data-field="description" rows="2">${escapeHtml(inst.description || '')}</textarea></label>
    </div>
    ${instrumentCrossLinksHtml(inst)}`;
}

function itemDomId(kind, index) {
  return `${kind}-${index}`;
}

function itemHtml(title, formHtml, kind, index) {
  return `
    <article class="item" id="${itemDomId(kind, index)}" data-item-kind="${kind}" data-item-index="${index}">
      <div class="item-header">
        <div class="item-title">${escapeHtml(title)}</div>
        <div class="actions">
          <button data-json-item="${kind}" data-index="${index}" type="button">Edit JSON</button>
          <button data-delete-item="${kind}" data-index="${index}" type="button">Delete</button>
        </div>
      </div>
      ${formHtml}
    </article>`;
}


function entityId(item) {
  return item?.id || item?.uid || item?.identifier || '';
}

function configStart(config) {
  return config?.time?.interval?.[0] ?? config?.validFrom ?? '';
}

function configEnd(config) {
  return config?.time?.interval?.[1] ?? '..';
}

function indexByUid(kind) {
  return new Map(getSectionForKind(kind).map((item, index) => [entityId(item), index]).filter(([id]) => Boolean(id)));
}

function linkToItem(kind, index, label) {
  if (index === undefined || index < 0) {
    return `<span class="xref missing" title="No matching ${escapeAttr(kind)} record found">${escapeHtml(label)} ⚠</span>`;
  }
  const id = itemDomId(kind, index);
  return `<a class="xref" href="#${id}" data-scroll-target="${id}">${escapeHtml(label)}</a>`;
}

function xrefRow(label, items, emptyText = 'None') {
  const content = items.length ? items.join('') : `<span class="xref-empty">${escapeHtml(emptyText)}</span>`;
  return `<div class="xref-row"><span class="xref-label">${escapeHtml(label)}</span><div class="xref-list">${content}</div></div>`;
}

function normalizeRole(role) {
  return String(role ?? '').trim().toLowerCase();
}

function contactLabel(contact, index) {
  return contact.name || contact.organization || entityId(contact) || `Contact ${index + 1}`;
}

function contactsWithRole(role) {
  const wanted = normalizeRole(role);
  return asArray(props().contacts)
    .map((contact, index) => ({ contact, index }))
    .filter(({ contact }) => asArray(contact.roles).map(normalizeRole).includes(wanted));
}

function contactsExceptRole(role) {
  const excluded = normalizeRole(role);
  return asArray(props().contacts)
    .map((contact, index) => ({ contact, index }))
    .filter(({ contact }) => asArray(contact.roles).some(r => normalizeRole(r) && normalizeRole(r) !== excluded));
}

function contactRoleText(contact, excludedRole = '') {
  const excluded = normalizeRole(excludedRole);
  return asArray(contact.roles)
    .filter(role => normalizeRole(role) && normalizeRole(role) !== excluded)
    .join(', ');
}

function contactLink(contact, index, prefix = '') {
  const label = prefix ? `${prefix}: ${contactLabel(contact, index)}` : contactLabel(contact, index);
  return linkToItem('contact', index, label);
}

function renderFacilityContactLinks() {
  const form = $('facilityForm');
  const existing = $('facilityContactLinks');
  if (existing) existing.remove();
  form.insertAdjacentHTML('afterend', `<div id="facilityContactLinks">${facilityContactLinksHtml()}</div>`);
}

function facilityContactLinksHtml() {
  const ownerContacts = contactsWithRole('owner');
  const ownerLinks = ownerContacts.map(({ contact, index }) => contactLink(contact, index));
  const buttonLabel = ownerContacts.length === 1 ? 'Edit owner contact' : (ownerContacts.length > 1 ? 'Edit owner contacts' : 'Add owner contact');
  return `${xrefRow('Owner contacts', ownerLinks, 'No contact has role owner')}<div class="actions section-actions inline-actions"><button type="button" data-open-owner-contact>${escapeHtml(buttonLabel)}</button></div>`;
}

function observationContactLinksHtml(_obs) {
  const links = contactsExceptRole('owner').map(({ contact, index }) => {
    const roles = contactRoleText(contact, 'owner');
    return contactLink(contact, index, roles || undefined);
  });
  return xrefRow('Contacts by role', links, 'No non-owner contact roles available');
}

function configsUsingInstrument(instrumentUid) {
  if (!instrumentUid) return [];
  return flattenConfigurations().filter(({ config }) => config?.instrument === instrumentUid);
}

function instrumentCrossLinksHtml(inst) {
  const configs = configsUsingInstrument(entityId(inst));
  const configLinks = configs.map(({ config, seriesIndex, configIndex }) =>
    `<a class="xref" href="#${configurationDomId(seriesIndex, configIndex)}" data-scroll-target="${configurationDomId(seriesIndex, configIndex)}">${escapeHtml(configLabel(config, configIndex))}</a>`
  );
  const seenSeries = new Set();
  const seriesLinks = configs
    .filter(({ seriesIndex }) => !seenSeries.has(seriesIndex) && seenSeries.add(seriesIndex))
    .map(({ obs, seriesIndex }) => linkToItem('observationSeries', seriesIndex, entityId(obs) || obs.title || `ObservationSeries ${seriesIndex + 1}`));
  return `${xrefRow('Used by configurations', configLinks, 'No observing configuration uses this instrument')}${xrefRow('Used by ObservationSeries', seriesLinks, 'No ObservationSeries uses this instrument')}`;
}

function renderContacts() {
  const contacts = asArray(props().contacts);
  $('contactCount').textContent = contacts.length;
  $('contactsList').innerHTML = contacts.map((contact, index) => itemHtml(
    contactLabel(contact, index),
    contactFormHtml(contact, index),
    'contact',
    index,
  )).join('') || '<p class="muted">No contacts yet.</p>';
}

function contactFormHtml(contact, index) {
  return `
    <div class="item-form" data-kind="contact" data-index="${index}">
      <label>Identifier <input data-field="identifier" value="${escapeAttr(entityId(contact))}" /></label>
      <label>Name <input data-field="name" value="${escapeAttr(contact.name || '')}" /></label>
      <label>Organization <input data-field="organization" value="${escapeAttr(contact.organization || '')}" /></label>
      <label>Position <input data-field="position" value="${escapeAttr(contact.position || '')}" /></label>
      <label>Roles, comma-separated <input data-field="roles" value="${escapeAttr(asArray(contact.roles).join(', '))}" /></label>
      <label>Email values, comma-separated <input data-field="emails" value="${escapeAttr(asArray(contact.emails).map(e => e.value ?? e).join(', '))}" /></label>
      <label class="wide">Phone values, comma-separated <input data-field="phones" value="${escapeAttr(asArray(contact.phones).map(p => p.value ?? p).join(', '))}" /></label>
    </div>
    ${contactCrossLinksHtml(contact)}`;
}

function contactCrossLinksHtml(contact) {
  const roles = asArray(contact.roles).map(normalizeRole);
  const links = [];
  if (roles.includes('owner')) {
    links.push(`<a class="xref" href="#facilitySection" data-scroll-target="facilitySection">Facility</a>`);
  }
  if (roles.some(role => role && role !== 'owner')) {
    links.push(`<a class="xref" href="#observationsSection" data-scroll-target="observationsSection">ObservationSeries</a>`);
  }
  return xrefRow('Linked from', links, 'No role-based section link');
}

function syncItemForms() {
  document.querySelectorAll('[data-kind="observationSeries"], [data-kind="instrument"], [data-kind="contact"]').forEach(form => {
    const kind = form.dataset.kind;
    const index = Number(form.dataset.index);
    const target = getSectionForKind(kind)[index];
    if (!target) return;
    form.querySelectorAll('[data-field]').forEach(input => {
      setField(target, input.dataset.field, coerceField(input.dataset.field, input.value));
    });
  });

  document.querySelectorAll('[data-kind="observingConfiguration"]').forEach(form => {
    const seriesIndex = Number(form.dataset.seriesIndex);
    const configIndex = Number(form.dataset.configIndex);
    const target = props().observationSeries?.[seriesIndex]?.observingConfigurations?.[configIndex];
    if (!target) return;
    form.querySelectorAll('[data-field]').forEach(input => {
      setField(target, input.dataset.field, coerceField(input.dataset.field, input.value));
    });
    cleanupObservingConfiguration(target);
  });
}

function cleanupObservingConfiguration(config) {
  const quantity = config.verticalDistanceFromReferenceSurface;
  if (quantity && typeof quantity === 'object' && !Array.isArray(quantity)) {
    if (isEmptyFormValue(quantity.value)) {
      delete config.verticalDistanceFromReferenceSurface;
    } else if (isEmptyFormValue(quantity.uom)) {
      delete quantity.uom;
    }
  }
}

function getSectionForKind(kind) {
  const p = props();
  if (kind === 'observationSeries') return p.observationSeries ??= [];
  if (kind === 'instrument') return p.instruments ??= [];
  if (kind === 'contact') return p.contacts ??= [];
  throw new Error(`Unknown item type ${kind}`);
}

function setField(obj, path, value) {
  const parts = path.split('.');
  let target = obj;
  const ancestors = [];
  while (parts.length > 1) {
    const key = parts.shift();
    const nextKey = parts[0];
    const shouldBeArray = /^\d+$/.test(nextKey);
    if (Array.isArray(target)) {
      const index = Number(key);
      target[index] ??= shouldBeArray ? [] : {};
      ancestors.push({ container: target, key: index });
      target = target[index];
    } else {
      target[key] ??= shouldBeArray ? [] : {};
      ancestors.push({ container: target, key });
      target = target[key];
    }
  }
  const finalKey = parts[0];
  const empty = isEmptyFormValue(value);
  if (Array.isArray(target) && /^\d+$/.test(finalKey)) {
    if (empty) delete target[Number(finalKey)];
    else target[Number(finalKey)] = value;
  } else if (empty) {
    delete target[finalKey];
  } else {
    target[finalKey] = value;
  }
  pruneEmptyAncestors(ancestors);
}

function isEmptyFormValue(value) {
  return value === '' || value === undefined || value === null || (Array.isArray(value) && !value.length);
}

function pruneEmptyAncestors(ancestors) {
  for (let index = ancestors.length - 1; index >= 0; index -= 1) {
    const { container, key } = ancestors[index];
    const value = container[key];
    const emptyObject = value && !Array.isArray(value) && typeof value === 'object' && Object.keys(value).length === 0;
    const emptyArray = Array.isArray(value) && value.length === 0;
    if (emptyObject || emptyArray) delete container[key];
    else break;
  }
}

function coerceField(field, value) {
  const trimmed = String(value ?? '').trim();
  if (field === 'time.interval.0' || field === 'time.interval.1') return trimmed || '..';
  if (['programAffiliations', 'applicationAreas', 'observingMethods', 'roles'].includes(field)) {
    return splitValues(trimmed).map(valueOrNumber);
  }
  if (['emails', 'phones'].includes(field)) {
    return splitValues(trimmed);
  }
  if (['observedProperty', 'observedGeometry', 'observingMethod', 'operatingStatus', 'sourceOfObservation', 'exposure'].includes(field) || field.endsWith('.domain') || field.endsWith('.value')) {
    return valueOrJsonOrNumber(trimmed);
  }
  return trimmed;
}

function splitValues(value) {
  return value ? value.split(',').map(part => part.trim()).filter(Boolean) : [];
}

function valueOrJsonOrNumber(value) {
  if (value === '') return '';
  if (value.startsWith('{') || value.startsWith('[')) {
    try { return JSON.parse(value); } catch { return value; }
  }
  return valueOrNumber(value);
}

function valueOrNumber(value) {
  if (value === '') return '';
  const asNumber = Number(value);
  return Number.isFinite(asNumber) && String(asNumber) === String(value).trim() ? asNumber : value;
}

function numberOrNull(value) {
  if (String(value).trim() === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function inputValue(value) {
  if (value === undefined || value === null) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function displayCompact(value) {
  if (value === undefined || value === null || value === '') return '';
  if (typeof value === 'object') return value.nilReason ? `nil:${value.nilReason}` : JSON.stringify(value);
  return String(value);
}



function openNewRecordDialog() {
  const modal = $('newRecordModal');
  if (!modal) return;
  $('newRecordIdInput').value = '';
  $('newRecordTitleInput').value = '';
  setSelectValue($('newRecordWmoRegionSelect'), '');
  $('newRecordBeginInput').value = '';
  $('newRecordEndInput').value = '';
  $('newRecordLonInput').value = '';
  $('newRecordLatInput').value = '';
  $('newRecordElevInput').value = '';
  const result = $('newRecordResult');
  if (result) {
    result.className = 'validation empty';
    result.textContent = 'Enter at least a facility id and title.';
  }
  populateStaticVocabularySelects(modal);
  modal.showModal();
  window.setTimeout(() => $('newRecordIdInput')?.focus(), 0);
}

function newRecordInputValue(id) {
  return String($(id)?.value ?? '').trim();
}

function createNewRecordTemplateFromDialog() {
  const facilityId = newRecordInputValue('newRecordIdInput');
  const title = newRecordInputValue('newRecordTitleInput');
  const result = $('newRecordResult');
  if (!facilityId) {
    if (result) {
      result.className = 'validation invalid';
      result.textContent = 'Facility id is required for a new record.';
    }
    return null;
  }
  if (!title) {
    if (result) {
      result.className = 'validation invalid';
      result.textContent = 'Title is required for a new record.';
    }
    return null;
  }

  const begin = newRecordInputValue('newRecordBeginInput') || '..';
  const end = newRecordInputValue('newRecordEndInput') || '..';
  const lon = numberOrNull(newRecordInputValue('newRecordLonInput'));
  const lat = numberOrNull(newRecordInputValue('newRecordLatInput'));
  const elev = numberOrNull(newRecordInputValue('newRecordElevInput'));
  const hasPoint = lon !== null && lat !== null;
  const coordinates = hasPoint ? (elev === null ? [lon, lat] : [lon, lat, elev]) : null;
  const wmoRegion = newRecordInputValue('newRecordWmoRegionSelect');

  const record = {
    type: 'Feature',
    id: facilityId,
    conformsTo: ['http://wigos.wmo.int/spec/wmdr/2/conf/core'],
    geometry: hasPoint ? { type: 'Point', coordinates } : null,
    time: { interval: [begin, end], resolution: 'P1D' },
    properties: {
      type: 'facility',
      title,
      observationSeries: [],
      instruments: [],
      contacts: [],
      schedules: [],
    },
  };
  if (wmoRegion) record.properties.wmoRegion = wmoRegion;
  if (hasPoint) {
    record.temporalGeometry = {
      type: 'MovingPoint',
      coordinates: [coordinates],
      dates: [begin],
      methods: [[]],
    };
  }
  return record;
}

async function createNewRecordFromDialog() {
  const record = createNewRecordTemplateFromDialog();
  if (!record) return;
  const result = $('newRecordResult');
  if (result) {
    result.className = 'validation empty';
    result.textContent = 'Creating facility…';
  }
  try {
    await loadRecord(record, `${safeFileNamePart(record.id)}.json`);
    $('newRecordModal').close();
  } catch (error) {
    if (result) {
      result.className = 'validation invalid';
      result.textContent = error.message;
    } else {
      alert(error.message);
    }
  }
}

function defaultSaveFileName() {
  const base = state.record?.id || 'record';
  return `${safeFileNamePart(base)}.json`;
}

function safeFileNamePart(value) {
  return String(value || 'record').replace(/[^A-Za-z0-9_.-]+/g, '_').replace(/^[._]+|[._]+$/g, '') || 'record';
}

function openSaveDialog() {
  if (!state.record) return;
  syncFacilityForm();
  syncItemForms();
  $('saveLocationInput').value = state.saveLocation || 'data/records';
  $('saveFileNameInput').value = state.sourceFilename || defaultSaveFileName();
  const result = $('saveResult');
  result.className = 'validation empty';
  result.textContent = 'Ready to save.';
  $('saveModal').showModal();
}

async function saveAsFromDialog() {
  if (!state.record) return;
  syncFacilityForm();
  syncItemForms();
  const location = $('saveLocationInput').value.trim() || 'data/records';
  const filename = $('saveFileNameInput').value.trim() || defaultSaveFileName();
  const resultPanel = $('saveResult');
  resultPanel.className = 'validation empty';
  resultPanel.textContent = 'Saving…';
  try {
    const result = await api(`/api/records/${encodeURIComponent(state.recordId || state.record.id)}/save-as`, {
      method: 'POST',
      body: JSON.stringify({ record: state.record, location, filename }),
    });
    state.record = result.record;
    state.recordId = result.id;
    state.validation = result.validation;
    state.sourceFilename = result.filename || filename;
    state.saveLocation = result.location || location;
    renderAll();
    await refreshSavedRecords(result.id || state.recordId);
    resultPanel.className = 'validation valid save-success';
    resultPanel.innerHTML = `Saved to <code>${escapeHtml(result.saved_as || filename)}</code>.`;
  } catch (error) {
    resultPanel.className = 'validation invalid';
    resultPanel.textContent = error.message;
  }
}

function configurationsSectionJson() {
  return asArray(props().observationSeries).map((obs, index) => ({
    observationSeries: entityId(obs) || index,
    observingConfigurations: asArray(obs.observingConfigurations),
  }));
}

function applyConfigurationsSectionJson(value) {
  const entries = ensureArray(value, 'observing configurations');
  const series = asArray(props().observationSeries);
  entries.forEach((entry, index) => {
    const targetIndex = findObservationSeriesIndexForConfigurationEntry(entry, index);
    if (targetIndex >= 0 && series[targetIndex]) {
      series[targetIndex].observingConfigurations = ensureArray(entry.observingConfigurations ?? [], 'observingConfigurations');
    }
  });
}

function findObservationSeriesIndexForConfigurationEntry(entry, fallbackIndex) {
  const key = entry?.observationSeries;
  if (key) {
    const found = asArray(props().observationSeries).findIndex(obs => entityId(obs) === key);
    if (found >= 0) return found;
  }
  return Number.isInteger(fallbackIndex) ? fallbackIndex : -1;
}

function uniqueUid(prefix, existingUids) {
  let next = existingUids.size + 1;
  let uid = `${prefix}:new-${next}`;
  while (existingUids.has(uid)) {
    next += 1;
    uid = `${prefix}:new-${next}`;
  }
  return uid;
}

function openOwnerContactModal() {
  syncFacilityForm();
  syncItemForms();
  const contacts = props().contacts ??= [];
  const owners = contactsWithRole('owner');
  const select = $('ownerContactSelect');
  if (!select) return;
  $('ownerContactModalTitle').textContent = owners.length === 1 ? 'Edit owner contact' : (owners.length > 1 ? 'Edit owner contacts' : 'Add owner contact');
  $('ownerContactModalHelp').textContent = owners.length
    ? 'Review the current owner contact, assign another existing contact as owner, or create a new owner contact.'
    : 'No owner contact is assigned. Choose an existing contact or create a new contact with role owner.';
  select.innerHTML = contacts.map((contact, index) => {
    const selected = owners.length === 1 && owners[0].index === index ? ' selected' : '';
    const roles = asArray(contact.roles).join(', ');
    const roleText = roles ? ` (${roles})` : '';
    return `<option value="${index}"${selected}>${escapeHtml(contactLabel(contact, index) + roleText)}</option>`;
  }).join('') || '<option value="">No contacts available</option>';
  $('ownerContactJumpBtn').disabled = contacts.length === 0;
  $('ownerContactAssignBtn').disabled = contacts.length === 0;
  $('ownerContactModal').showModal();
}

function selectedOwnerContactIndex() {
  const value = $('ownerContactSelect')?.value;
  if (value === undefined || value === '') return -1;
  const index = Number(value);
  return Number.isInteger(index) ? index : -1;
}

function ensureContactRole(contact, role) {
  contact.roles = asArray(contact.roles).map(String).filter(Boolean);
  if (!contact.roles.map(normalizeRole).includes(normalizeRole(role))) {
    contact.roles.push(role);
  }
}

function assignSelectedOwnerContact() {
  const index = selectedOwnerContactIndex();
  const contact = props().contacts?.[index];
  if (!contact) return;
  ensureContactRole(contact, 'owner');
  $('ownerContactModal').close();
  state.pendingScrollTarget = itemDomId('contact', index);
  renderAll();
}

function jumpToSelectedOwnerContact() {
  const index = selectedOwnerContactIndex();
  if (index < 0) return;
  $('ownerContactModal').close();
  scrollToItem(itemDomId('contact', index));
}

function addOwnerContact() {
  syncFacilityForm();
  syncItemForms();
  const contacts = props().contacts ??= [];
  const uid = uniqueUid('contact', new Set(contacts.map(entityId).filter(Boolean)));
  contacts.push({
    identifier: uid,
    name: '',
    organization: '',
    roles: ['owner'],
    emails: [],
    phones: [],
  });
  $('ownerContactModal')?.close();
  state.pendingScrollTarget = itemDomId('contact', contacts.length - 1);
  renderAll();
}

function addInstrumentForObservationSeries(seriesIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observationSeries?.[seriesIndex];
  if (!obs) return;

  const instruments = props().instruments ??= [];
  const uid = uniqueUid('instrument', new Set(instruments.map(entityId).filter(Boolean)));
  const configs = obs.observingConfigurations ??= [];
  let configIndex = configs.findIndex(config => !config?.instrument);
  if (configIndex < 0) {
    configs.push({
      time: { interval: ['..', '..'] },
      observingMethod: { nilReason: 'unknown' },
    });
    configIndex = configs.length - 1;
  }
  const config = configs[configIndex];
  config.instrument = uid;

  const observingMethods = [];
  if (config.observingMethod !== undefined && config.observingMethod !== '' && typeof config.observingMethod !== 'object') {
    observingMethods.push(config.observingMethod);
  }
  instruments.push({
    id: uid,
    title: '',
    manufacturer: '',
    model: '',
    observingMethods,
  });

  state.pendingScrollTarget = itemDomId('instrument', instruments.length - 1);
  renderAll();
}

function addItem(kind) {
  syncFacilityForm();
  syncItemForms();
  const section = getSectionForKind(kind);
  const next = section.length + 1;
  if (kind === 'observationSeries') section.push({
    id: `observationSeries:new-${next}`,
    observedProperty: '',
    observedFeature: { domain: '' },
    applicationAreas: [],
    observingConfigurations: [],
  });
  if (kind === 'instrument') section.push({ id: uniqueUid('instrument', new Set(section.map(entityId).filter(Boolean))) });
  if (kind === 'contact') section.push({ identifier: uniqueUid('contact', new Set(section.map(entityId).filter(Boolean))), roles: [], emails: [] });
  renderAll();
}

function addConfiguration(seriesIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observationSeries?.[seriesIndex];
  if (!obs) return;
  obs.observingConfigurations ??= [];
  obs.observingConfigurations.push({
    time: { interval: ['..', '..'] },
    observingMethod: { nilReason: 'unknown' },
  });
  state.pendingScrollTarget = configurationDomId(seriesIndex, obs.observingConfigurations.length - 1);
  renderAll();
}

function deleteItem(kind, index) {
  syncFacilityForm();
  syncItemForms();
  getSectionForKind(kind).splice(index, 1);
  renderAll();
}

function deleteConfiguration(seriesIndex, configIndex) {
  syncFacilityForm();
  syncItemForms();
  props().observationSeries?.[seriesIndex]?.observingConfigurations?.splice(configIndex, 1);
  renderAll();
}

function openModal(target, title, value) {
  state.modalTarget = target;
  $('modalTitle').textContent = title;
  $('modalJson').value = pretty(value);
  $('jsonModal').showModal();
}

function focusSection(sectionId, options = {}) {
  const { scroll = true } = options;
  TOP_LEVEL_SECTION_IDS.forEach(id => {
    const section = $(id);
    if (section) section.open = id === sectionId;
  });
  const section = $(sectionId);
  if (section && scroll) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function scrollToItem(targetId) {
  const target = $(targetId);
  if (!target) return;
  const topLevelDetails = target.matches('details.card') ? target : target.closest('details.card');
  if (topLevelDetails?.id) focusSection(topLevelDetails.id, { scroll: false });
  else {
    const details = target.closest('details');
    if (details) details.open = true;
  }
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  target.classList.add('flash');
  window.setTimeout(() => target.classList.remove('flash'), 1600);
}

function refreshRelationshipViews() {
  renderFacility();
  renderObservationSeries();
  renderConfigurationsOverview();
  renderInstruments();
  renderContacts();
  $('recordRaw').value = pretty(state.record);
}

function applyModal() {
  const value = parseJson($('modalJson').value, $('modalTitle').textContent);
  const target = state.modalTarget;
  if (target === 'facilityRaw') {
    Object.assign(state.record, pick(value, ['id', 'geometry', 'temporalGeometry', 'time', 'conformsTo']));
    Object.assign(props(), omit(value.properties ? value.properties : value, ['observationSeries', 'instruments', 'contacts', 'schedules']));
  } else if (target === 'observationSeriesRaw') props().observationSeries = ensureArray(value, 'observationSeries');
  else if (target === 'configurationsRaw') applyConfigurationsSectionJson(value);
  else if (target === 'instrumentsRaw') props().instruments = ensureArray(value, 'instruments');
  else if (target === 'contactsRaw') props().contacts = ensureArray(value, 'contacts');
  else if (target?.startsWith('item:')) {
    const [, kind, indexText] = target.split(':');
    getSectionForKind(kind)[Number(indexText)] = value;
  } else if (target?.startsWith('config:')) {
    const [, seriesText, configText] = target.split(':');
    props().observationSeries[Number(seriesText)].observingConfigurations[Number(configText)] = value;
  }
  $('jsonModal').close();
  renderAll();
}

function ensureArray(value, label) {
  if (!Array.isArray(value)) throw new Error(`${label} JSON must be an array.`);
  return value;
}

function pick(obj, keys) {
  const out = {};
  for (const key of keys) if (key in obj) out[key] = obj[key];
  return out;
}

function omit(obj, keys) {
  const out = { ...obj };
  for (const key of keys) delete out[key];
  return out;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function escapeAttr(value) {
  return escapeHtml(value);
}

loadVocabularies();
refreshSavedRecords();

$('fileInput').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const form = new FormData();
    form.append('file', file);
    const result = await api('/api/records', { method: 'POST', body: form });
    acceptLoadedRecord(result, file.name);
    await refreshSavedRecords(result.id);
  } catch (error) {
    alert(error.message);
  }
});

$('loadPasteBtn').addEventListener('click', async () => {
  try {
    await loadRecord(parseJson($('pasteInput').value, 'Pasted record'));
  } catch (error) {
    alert(error.message);
  }
});

$('loadExampleBtn').addEventListener('click', () => loadRecord(exampleRecord).catch(error => alert(error.message)));
$('newRecordBtn').addEventListener('click', () => openNewRecordDialog());
$('refreshSavedBtn').addEventListener('click', () => refreshSavedRecords());
$('openSavedBtn').addEventListener('click', () => openSavedRecord());
$('saveBtn').addEventListener('click', () => openSaveDialog());
$('validateBtn').addEventListener('click', () => validateRecord().catch(error => alert(error.message)));
$('applyRawBtn').addEventListener('click', () => {
  try {
    state.record = parseJson($('recordRaw').value, 'Full record');
    state.recordId = state.record.id;
    renderAll();
  } catch (error) {
    alert(error.message);
  }
});
$('addObservationBtn').addEventListener('click', () => addItem('observationSeries'));
$('addInstrumentBtn').addEventListener('click', () => addItem('instrument'));
$('addContactBtn').addEventListener('click', () => addItem('contact'));
$('addTemporalGeometryBtn').addEventListener('click', () => addTemporalGeometryRow());
$('modalCancelBtn').addEventListener('click', () => $('jsonModal').close());
$('modalApplyBtn').addEventListener('click', () => {
  try { applyModal(); } catch (error) { alert(error.message); }
});
$('saveCancelBtn').addEventListener('click', () => $('saveModal').close());
$('saveConfirmBtn').addEventListener('click', () => saveAsFromDialog());
$('newRecordCancelBtn').addEventListener('click', () => $('newRecordModal').close());
$('newRecordCreateBtn').addEventListener('click', () => createNewRecordFromDialog());
$('ownerContactCancelBtn').addEventListener('click', () => $('ownerContactModal').close());
$('ownerContactAssignBtn').addEventListener('click', () => assignSelectedOwnerContact());
$('ownerContactJumpBtn').addEventListener('click', () => jumpToSelectedOwnerContact());
$('ownerContactNewBtn').addEventListener('click', () => addOwnerContact());

// Keep old development data from throwing if an old HTML is cached.
const oldAddDeployment = $('addDeploymentBtn');
if (oldAddDeployment) oldAddDeployment.addEventListener('click', () => alert('WMDR2 v0.3.x no longer has facility-level deployments. Use observingConfigurations instead.'));

document.body.addEventListener('click', event => {
  const summaryModalButton = event.target.closest('summary [data-open-modal]');
  if (summaryModalButton) {
    event.preventDefault();
    event.stopPropagation();
  }

  const xref = event.target.closest('[data-scroll-target]');
  if (xref) {
    event.preventDefault();
    scrollToItem(xref.dataset.scrollTarget);
    return;
  }

  const ownerContactButton = event.target.closest('[data-open-owner-contact]');
  if (ownerContactButton) {
    openOwnerContactModal();
    return;
  }

  const addObsInstrument = event.target.closest('[data-add-observation-instrument]');
  if (addObsInstrument) {
    addInstrumentForObservationSeries(Number(addObsInstrument.dataset.addObservationInstrument));
    return;
  }

  const addConfig = event.target.closest('[data-add-config]');
  if (addConfig) {
    addConfiguration(Number(addConfig.dataset.addConfig));
    return;
  }

  const selectTemporal = event.target.closest('[data-select-temporal-geometry]');
  if (selectTemporal) {
    syncFacilityForm();
    state.selectedTemporalGeometryIndex = Number(selectTemporal.dataset.selectTemporalGeometry);
    renderTemporalGeometryHistory();
    return;
  }

  const deleteTemporal = event.target.closest('[data-delete-temporal-geometry]');
  if (deleteTemporal) {
    deleteTemporalGeometryRow(Number(deleteTemporal.dataset.deleteTemporalGeometry));
    return;
  }

  const open = event.target.closest('[data-open-modal]');
  if (open) {
    if (!state.record) return;
    syncFacilityForm();
    syncItemForms();
    const target = open.dataset.openModal;
    const mapping = {
      facilityRaw: ['Facility JSON', { id: state.record.id, geometry: state.record.geometry, temporalGeometry: state.record.temporalGeometry, time: state.record.time, conformsTo: state.record.conformsTo, properties: omit(props(), ['observationSeries', 'instruments', 'contacts', 'schedules']) }],
      observationSeriesRaw: ['ObservationSeries JSON', props().observationSeries ?? []],
      configurationsRaw: ['Observing configurations JSON', configurationsSectionJson()],
      instrumentsRaw: ['Instruments JSON', props().instruments ?? []],
      contactsRaw: ['Contacts JSON', props().contacts ?? []],
    };
    if (!mapping[target]) return;
    openModal(target, mapping[target][0], mapping[target][1]);
  }

  const deleteButton = event.target.closest('[data-delete-item]');
  if (deleteButton) deleteItem(deleteButton.dataset.deleteItem, Number(deleteButton.dataset.index));

  const deleteConfigButton = event.target.closest('[data-delete-config]');
  if (deleteConfigButton) {
    const [seriesIndex, configIndex] = deleteConfigButton.dataset.deleteConfig.split(':').map(Number);
    deleteConfiguration(seriesIndex, configIndex);
  }

  const jsonButton = event.target.closest('[data-json-item]');
  if (jsonButton) {
    syncFacilityForm();
    syncItemForms();
    const kind = jsonButton.dataset.jsonItem;
    const index = Number(jsonButton.dataset.index);
    openModal(`item:${kind}:${index}`, `${kind} JSON`, getSectionForKind(kind)[index]);
  }

  const jsonConfigButton = event.target.closest('[data-json-config]');
  if (jsonConfigButton) {
    syncFacilityForm();
    syncItemForms();
    const [seriesIndex, configIndex] = jsonConfigButton.dataset.jsonConfig.split(':').map(Number);
    openModal(`config:${seriesIndex}:${configIndex}`, 'ObservingConfiguration JSON', props().observationSeries[seriesIndex].observingConfigurations[configIndex]);
  }
});

document.body.addEventListener('input', event => {
  const changedByCalendar = applyDatePickerValue(event);
  if (!state.record) return;
  if (!changedByCalendar && (event.target.matches?.('input[data-date-text], input[data-field="time.interval.0"], input[data-field="time.interval.1"]'))) {
    syncDatePickerFromTextInput(event.target);
  }
  if (event.target.closest('#facilityForm') || event.target.closest('[data-kind]')) {
    syncFacilityForm();
    syncItemForms();
    $('recordRaw').value = pretty(state.record);
    $('recordTitle').textContent = props().title || state.record.id || 'Untitled facility';
    $('recordId').textContent = state.record.id || 'No id';
    $('downloadLink').href = appUrl(`api/records/${encodeURIComponent(state.record.id)}/download`);
  }
});

document.body.addEventListener('change', event => {
  const vocabAppend = event.target.closest?.('select[data-add-vocab-target]');
  if (vocabAppend) {
    appendVocabularyChoice(vocabAppend);
    return;
  }

  const changedByCalendar = applyDatePickerValue(event);
  if (!state.record) return;
  if (!changedByCalendar && (event.target.matches?.('input[data-date-text], input[data-field="time.interval.0"], input[data-field="time.interval.1"]'))) {
    syncDatePickerFromTextInput(event.target);
  }
  const field = event.target?.dataset?.field;
  if (!field) return;

  syncFacilityForm();
  syncItemForms();
  $('recordRaw').value = pretty(state.record);
  $('recordTitle').textContent = props().title || state.record.id || 'Untitled facility';
  $('recordId').textContent = state.record.id || 'No id';
  $('downloadLink').href = appUrl(`api/records/${encodeURIComponent(state.record.id)}/download`);

  if (changedByCalendar || ['instrument', 'id', 'uid', 'identifier', 'roles', 'name', 'organization', 'time.interval.0', 'time.interval.1', 'observingMethod', 'observedProperty', 'observedGeometry', 'date', 'lon', 'lat', 'elev', 'methods'].includes(field)) {
    refreshRelationshipViews();
  }
});
