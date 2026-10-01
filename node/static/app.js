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
  'proceduresSection',
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
  const currentValues = asArray(values).map(inputValue).filter(Boolean);
  const value = currentValues.join(', ');
  const selectHtml = selectOptionsHtml(vocabularyName, '', { blankLabel: `Add ${label || 'choice'}…` });
  const chips = currentValues.length
    ? currentValues.map(item => `
        <span class="value-chip">
          <span>${escapeHtml(item)}</span>
          <button type="button" class="chip-remove" data-remove-vocab-target="${escapeAttr(field)}" data-remove-vocab-value="${escapeAttr(item)}" aria-label="Remove ${escapeAttr(item)}">×</button>
        </span>`).join('')
    : '<span class="xref-empty">No values selected</span>';
  return `
    <div class="multi-vocab chip-picker" data-multi-vocab="${escapeAttr(field)}">
      <input type="hidden" data-field="${escapeAttr(field)}" value="${escapeAttr(value)}" />
      <div class="multi-vocab-values" aria-label="Selected ${escapeAttr(label || field)} values">
        ${chips}
        <button type="button" class="chip-add-button" data-toggle-add-vocab-target="${escapeAttr(field)}" aria-label="Add ${escapeAttr(label || field)} from list" title="Add from list">+</button>
        <select class="vocab-select add-vocab-select chip-add-select" data-add-vocab-target="${escapeAttr(field)}" aria-label="Add ${escapeAttr(label || field)} from vocabulary" hidden>${selectHtml}</select>
      </div>
    </div>`;
}


function multiTextInputHtml(field, values, label) {
  const currentValues = asArray(values).map(inputValue).filter(Boolean);
  const value = currentValues.join(', ');
  const chips = currentValues.length
    ? currentValues.map(item => `
        <span class="value-chip">
          <span>${escapeHtml(item)}</span>
          <button type="button" class="chip-remove" data-remove-text-target="${escapeAttr(field)}" data-remove-text-value="${escapeAttr(item)}" aria-label="Remove ${escapeAttr(item)}">×</button>
        </span>`).join('')
    : '<span class="xref-empty">No values selected</span>';
  return `
    <div class="multi-vocab multi-text" data-multi-text="${escapeAttr(field)}">
      <input type="hidden" data-field="${escapeAttr(field)}" value="${escapeAttr(value)}" />
      <div class="multi-vocab-values" aria-label="Selected ${escapeAttr(label || field)} values">${chips}</div>
      <input class="inline-add-input" data-add-text-target="${escapeAttr(field)}" placeholder="Add ${escapeAttr(label || 'value')} and press Enter" />
    </div>`;
}

function appendTextChoice(input) {
  const value = String(input.value ?? '').trim();
  if (!value) return false;
  const targetField = input.dataset.addTextTarget;
  const scope = input.closest('[data-kind], [data-procedure-kind], [data-schedule-index], #facilityForm') || document;
  const hidden = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
  if (!hidden) return false;
  const values = splitValues(hidden.value);
  if (!values.includes(value)) {
    values.push(value);
    hidden.value = values.join(', ');
    hidden.dispatchEvent(new Event('input', { bubbles: true }));
  }
  input.value = '';
  return true;
}

function removeTextChoice(button) {
  const targetField = button.dataset.removeTextTarget;
  const value = button.dataset.removeTextValue;
  if (!targetField || !value) return false;
  const scope = button.closest('[data-kind], [data-procedure-kind], [data-schedule-index], #facilityForm') || document;
  const input = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
  if (!input) return false;
  input.value = splitValues(input.value).filter(item => item !== value).join(', ');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}

function scheduleReferenceInputHtml(field, values, label) {
  const currentValues = asArray(values).map(inputValue).filter(Boolean);
  const value = currentValues.join(', ');
  const schedules = asArray(props().schedules).map((schedule, index) => ({ uid: inputValue(schedule.uid), index })).filter(item => item.uid);
  const scheduleIndex = new Map(schedules.map(item => [item.uid, item.index]));
  const selectOptions = ['<option value="">Add schedule ref…</option>']
    .concat(schedules.map(item => `<option value="${escapeAttr(item.uid)}">${escapeHtml(item.uid)}</option>`))
    .join('');
  const chips = currentValues.length
    ? currentValues.map(item => {
        const index = scheduleIndex.get(item);
        const ref = index === undefined
          ? `<span class="xref missing" title="No matching reusable schedule found">${escapeHtml(item)} ⚠</span>`
          : `<a class="xref" href="#schedule-${index}" data-scroll-target="schedule-${index}" title="Go to reusable schedule ${escapeAttr(item)}">${escapeHtml(item)}</a>`;
        return `
          <span class="value-chip schedule-ref-chip">
            ${ref}
            <button type="button" class="chip-remove" data-remove-ref-target="${escapeAttr(field)}" data-remove-ref-value="${escapeAttr(item)}" aria-label="Remove ${escapeAttr(item)}">×</button>
          </span>`;
      }).join('')
    : '<span class="xref-empty">No schedule references selected</span>';
  return `
    <div class="multi-vocab schedule-ref chip-picker" data-schedule-ref="${escapeAttr(field)}">
      <input type="hidden" data-field="${escapeAttr(field)}" value="${escapeAttr(value)}" />
      <div class="multi-vocab-values" aria-label="Selected ${escapeAttr(label || field)} references">
        ${chips}
        <button type="button" class="chip-add-button" data-toggle-add-ref-target="${escapeAttr(field)}" aria-label="Add ${escapeAttr(label || field)} reference" title="Add schedule reference">+</button>
        <select class="vocab-select add-ref-select chip-add-select" data-add-ref-target="${escapeAttr(field)}" aria-label="Add ${escapeAttr(label || field)} reference" hidden>${selectOptions}</select>
      </div>
    </div>`;
}

function appendReferenceChoice(select) {
  const value = select.value;
  if (!value) return false;
  const targetField = select.dataset.addRefTarget;
  const scope = select.closest('[data-procedure-kind], [data-schedule-index], [data-kind], #facilityForm') || document;
  const input = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
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

function removeReferenceChoice(button) {
  const targetField = button.dataset.removeRefTarget;
  const value = button.dataset.removeRefValue;
  if (!targetField || !value) return false;
  const scope = button.closest('[data-procedure-kind], [data-schedule-index], [data-kind], #facilityForm') || document;
  const input = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
  if (!input) return false;
  input.value = splitValues(input.value).filter(item => item !== value).join(', ');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
}

function showChipAddSelect(button, selector) {
  const picker = button.closest('.chip-picker');
  if (!picker) return false;
  const select = picker.querySelector(selector);
  if (!select) return false;
  button.hidden = true;
  select.hidden = false;
  select.value = '';
  select.focus();
  if (typeof select.showPicker === 'function') {
    try { select.showPicker(); } catch (_error) { /* Some browsers only allow showPicker in narrower user-activation cases. */ }
  }
  return true;
}

function hideChipAddSelect(select) {
  if (!select?.matches?.('.chip-add-select')) return false;
  const picker = select.closest('.chip-picker');
  select.hidden = true;
  select.value = '';
  const button = picker?.querySelector('.chip-add-button');
  if (button) button.hidden = false;
  return true;
}

function appendVocabularyChoice(select) {
  const value = select.value;
  if (!value) return false;
  const targetField = select.dataset.addVocabTarget;
  const scope = select.closest('[data-kind], #facilityForm') || document;
  const input = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
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

function removeVocabularyChoice(button) {
  const targetField = button.dataset.removeVocabTarget;
  const value = button.dataset.removeVocabValue;
  if (!targetField || !value) return false;
  const scope = button.closest('[data-kind], #facilityForm') || document;
  const input = scope.querySelector(`input[type="hidden"][data-field="${cssAttrValue(targetField)}"]`);
  if (!input) return false;
  input.value = splitValues(input.value).filter(item => item !== value).join(', ');
  input.dispatchEvent(new Event('input', { bubbles: true }));
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
    description: 'Example facility for WIGOS Node PoC.',
    facilityType: { id: 'landFixed', url: 'http://codes.wmo.int/wmdr/FacilityType/landFixed' },
    wmoRegion: { id: 'europe', url: 'http://codes.wmo.int/wmdr/WMORegion/europe' },
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
    territories: [{ dates: ['2000-08-17', '..'], territory: { id: 'CHE', url: 'http://codes.wmo.int/wmdr/TerritoryName/CHE' } }],
    environment: [{ time: { interval: ['2000-08-17', '..'] }, surfaceCover: { scheme: { id: 'igbp', url: 'http://codes.wmo.int/wmdr/SurfaceCoverClassification/igbp' }, value: { id: 'grassland', url: 'http://codes.wmo.int/wmdr/SurfaceCoverIGBP/grassland' } }, surfaceRoughness: { id: 'open', url: 'http://codes.wmo.int/wmdr/SurfaceRoughnessDavenport/open' }, topographyBathymetry: { localTopography: { id: 'flat', url: 'http://codes.wmo.int/wmdr/LocalTopography/flat' } } }],
    observations: [
      {
        id: '12006-point',
        title: 'Horizontal wind speed at specified distance from reference surface',
        observedProperty: { id: '12006', url: 'http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/12006' },
        observedFeature: { domain: { id: 'atmosphere', url: 'http://codes.wmo.int/wmdr/Domain/atmosphere' }, domainFeature: 'near-surface-air', featureName: '10 m air' },
        observedGeometry: { id: 'point', url: 'http://codes.wmo.int/wmdr/Geometry/point' },
        programAffiliations: [{ programAffiliation: { id: 'GOSGeneral', url: 'http://codes.wmo.int/wmdr/ProgramAffiliation/GOSGeneral' } }],
        applicationAreas: [{ id: 'weatherForecasting', url: 'http://codes.wmo.int/wmdr/ApplicationArea/weatherForecasting' }],
        configurations: [
          {
            id: '12006-point-configuration-1',
            time: { interval: ['2020-01-01', '..'] },
            verticalDistance: { distances: [10], unit: { id: 'm', url: 'http://codes.wmo.int/wmdr/unit/m' }, referenceSurface: { id: 'localGround', url: 'http://codes.wmo.int/wmdr/ReferenceSurfaceType/localGround' } },
            observingMethod: { id: '266', url: 'http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/266' },
            sourceOfObservation: { id: 'automaticReading', url: 'http://codes.wmo.int/wmdr/SourceOfObservation/automaticReading' },
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
        observingMethods: [{ id: '266', url: 'http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/266' }],
      },
    ],
    schedules: [],
  },
};

function props() {
  state.record.properties ??= { type: 'facility', title: '' };
  if (!Array.isArray(state.record.properties.observations) && Array.isArray(state.record.properties.observationSeries)) {
    state.record.properties.observations = state.record.properties.observationSeries;
    delete state.record.properties.observationSeries;
  }
  state.record.properties.observations ??= [];
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
  renderObservations();
  renderConfigurationsOverview();
  renderProceduresSchedules();
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
  clearValidationMarkers();
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
  setStatus(valid ? (warnings.length ? 'Valid with warnings' : 'Valid WMDR2 v0.4.0') : 'Invalid WMDR2 v0.4.0', valid ? (warnings.length ? 'warning' : 'valid') : 'invalid');
  const parts = [];
  parts.push(`<strong>${valid ? 'Structurally valid.' : `${errors.length} error(s).`}</strong>`);
  if (errors.length) {
    parts.push('<p class="muted">Click an error path to open the relevant section. Matching fields are highlighted in the form.</p>');
    parts.push('<h3>Errors</h3><ul>' + errors.map(e => validationMessageHtml(e, 'error')).join('') + '</ul>');
  }
  if (warnings.length) {
    parts.push('<h3>Warnings</h3><ul>' + warnings.map(w => validationMessageHtml(w, 'warning')).join('') + '</ul>');
  }
  panel.innerHTML = parts.join('');
  applyValidationMarkers(errors);
}

function validationMessageHtml(message, kind) {
  const target = validationTargetForPath(message.path);
  const pathHtml = `<code>${escapeHtml(message.path)}</code>`;
  const path = target?.scrollTarget
    ? `<a class="validation-jump ${escapeAttr(kind)}" href="#${escapeAttr(target.scrollTarget)}" data-scroll-target="${escapeAttr(target.scrollTarget)}">${pathHtml}</a>`
    : pathHtml;
  return `<li>${path}: ${escapeHtml(message.message)}</li>`;
}

function clearValidationMarkers() {
  document.querySelectorAll('.field-error, .field-error-label, .item-error').forEach(element => {
    element.classList.remove('field-error', 'field-error-label', 'item-error');
    if (element instanceof HTMLElement) {
      element.removeAttribute('aria-invalid');
      if (element.dataset.validationTitle) {
        element.title = element.dataset.validationTitle;
        delete element.dataset.validationTitle;
      }
    }
  });
}

function applyValidationMarkers(errors) {
  asArray(errors).forEach(error => {
    const target = validationTargetForPath(error.path);
    if (!target) return;
    const field = target.field;
    const item = target.item;
    if (item) item.classList.add('item-error');
    if (!field) return;
    const visible = field.type === 'hidden'
      ? field.closest('.multi-vocab') || field
      : field;
    visible.classList.add('field-error');
    visible.setAttribute('aria-invalid', 'true');
    if (visible instanceof HTMLElement) {
      visible.dataset.validationTitle = visible.title || '';
      visible.title = error.message;
    }
    const label = visible.closest('label');
    if (label) label.classList.add('field-error-label');
  });
}

function validationTargetForPath(path) {
  if (!path || typeof path !== 'string') return null;
  if (path === '$.id') return sectionFieldTarget('facilitySection', '#facilityForm [name="id"]');
  if (path === '$.properties.title') return sectionFieldTarget('facilitySection', '#facilityForm [name="title"]');
  if (path === '$.properties.wmoRegion') return sectionFieldTarget('facilitySection', '#facilityForm [name="wmoRegion"]');
  if (path === '$.properties.facilityType') return sectionFieldTarget('facilitySection', '#facilityForm [name="facilityType"]');
  if (path === '$.time.interval[0]') return sectionFieldTarget('facilitySection', '#facilityForm [name="begin"]');
  if (path === '$.time.interval[1]') return sectionFieldTarget('facilitySection', '#facilityForm [name="end"]');
  if (path.startsWith('$.temporalGeometry') || path.startsWith('$.geometry')) {
    return sectionFieldTarget('facilitySection', '#temporalGeometryEditor input, #facilityForm [name="id"]');
  }

  let match = path.match(/^\$\.properties\.observations\[(\d+)\](?:\.(.*))?$/);
  if (match) {
    const seriesIndex = Number(match[1]);
    const rest = match[2] || '';
    if (rest.startsWith('configurations[')) {
      const configMatch = rest.match(/^configurations\[(\d+)\](?:\.(.*))?$/);
      const configIndex = configMatch ? Number(configMatch[1]) : 0;
      const configPath = configMatch?.[2] || '';
      return configurationValidationTarget(seriesIndex, configIndex, configPath);
    }
    if (rest.startsWith('observingProcedures[') || rest.startsWith('reportingProcedures[')) {
      const procMatch = rest.match(/^(observingProcedures|reportingProcedures)\[(\d+)\](?:\.(.*))?$/);
      const arrayName = procMatch?.[1] || 'observingProcedures';
      const procIndex = procMatch ? Number(procMatch[2]) : 0;
      const procPath = procMatch?.[3] || '';
      return procedureValidationTarget(seriesIndex, arrayName, procIndex, procPath);
    }
    return observationValidationTarget(seriesIndex, rest);
  }


  match = path.match(/^\$\.properties\.territories\[(\d+)\](?:\.(.*))?$/);
  if (match) return facilityCollectionValidationTarget('territory', Number(match[1]), validationFieldFromPath(match[2] || ''));

  match = path.match(/^\$\.properties\.environment\[(\d+)\](?:\.(.*))?$/);
  if (match) return facilityCollectionValidationTarget('environment', Number(match[1]), validationFieldFromPath(match[2] || ''));

  match = path.match(/^\$\.properties\.schedules\[(\d+)\](?:\.(.*))?$/);
  if (match) return scheduleValidationTarget(Number(match[1]), validationFieldFromPath(match[2] || ''));

  match = path.match(/^\$\.properties\.instruments\[(\d+)\](?:\.(.*))?$/);
  if (match) return itemValidationTarget('instrument', Number(match[1]), validationFieldFromPath(match[2] || ''));

  match = path.match(/^\$\.properties\.contacts\[(\d+)\](?:\.(.*))?$/);
  if (match) return itemValidationTarget('contact', Number(match[1]), validationFieldFromPath(match[2] || ''));

  return null;
}

function sectionFieldTarget(sectionId, fieldSelector) {
  const section = $(sectionId);
  return { scrollTarget: sectionId, item: section, field: fieldSelector ? document.querySelector(fieldSelector) : null };
}

function observationValidationTarget(index, path) {
  const itemId = itemDomId('observations', index);
  return itemValidationTarget('observations', index, validationFieldFromPath(path), itemId);
}

function configurationValidationTarget(seriesIndex, configIndex, path) {
  const itemId = configurationDomId(seriesIndex, configIndex);
  const item = $(itemId);
  const field = validationFieldFromPath(path);
  const form = item?.querySelector('[data-kind="observingConfiguration"]');
  return { scrollTarget: itemId, item, field: field ? form?.querySelector(`[data-field="${cssAttrValue(field)}"]`) : null };
}


function procedureValidationTarget(seriesIndex, arrayName, procIndex, fieldPath) {
  const domId = arrayName === 'observingProcedures'
    ? `observing-procedure-${seriesIndex}-${procIndex}`
    : `reporting-procedure-${seriesIndex}-${procIndex}`;
  const row = $(domId);
  return { scrollTarget: domId, item: row, field: row?.querySelector(`[data-field="${cssAttrValue(validationFieldFromPath(fieldPath))}"]`) || row?.querySelector('[data-field]') || null };
}

function scheduleValidationTarget(index, fieldPath) {
  const domId = `schedule-${index}`;
  const row = $(domId);
  return { scrollTarget: domId, item: row, field: row?.querySelector(`[data-field="${cssAttrValue(validationFieldFromPath(fieldPath))}"]`) || row?.querySelector('[data-field]') || null };
}
function facilityCollectionValidationTarget(kind, index, fieldPath) {
  const idMap = { territory: `territory-${index}`, environment: `environment-${index}` };
  const domId = idMap[kind] || `${kind}-${index}`;
  const row = $(domId);
  const field = validationFieldFromPath(fieldPath);
  return { scrollTarget: domId, item: row, field: field ? row?.querySelector(`[data-field="${cssAttrValue(field)}"]`) : row?.querySelector('[data-field]') || null };
}


function itemValidationTarget(kind, index, field, itemId = itemDomId(kind, index)) {
  const item = $(itemId);
  const form = item?.querySelector(`[data-kind="${cssAttrValue(kind)}"]`);
  return { scrollTarget: itemId, item, field: field ? form?.querySelector(`[data-field="${cssAttrValue(field)}"]`) : null };
}

function validationFieldFromPath(path) {
  if (!path) return '';
  const normalized = path.replace(/\[(\d+)\]/g, '');
  if (normalized === 'time' || normalized === 'time.interval') return 'time.interval.0';
  if (normalized === 'observedFeature') return 'observedFeature.domain';
  if (normalized === 'verticalDistance' || normalized === 'verticalDistance.distances') return 'verticalDistance.distances.0';
  if (normalized === 'surfaceCover') return 'surfaceCover.value';
  return normalized;
}

function renderFacility() {
  const form = $('facilityForm');
  const p = props();
  form.elements.id.value = state.record.id || '';
  form.elements.title.value = p.title || '';
  form.elements.description.value = p.description || '';
  setSelectValue(form.elements.wmoRegion, p.wmoRegion || '');
  setSelectValue(form.elements.facilityType, p.facilityType || '');
  form.elements.additionalTitles.value = asArray(p.additionalTitles).join(', ');
  form.elements.additionalIds.value = asArray(p.additionalIds).join(', ');
  form.elements.keywords.value = asArray(p.keywords).join(', ');
  form.elements.facilitySets.value = asArray(p.facilitySets).join(', ');
  const coords = state.record.geometry?.coordinates || [];
  form.elements.lon.value = coords[0] ?? '';
  form.elements.lat.value = coords[1] ?? '';
  form.elements.elev.value = coords[2] ?? '';
  const interval = state.record.time?.interval || [];
  form.elements.begin.value = isoDateOrEmpty(interval[0]);
  form.elements.end.value = isoDateOrEmpty(interval[1]);
  renderTemporalGeometryHistory();
  renderTerritoryHistory();
  renderEnvironmentHistory();
  renderFacilityLinks();
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
  p.facilityType = form.elements.facilityType.value.trim() || null;
  setOptionalStringArray(p, 'additionalTitles', form.elements.additionalTitles.value);
  setOptionalStringArray(p, 'additionalIds', form.elements.additionalIds.value);
  setOptionalStringArray(p, 'keywords', form.elements.keywords.value);
  setOptionalStringArray(p, 'facilitySets', form.elements.facilitySets.value);
  const lon = numberOrNull(form.elements.lon.value);
  const lat = numberOrNull(form.elements.lat.value);
  const elev = numberOrNull(form.elements.elev.value);
  if (lon !== null && lat !== null) {
    state.record.geometry = { type: 'Point', coordinates: elev === null ? [lon, lat] : [lon, lat, elev] };
  }
  syncTemporalGeometryForms();
  syncTerritoryForms();
  syncEnvironmentForms();
  syncFacilityLinkForms();
  const begin = form.elements.begin.value.trim() || '..';
  const end = form.elements.end.value.trim() || '..';
  state.record.time = { interval: [begin, end], resolution: state.record.time?.resolution || 'P1D' };
}


function setOptionalStringArray(target, key, raw) {
  const values = splitValues(raw || '');
  if (values.length) target[key] = values;
  else delete target[key];
}

function timeBegin(item) {
  return item?.time?.interval?.[0] ?? '..';
}

function timeEnd(item) {
  return item?.time?.interval?.[1] ?? '..';
}

const DEFAULT_ENVIRONMENT_PERIMETERS_KM = [10, 50];

function environmentPerimeters(row) {
  const perimeters = asArray(row?.perimeter_km);
  return DEFAULT_ENVIRONMENT_PERIMETERS_KM.map((fallback, index) => {
    const parsed = numberOrNull(perimeters[index]);
    return parsed === null ? fallback : parsed;
  });
}

function hasPopulationValue(values) {
  return asArray(values).some(value => value !== null && value !== undefined && value !== '');
}

function renderTerritoryHistory() {
  const rows = asArray(props().territories);
  const count = $('territoryCount');
  const list = $('territoryList');
  if (!count || !list) return;
  count.textContent = rows.length;
  list.innerHTML = rows.length ? `
    <div class="table-wrap">
      <table class="data-table facility-history-table">
        <thead><tr><th>Begin</th><th>End</th><th>Territory</th><th>Actions</th></tr></thead>
        <tbody>${rows.map(territoryRowHtml).join('')}</tbody>
      </table>
    </div>` : '<p class="muted">No territory history yet.</p>';
}

function territoryRowHtml(row, index) {
  return `<tr data-facility-collection="territory" data-index="${index}" id="territory-${index}">
    <td>${dateControlHtml('dates.0', asArray(row.dates)[0], `territory ${index + 1} begin`)}</td>
    <td>${dateControlHtml('dates.1', asArray(row.dates)[1], `territory ${index + 1} end`)}</td>
    <td>${codeInputHtml('territory', row.territory, 'territory', '— Select territory —')}</td>
    <td><button class="small-button danger" data-delete-facility-row="territory:${index}" type="button">Delete</button></td>
  </tr>`;
}

function syncTerritoryForms() {
  const list = $('territoryList');
  if (!list) return;
  const rows = [...list.querySelectorAll('[data-facility-collection="territory"]')];
  const values = rows.map(row => rowObjectFromFields(row, { coerce: true })).filter(item => item.territory || !isOpenInterval(item));
  if (values.length) props().territories = values;
  else delete props().territories;
}


function environmentPopulationHeaderPerimeters(rows) {
  const rowWithPopulation = asArray(rows).find(row => hasPopulationValue(row?.population) && Array.isArray(row?.perimeter_km));
  return environmentPerimeters(rowWithPopulation || null);
}

function surfaceCoverParts(surfaceCover) {
  if (surfaceCover && typeof surfaceCover === 'object' && !Array.isArray(surfaceCover)) {
    const scheme = inputValue(surfaceCover.scheme || surfaceCover.classificationScheme || surfaceCover.classification || '');
    const uri = inputValue(surfaceCover.scheme?.url || surfaceCover.classificationURI || surfaceCover.schemeURI || surfaceCover.schemeUri || '');
    const value = inputValue(surfaceCover.value ?? surfaceCover.code ?? surfaceCover.notation ?? '');
    return { scheme, uri, value };
  }
  return { scheme: '', uri: '', value: inputValue(surfaceCover ?? '') };
}

function surfaceCoverClassificationUri(scheme) {
  const text = inputValue(scheme).trim();
  if (!text) return '';
  if (/^https?:\/\//i.test(text)) return text;
  return `http://codes.wmo.int/wmdr/SurfaceCoverClassification/${text}`;
}

const SURFACE_COVER_SCHEME_VOCABULARIES = {
  globCover2009: { vocabulary: 'surfaceCoverGlobCover2009', register: 'SurfaceCoverGlobCover2009' },
  igbp: { vocabulary: 'surfaceCoverIGBP', register: 'SurfaceCoverIGBP' },
  lccs: { vocabulary: 'surfaceCoverLCCS', register: 'SurfaceCoverLCCS' },
  pft: { vocabulary: 'surfaceCoverPFT', register: 'SurfaceCoverPFT' },
  umd: { vocabulary: 'surfaceCoverUMD', register: 'SurfaceCoverUMD' },
  laifpar: { vocabulary: 'surfaceCoverLAIFPAR', register: 'SurfaceCoverLAIFPAR' },
  npp: { vocabulary: 'surfaceCoverNPP', register: 'SurfaceCoverNPP' },
};

function normalizedSurfaceCoverScheme(scheme) {
  const text = inputValue(scheme).trim();
  if (!text) return '';
  return text.split('/').filter(Boolean).pop();
}

function surfaceCoverVocabularyForScheme(scheme) {
  const key = normalizedSurfaceCoverScheme(scheme);
  return SURFACE_COVER_SCHEME_VOCABULARIES[key]?.vocabulary || '';
}

function surfaceCoverRegisterForScheme(scheme) {
  const key = normalizedSurfaceCoverScheme(scheme);
  return SURFACE_COVER_SCHEME_VOCABULARIES[key]?.register || '';
}

function surfaceCoverValueUri(scheme, value) {
  const register = surfaceCoverRegisterForScheme(scheme);
  const code = inputValue(value).trim();
  if (!register || !code) return '';
  if (/^https?:\/\//i.test(code)) return code;
  return `http://codes.wmo.int/wmdr/${register}/${code}`;
}

function surfaceCoverValueOptionsHtml(scheme, currentValue) {
  const vocabName = surfaceCoverVocabularyForScheme(scheme);
  const blankLabel = vocabName ? '— Select surface cover —' : '— Select classification first —';
  if (!vocabName) {
    const current = inputValue(currentValue).trim();
    return current
      ? `<option value="">${escapeHtml(blankLabel)}</option><option value="${escapeAttr(current)}" selected>${escapeHtml(`${current} — current value`)}</option>`
      : `<option value="">${escapeHtml(blankLabel)}</option>`;
  }
  return selectOptionsHtml(vocabName, currentValue, { blankLabel });
}

function surfaceCoverValueSelectHtml(cover) {
  const vocabName = surfaceCoverVocabularyForScheme(cover.scheme);
  const disabled = vocabName ? '' : ' disabled';
  return `<select class="vocab-select" data-field="surfaceCover.value" data-environment-surface-cover-value="1" data-surface-cover-vocab="${escapeAttr(vocabName)}"${disabled}>${surfaceCoverValueOptionsHtml(cover.scheme, cover.value)}</select>`;
}

function updateSurfaceCoverValueSelectForScheme(schemeSelect) {
  const row = schemeSelect.closest('[data-facility-collection="environment"]');
  if (!row) return;
  const valueSelect = row.querySelector('[data-environment-surface-cover-value]');
  if (!valueSelect) return;
  const current = valueSelect.value;
  const vocabName = surfaceCoverVocabularyForScheme(schemeSelect.value);
  valueSelect.dataset.surfaceCoverVocab = vocabName;
  valueSelect.disabled = !vocabName;
  valueSelect.innerHTML = surfaceCoverValueOptionsHtml(schemeSelect.value, current);
  setSelectValue(valueSelect, current);
}

function surfaceCoverObjectFromRow(row) {
  const scheme = inputValue(row.querySelector('[data-environment-surface-cover-scheme]')?.value || '').trim();
  const value = inputValue(row.querySelector('[data-environment-surface-cover-value]')?.value || '').trim();
  if (!scheme && !value) return null;
  const result = {};
  if (scheme) {
    result.scheme = { id: scheme };
    const schemeUri = surfaceCoverClassificationUri(scheme);
    if (schemeUri) result.scheme.url = schemeUri;
  }
  if (value) {
    result.value = { id: value };
    const valueUri = surfaceCoverValueUri(scheme, value);
    if (valueUri) result.value.url = valueUri;
  }
  return result;
}

function topographyBathymetryParts(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return {
    localTopography: inputValue(value.localTopography ?? value.local_topography ?? ''),
    relativeElevation: inputValue(value.relativeElevation ?? value.relative_elevation ?? ''),
    topographicContext: inputValue(value.topographicContext ?? value.topographic_context ?? ''),
    altitudeOrDepth: inputValue(value.altitudeOrDepth ?? value.altitude_or_depth ?? ''),
  };
}

function topographyBathymetryObjectFromRow(row) {
  const fields = ['localTopography', 'relativeElevation', 'topographicContext', 'altitudeOrDepth'];
  const result = {};
  fields.forEach(field => {
    const value = inputValue(row.querySelector(`[data-topography-bathymetry="${field}"]`)?.value || '').trim();
    if (value) result[field] = valueOrNumber(value);
  });
  return Object.keys(result).length ? result : null;
}

function renderEnvironmentHistory() {
  const rows = asArray(props().environment);
  const count = $('environmentCount');
  const list = $('environmentList');
  if (!count || !list) return;
  count.textContent = rows.length;
  const populationHeaders = environmentPopulationHeaderPerimeters(rows);
  list.innerHTML = rows.length
    ? `<div class="environment-card-list">${rows.map((row, index) => environmentRowHtml({ ...row, __index: index }, populationHeaders)).join('')}</div>`
    : '<p class="muted">No environment metadata yet.</p>';
  populateStaticVocabularySelects(list);
}

function environmentRowHtml(row, headerPerimeters) {
  const index = Number(row?.__index ?? 0);
  const population = asArray(row.population);
  const perimeters = hasPopulationValue(population) ? environmentPerimeters(row) : headerPerimeters;
  const cover = surfaceCoverParts(row.surfaceCover);
  const topo = topographyBathymetryParts(row.topographyBathymetry);
  const title = `Environment ${index + 1}`;
  return `<div class="facility-row-card environment-row-card" data-facility-collection="environment" data-index="${index}" id="environment-${index}">
    <div class="row-card-header">
      <strong>${escapeHtml(title)}</strong>
      <button class="small-button danger" data-delete-facility-row="environment:${index}" type="button">Delete</button>
    </div>
    <div class="facility-row facility-date-row environment-date-row">
      <label>Begin ${dateControlHtml('time.interval.0', timeBegin(row), `${title} begin`)}</label>
      <label>End ${dateControlHtml('time.interval.1', timeEnd(row), `${title} end`)}</label>
    </div>
    <div class="facility-row environment-classification-row">
      <label>Climate zone ${codeInputHtml('climateZone', row.climateZone, 'climateZone')}</label>
      <label>Surface roughness ${codeInputHtml('surfaceRoughness', row.surfaceRoughness, 'surfaceRoughness', '— Select Davenport roughness —')}</label>
    </div>
    <div class="facility-row environment-surface-cover-row">
      <label>Surface cover classification ${codeInputHtml('surfaceCover.classificationScheme', cover.scheme, 'surfaceCoverClassification', '— Select classification —').replace('data-field="surfaceCover.classificationScheme"', 'data-field="surfaceCover.classificationScheme" data-environment-surface-cover-scheme="1"')}</label>
      <label>Surface cover code ${surfaceCoverValueSelectHtml(cover)}</label>
    </div>
    <div class="facility-row environment-population-row">
      <label>Population within ${escapeHtml(perimeters[0])} km
        <input data-field="population.0" data-environment-population="0" data-environment-perimeter="${escapeAttr(perimeters[0])}" type="number" step="any" value="${escapeAttr(population[0] ?? '')}" />
      </label>
      <label>Population within ${escapeHtml(perimeters[1])} km
        <input data-field="population.1" data-environment-population="1" data-environment-perimeter="${escapeAttr(perimeters[1])}" type="number" step="any" value="${escapeAttr(population[1] ?? '')}" />
      </label>
    </div>
    <div class="environment-topography-block">
      <div class="subtle-heading">Topography/bathymetry</div>
      <div class="facility-row environment-topography-row">
        <label>Local topography ${codeInputHtml('topographyBathymetry.localTopography', topo.localTopography, 'localTopography', '— Select local topography —').replace('data-field="topographyBathymetry.localTopography"', 'data-field="topographyBathymetry.localTopography" data-topography-bathymetry="localTopography"')}</label>
        <label>Relative elevation ${codeInputHtml('topographyBathymetry.relativeElevation', topo.relativeElevation, 'relativeElevation', '— Select relative elevation —').replace('data-field="topographyBathymetry.relativeElevation"', 'data-field="topographyBathymetry.relativeElevation" data-topography-bathymetry="relativeElevation"')}</label>
        <label>Topographic context ${codeInputHtml('topographyBathymetry.topographicContext', topo.topographicContext, 'topographicContext', '— Select context —').replace('data-field="topographyBathymetry.topographicContext"', 'data-field="topographyBathymetry.topographicContext" data-topography-bathymetry="topographicContext"')}</label>
        <label>Altitude/depth ${codeInputHtml('topographyBathymetry.altitudeOrDepth', topo.altitudeOrDepth, 'altitudeOrDepth', '— Select altitude/depth —').replace('data-field="topographyBathymetry.altitudeOrDepth"', 'data-field="topographyBathymetry.altitudeOrDepth" data-topography-bathymetry="altitudeOrDepth"')}</label>
      </div>
    </div>
  </div>`;
}

function syncEnvironmentForms() {
  const list = $('environmentList');
  if (!list) return;
  const rows = [...list.querySelectorAll('[data-facility-collection="environment"]')];
  const values = rows.map(row => {
    const item = rowObjectFromFields(row, { coerce: true, numberArrays: ['population'] });
    const surfaceCover = surfaceCoverObjectFromRow(row);
    if (surfaceCover === null) delete item.surfaceCover;
    else item.surfaceCover = surfaceCover;
    const topography = topographyBathymetryObjectFromRow(row);
    if (topography) item.topographyBathymetry = topography;
    else delete item.topographyBathymetry;
    const population = [0, 1].map(index => numberOrNull(row.querySelector(`[data-environment-population="${index}"]`)?.value ?? ''));
    if (hasPopulationValue(population)) {
      item.population = population;
      item.perimeter_km = [0, 1].map(index => {
        const input = row.querySelector(`[data-environment-population="${index}"]`);
        return numberOrNull(input?.dataset.environmentPerimeter) ?? DEFAULT_ENVIRONMENT_PERIMETERS_KM[index];
      });
    } else {
      delete item.population;
      delete item.perimeter_km;
    }
    return item;
  }).filter(item => Object.keys(item).some(key => key !== 'time') || !isOpenInterval(item));
  if (values.length) props().environment = values;
  else delete props().environment;
}

function renderFacilityLinks() {
  const rows = asArray(props().links);
  const count = $('facilityLinkCount');
  const list = $('facilityLinksList');
  if (!count || !list) return;
  count.textContent = rows.length;
  list.innerHTML = rows.length ? `
    <div class="table-wrap">
      <table class="data-table facility-link-table">
        <thead><tr><th>Href</th><th>Rel</th><th>Type</th><th>Title</th><th>Actions</th></tr></thead>
        <tbody>${rows.map(facilityLinkRowHtml).join('')}</tbody>
      </table>
    </div>` : '<p class="muted">No facility links yet.</p>';
}

function facilityLinkRowHtml(row, index) {
  return `<tr data-facility-collection="facilityLink" data-index="${index}" id="facility-link-${index}">
    <td><input data-field="href" value="${escapeAttr(row.href || '')}" placeholder="https://…" /></td>
    <td><input data-field="rel" value="${escapeAttr(row.rel || '')}" placeholder="about" /></td>
    <td><input data-field="type" value="${escapeAttr(row.type || '')}" placeholder="text/html" /></td>
    <td><input data-field="title" value="${escapeAttr(row.title || '')}" /></td>
    <td><button class="small-button danger" data-delete-facility-row="facilityLink:${index}" type="button">Delete</button></td>
  </tr>`;
}

function syncFacilityLinkForms() {
  const list = $('facilityLinksList');
  if (!list) return;
  const rows = [...list.querySelectorAll('[data-facility-collection="facilityLink"]')];
  const values = rows.map(row => rowObjectFromFields(row, { coerce: false })).filter(item => item.href || item.rel || item.type || item.title);
  if (values.length) props().links = values;
  else delete props().links;
}

function rowObjectFromFields(row, options = {}) {
  const item = {};
  row.querySelectorAll('[data-field]').forEach(input => {
    const field = input.dataset.field;
    let value = input.value;
    if (field === 'time.interval.0' || field === 'time.interval.1') value = value || '..';
    else if (options.coerce) value = valueOrJsonOrNumber(String(value ?? '').trim());
    else value = String(value ?? '').trim();
    setField(item, field, value);
  });
  if (options.numberArrays) {
    options.numberArrays.forEach(key => {
      if (Array.isArray(item[key])) {
        item[key] = item[key].map(value => value === '' || value === undefined ? null : value);
        if (item[key].every(value => value === null)) delete item[key];
      }
    });
  }
  return item;
}

function isOpenInterval(item) {
  const interval = item?.time?.interval;
  return Array.isArray(interval) && (interval[0] || '..') === '..' && (interval[1] || '..') === '..';
}

function addFacilityCollectionRow(kind) {
  syncFacilityForm();
  if (kind === 'territory') {
    const rows = props().territories ??= [];
    rows.push({ territory: '', dates: [state.record.time?.interval?.[0] || '..', '..'] });
    state.pendingScrollTarget = `territory-${rows.length - 1}`;
  } else if (kind === 'environment') {
    const rows = props().environment ??= [];
    rows.push({ time: { interval: [state.record.time?.interval?.[0] || '..', '..'] }, perimeter_km: [...DEFAULT_ENVIRONMENT_PERIMETERS_KM] });
    state.pendingScrollTarget = `environment-${rows.length - 1}`;
  } else if (kind === 'facilityLink') {
    const rows = props().links ??= [];
    rows.push({ href: '', rel: 'about', type: 'text/html' });
    state.pendingScrollTarget = `facility-link-${rows.length - 1}`;
  }
  renderAll();
}

function deleteFacilityCollectionRow(kind, index) {
  syncFacilityForm();
  if (kind === 'territory') props().territories?.splice(index, 1);
  if (kind === 'environment') props().environment?.splice(index, 1);
  if (kind === 'facilityLink') props().links?.splice(index, 1);
  renderAll();
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

function renderObservations() {
  const series = asArray(props().observations);
  $('observationCount').textContent = series.length;
  $('observationsList').innerHTML = series.map((obs, index) => itemHtml(
    observationsHeaderTitle(obs, index),
    observationsFormHtml(obs, index),
    'observations',
    index,
  )).join('') || '<p class="muted">No Observations yet.</p>';
}

function observationsHeaderTitle(obs, index) {
  const id = entityId(obs) || `observations:${index + 1}`;
  const title = String(obs.title || '').trim();
  return title ? `${id} [${title}]` : id;
}


function programAffiliationValues(values) {
  return asArray(values).map(item => inputValue(item?.programAffiliation ?? item)).filter(Boolean);
}

function observationsFormHtml(obs, index) {
  return `
    <div class="item-form observation-form" data-kind="observations" data-index="${index}">
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
        <label>Program affiliations ${multiCodeInputHtml('programAffiliations', programAffiliationValues(obs.programAffiliations), 'programAffiliations', 'program affiliation')}</label>
        <label>Application areas ${multiCodeInputHtml('applicationAreas', obs.applicationAreas, 'applicationAreas', 'application area')}</label>
      </div>
    </div>
    ${observationConfigurationLinksHtml(obs, index)}
    ${observationInstrumentLinksHtml(obs)}
    ${observationProcedureLinksHtml(obs, index)}
    ${observationContactLinksHtml(obs)}
    <div class="actions section-actions">
      <button type="button" data-add-config="${index}">Add configuration</button>
      <button type="button" data-add-observation-instrument="${index}">Add linked instrument</button>
    </div>`;
}

function observationConfigurations(obs) {
  return asArray(obs.configurations);
}

function flattenConfigurations() {
  return asArray(props().observations).flatMap((obs, seriesIndex) =>
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
  return xrefRow('Configurations', links, 'No configurations');
}

function observationInstrumentLinksHtml(obs) {
  const instrumentIndex = indexByUid('instrument');
  const links = observationInstrumentRefs(obs).map(ref => linkToItem('instrument', instrumentIndex.get(ref), ref));
  return xrefRow('Linked instruments', links, 'No instrument refs in configurations');
}

function procedureCollectionDomId(kind, seriesIndex) {
  return `${kind}-procedures-${seriesIndex}`;
}

function observationProcedureLinksHtml(obs, seriesIndex) {
  const observingCount = observingProcedures(obs).length;
  const reportingCount = reportingProcedures(obs).length;
  const links = [
    `<a class="xref" href="#${procedureCollectionDomId('observing', seriesIndex)}" data-scroll-target="${procedureCollectionDomId('observing', seriesIndex)}">ObservingProcedures (${observingCount})</a>`,
    `<a class="xref" href="#${procedureCollectionDomId('reporting', seriesIndex)}" data-scroll-target="${procedureCollectionDomId('reporting', seriesIndex)}">ReportingProcedures (${reportingCount})</a>`,
  ];
  return xrefRow('Procedures and schedules', links, 'No procedure section');
}

function renderConfigurationsOverview() {
  const configs = flattenConfigurations();
  $('configurationCount').textContent = configs.length;
  $('configurationsList').innerHTML = configs.map(({ obs, config, seriesIndex, configIndex }) => configurationItemHtml(obs, config, seriesIndex, configIndex)).join('') || '<p class="muted">No configurations yet.</p>';
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
      <label>Configuration ID <input data-field="id" value="${escapeAttr(config.id || '')}" /></label>
      <label>Begin ${dateControlHtml('time.interval.0', configStart(config), 'configuration begin date')}</label>
      <label>End ${dateControlHtml('time.interval.1', configEnd(config), 'configuration end date')}</label>
      <label>Observing method ${codeInputHtml('observingMethod', config.observingMethod, 'observingMethodAtmosphere')}</label>
      <label>Operating status ${codeInputHtml('operatingStatus', config.operatingStatus, 'operatingStatus')}</label>
      <label>Source of observation ${codeInputHtml('sourceOfObservation', config.sourceOfObservation, 'sourceOfObservation')}</label>
      <label>Instrument ID <input data-field="instrument" value="${escapeAttr(config.instrument || '')}" /></label>
      <label>Serial number <input data-field="instrumentSerialNumber" value="${escapeAttr(config.instrumentSerialNumber || '')}" /></label>
      <label>Exposure ${codeInputHtml('exposure', config.exposure, 'exposure')}</label>
      <label>Reference surface ${codeInputHtml('verticalDistance.referenceSurface', config.verticalDistance?.referenceSurface, 'referenceSurface')}</label>
      <label>Relative location <input data-field="relativeLocation" value="${escapeAttr(config.relativeLocation ?? '')}" /></label>
      <label>Vertical distance <input data-field="verticalDistance.distances.0" value="${escapeAttr(asArray(config.verticalDistance?.distances)[0] ?? '')}" /></label>
      <label>Vertical distance unit ${codeInputHtml('verticalDistance.unit', config.verticalDistance?.unit, 'unit')}</label>
    </div>`;
}

function configurationCrossLinksHtml(obs, config, seriesIndex) {
  const instrumentIndex = indexByUid('instrument');
  const obsLink = linkToItem('observations', seriesIndex, entityId(obs) || obs.title || `Observations ${seriesIndex + 1}`);
  const instrumentLinks = config.instrument ? [linkToItem('instrument', instrumentIndex.get(config.instrument), config.instrument)] : [];
  return `${xrefRow('Belongs to', [obsLink], 'No Observations')}${xrefRow('Linked instrument', instrumentLinks, 'No instrument ref')}`;
}


function observingProcedures(obs) {
  return asArray(obs.observingProcedures);
}

function reportingProcedures(obs) {
  return asArray(obs.reportingProcedures ?? obs.reporting);
}

function renderProceduresSchedules() {
  const series = asArray(props().observations);
  const scheduleCount = asArray(props().schedules).length;
  const procedureTotal = series.reduce((count, obs) => count + observingProcedures(obs).length + reportingProcedures(obs).length, 0);
  const badge = $('procedureCount');
  if (badge) badge.textContent = procedureTotal + scheduleCount;
  const list = $('proceduresList');
  if (list) {
    list.innerHTML = series.length
      ? series.map((obs, index) => proceduresForObservationHtml(obs, index)).join('')
      : '<p class="muted">No Observations yet. Add an Observations before adding observing or reporting procedures.</p>';
  }
  renderSchedules();
}

function proceduresForObservationHtml(obs, seriesIndex) {
  const id = entityId(obs) || `Observations ${seriesIndex + 1}`;
  const label = observationsHeaderTitle(obs, seriesIndex);
  return `<article class="item procedure-card" id="procedures-${seriesIndex}" data-item-kind="procedures" data-series-index="${seriesIndex}">
    <div class="item-header">
      <div>
        <div class="item-title">Procedures and schedules for ${escapeHtml(label)}</div>
        <div class="item-subtitle">Observations: ${escapeHtml(id)}</div>
      </div>
      <div class="actions">
        ${linkToItem('observations', seriesIndex, 'Back to Observations')}
      </div>
    </div>
    <section class="procedure-block" id="${procedureCollectionDomId('observing', seriesIndex)}">
      <div class="procedure-block-heading">
        <h4>ObservingProcedures</h4>
        <span class="muted">for ${escapeHtml(label)}</span>
      </div>
      ${observingProceduresTableHtml(obs, seriesIndex)}
      <div class="actions section-actions"><button type="button" data-add-procedure="observing:${seriesIndex}">Add observing procedure</button></div>
    </section>
    <section class="procedure-block" id="${procedureCollectionDomId('reporting', seriesIndex)}">
      <div class="procedure-block-heading">
        <h4>ReportingProcedures</h4>
        <span class="muted">for ${escapeHtml(label)}</span>
      </div>
      ${reportingProceduresTableHtml(obs, seriesIndex)}
      <div class="actions section-actions"><button type="button" data-add-procedure="reporting:${seriesIndex}">Add reporting procedure</button></div>
    </section>
  </article>`;
}

function observingProceduresTableHtml(obs, seriesIndex) {
  const rows = observingProcedures(obs);
  if (!rows.length) return '<p class="muted">No observingProcedures yet.</p>';
  return `<div class="table-wrap"><table class="data-table procedure-table">
    <thead><tr><th>Begin</th><th>End</th><th>Strategy</th><th>Observing schedules</th><th>Actions</th></tr></thead>
    <tbody>${rows.map((row, index) => observingProcedureRowHtml(row, seriesIndex, index)).join('')}</tbody>
  </table></div>`;
}

function observingProcedureRowHtml(row, seriesIndex, procIndex) {
  return `<tr id="observing-procedure-${seriesIndex}-${procIndex}" data-procedure-kind="observingProcedure" data-series-index="${seriesIndex}" data-procedure-index="${procIndex}">
    <td>${dateControlHtml('time.interval.0', timeBegin(row), `observing procedure ${procIndex + 1} begin`)}</td>
    <td>${dateControlHtml('time.interval.1', timeEnd(row), `observing procedure ${procIndex + 1} end`)}</td>
    <td>${codeInputHtml('strategy', row.strategy, 'observingStrategy')}</td>
    <td>${scheduleReferenceInputHtml('observingSchedules', row.observingSchedules, 'observing schedules')}</td>
    <td><button class="small-button" data-json-procedure="observing:${seriesIndex}:${procIndex}" type="button">Edit JSON</button> <button class="small-button danger" data-delete-procedure="observing:${seriesIndex}:${procIndex}" type="button">Delete</button></td>
  </tr>`;
}

function reportingProceduresTableHtml(obs, seriesIndex) {
  const rows = reportingProcedures(obs);
  if (!rows.length) return '<p class="muted">No reportingProcedures yet.</p>';
  return `<div class="table-wrap"><table class="data-table procedure-table">
    <thead><tr><th>Exchange</th><th>Data policy</th><th>Level</th><th>UoM</th><th>Timeliness</th><th>N obs</th><th>Reporting schedules</th><th>Actions</th></tr></thead>
    <tbody>${rows.map((row, index) => reportingProcedureRowHtml(row, seriesIndex, index)).join('')}</tbody>
  </table></div>`;
}

function reportingProcedureRowHtml(row, seriesIndex, procIndex) {
  return `<tr id="reporting-procedure-${seriesIndex}-${procIndex}" data-procedure-kind="reportingProcedure" data-series-index="${seriesIndex}" data-procedure-index="${procIndex}">
    <td><select class="vocab-select" data-field="internationalExchange"><option value="">—</option><option value="true"${row.internationalExchange === true ? ' selected' : ''}>true</option><option value="false"${row.internationalExchange === false ? ' selected' : ''}>false</option></select></td>
    <td>${codeInputHtml('dataPolicy', row.dataPolicy, 'dataPolicy')}</td>
    <td>${codeInputHtml('levelOfData', row.levelOfData, 'levelOfData')}</td>
    <td>${codeInputHtml('uom', row.uom, 'unit')}</td>
    <td><input data-field="timeliness" value="${escapeAttr(row.timeliness ?? '')}" placeholder="P1Y" /></td>
    <td><input data-field="numberOfObservationsInReportingInterval" value="${escapeAttr(row.numberOfObservationsInReportingInterval ?? '')}" /></td>
    <td>${scheduleReferenceInputHtml('reportingSchedules', row.reportingSchedules, 'reporting schedules')}</td>
    <td><button class="small-button" data-json-procedure="reporting:${seriesIndex}:${procIndex}" type="button">Edit JSON</button> <button class="small-button danger" data-delete-procedure="reporting:${seriesIndex}:${procIndex}" type="button">Delete</button></td>
  </tr>`;
}

function renderSchedules() {
  const schedules = asArray(props().schedules);
  const count = $('scheduleCount');
  const list = $('schedulesList');
  if (count) count.textContent = schedules.length;
  if (!list) return;
  list.innerHTML = schedules.length ? `<div class="table-wrap"><table class="data-table schedule-table">
    <thead><tr><th>UID</th><th>Start</th><th>Duration</th><th>Sampling frequency</th><th>Aggregation interval</th><th>Diurnal base time</th><th>Used by</th><th>Actions</th></tr></thead>
    <tbody>${schedules.map(scheduleRowHtml).join('')}</tbody>
  </table></div>` : '<p class="muted">No reusable schedules yet.</p>';
}

function scheduleUsageLinksHtml(uid) {
  const value = inputValue(uid);
  if (!value) return '<span class="xref-empty">No UID yet</span>';
  const links = [];
  asArray(props().observations).forEach((obs, seriesIndex) => {
    const obsLabel = entityId(obs) || `Observations ${seriesIndex + 1}`;
    observingProcedures(obs).forEach((procedure, procIndex) => {
      if (asArray(procedure.observingSchedules).map(inputValue).includes(value)) {
        const target = `observing-procedure-${seriesIndex}-${procIndex}`;
        links.push(`<a class="xref" href="#${target}" data-scroll-target="${target}" title="Go to observing procedure using ${escapeAttr(value)}">${escapeHtml(obsLabel)} · observing ${procIndex + 1}</a>`);
      }
    });
    reportingProcedures(obs).forEach((procedure, procIndex) => {
      if (asArray(procedure.reportingSchedules).map(inputValue).includes(value)) {
        const target = `reporting-procedure-${seriesIndex}-${procIndex}`;
        links.push(`<a class="xref" href="#${target}" data-scroll-target="${target}" title="Go to reporting procedure using ${escapeAttr(value)}">${escapeHtml(obsLabel)} · reporting ${procIndex + 1}</a>`);
      }
    });
  });
  return links.length
    ? `<div class="schedule-usage-links">${links.join('')}</div>`
    : '<span class="xref-empty">Not referenced</span>';
}

function scheduleRowHtml(schedule, index) {
  return `<tr id="schedule-${index}" data-schedule-index="${index}">
    <td><input data-field="uid" value="${escapeAttr(schedule.uid || '')}" placeholder="schedule_…" /></td>
    <td><input data-field="start" value="${escapeAttr(schedule.start || '')}" placeholder="0001-01-01T00:00:00" /></td>
    <td><input data-field="duration" value="${escapeAttr(schedule.duration || '')}" placeholder="PT23H59M" /></td>
    <td><input data-field="wmo.int:samplingFrequency" value="${escapeAttr(schedule['wmo.int:samplingFrequency'] || '')}" placeholder="PT10M" /></td>
    <td><input data-field="wmo.int:aggregationInterval" value="${escapeAttr(schedule['wmo.int:aggregationInterval'] || '')}" placeholder="PT1H" /></td>
    <td><input data-field="wmo.int:diurnalBaseTime" value="${escapeAttr(schedule['wmo.int:diurnalBaseTime'] || '')}" placeholder="00:00:00" /></td>
    <td>${scheduleUsageLinksHtml(schedule.uid)}</td>
    <td><button class="small-button" data-json-schedule="${index}" type="button">Edit JSON</button> <button class="small-button danger" data-delete-schedule="${index}" type="button">Delete</button></td>
  </tr>`;
}

function syncProceduresAndSchedulesForms() {
  document.querySelectorAll('[data-procedure-kind="observingProcedure"]').forEach(row => {
    const seriesIndex = Number(row.dataset.seriesIndex);
    const procIndex = Number(row.dataset.procedureIndex);
    const target = props().observations?.[seriesIndex]?.observingProcedures?.[procIndex];
    if (!target) return;
    syncFieldsIntoTarget(row, target);
  });
  document.querySelectorAll('[data-procedure-kind="reportingProcedure"]').forEach(row => {
    const seriesIndex = Number(row.dataset.seriesIndex);
    const procIndex = Number(row.dataset.procedureIndex);
    const obs = props().observations?.[seriesIndex];
    const target = obs?.reportingProcedures?.[procIndex];
    if (!target) return;
    syncFieldsIntoTarget(row, target);
  });
  document.querySelectorAll('[data-schedule-index]').forEach(row => {
    const index = Number(row.dataset.scheduleIndex);
    const target = props().schedules?.[index];
    if (!target) return;
    syncFieldsIntoTarget(row, target);
    target['@type'] ||= 'Event';
  });
}

function syncFieldsIntoTarget(container, target) {
  container.querySelectorAll('[data-field]').forEach(input => {
    setField(target, input.dataset.field, coerceField(input.dataset.field, input.value));
  });
}

function addProcedure(kind, seriesIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observations?.[seriesIndex];
  if (!obs) return;
  if (kind === 'observing') {
    const rows = obs.observingProcedures ??= [];
    rows.push({ time: { interval: [state.record.time?.interval?.[0] || '..', '..'] }, observingSchedules: [] });
    state.pendingScrollTarget = `observing-procedure-${seriesIndex}-${rows.length - 1}`;
  } else if (kind === 'reporting') {
    const rows = obs.reportingProcedures ??= [];
    rows.push({ internationalExchange: null, reportingSchedules: [] });
    state.pendingScrollTarget = `reporting-procedure-${seriesIndex}-${rows.length - 1}`;
  }
  renderAll();
}

function deleteProcedure(kind, seriesIndex, procIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observations?.[seriesIndex];
  if (!obs) return;
  if (kind === 'observing') obs.observingProcedures?.splice(procIndex, 1);
  if (kind === 'reporting') obs.reportingProcedures?.splice(procIndex, 1);
  renderAll();
}

function uniqueScheduleUid() {
  const existing = new Set(asArray(props().schedules).map(item => item.uid).filter(Boolean));
  let next = existing.size + 1;
  let uid = `schedule_new_${next}`;
  while (existing.has(uid)) {
    next += 1;
    uid = `schedule_new_${next}`;
  }
  return uid;
}

function addSchedule() {
  syncFacilityForm();
  syncItemForms();
  const schedules = props().schedules ??= [];
  schedules.push({ uid: uniqueScheduleUid(), '@type': 'Event', start: '0001-01-01T00:00:00', duration: 'PT23H59M' });
  state.pendingScrollTarget = `schedule-${schedules.length - 1}`;
  renderAll();
}

function deleteSchedule(index) {
  syncFacilityForm();
  syncItemForms();
  props().schedules?.splice(index, 1);
  renderAll();
}

function proceduresSectionJson() {
  return {
    observations: asArray(props().observations).map((obs, index) => ({
      observations: entityId(obs) || index,
      observingProcedures: asArray(obs.observingProcedures),
      reportingProcedures: asArray(obs.reportingProcedures ?? obs.reporting),
    })),
    schedules: asArray(props().schedules),
  };
}

function applyProceduresSectionJson(value) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => applyProcedureEntry(entry, index));
    return;
  }
  if (value && typeof value === 'object') {
    if (Array.isArray(value.schedules)) props().schedules = value.schedules;
    asArray(value.observations).forEach((entry, index) => applyProcedureEntry(entry, index));
  }
}

function applyProcedureEntry(entry, fallbackIndex) {
  const series = asArray(props().observations);
  const key = entry?.observations;
  const index = key ? series.findIndex(obs => entityId(obs) === key) : fallbackIndex;
  if (index < 0 || !series[index]) return;
  if (Array.isArray(entry.observingProcedures)) series[index].observingProcedures = entry.observingProcedures;
  if (Array.isArray(entry.reportingProcedures)) series[index].reportingProcedures = entry.reportingProcedures;
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
    .map(({ obs, seriesIndex }) => linkToItem('observations', seriesIndex, entityId(obs) || obs.title || `Observations ${seriesIndex + 1}`));
  return `${xrefRow('Used by configurations', configLinks, 'No configuration uses this instrument')}${xrefRow('Used by Observations', seriesLinks, 'No Observations uses this instrument')}`;
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
    links.push(`<a class="xref" href="#observationsSection" data-scroll-target="observationsSection">Observations</a>`);
  }
  return xrefRow('Linked from', links, 'No role-based section link');
}

function syncItemForms() {
  document.querySelectorAll('[data-kind="observations"], [data-kind="instrument"], [data-kind="contact"]').forEach(form => {
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
    const target = props().observations?.[seriesIndex]?.configurations?.[configIndex];
    if (!target) return;
    form.querySelectorAll('[data-field]').forEach(input => {
      setField(target, input.dataset.field, coerceField(input.dataset.field, input.value));
    });
    cleanupConfiguration(target);
  });
  syncProceduresAndSchedulesForms();
}

function cleanupConfiguration(config) {
  const vd = config.verticalDistance;
  if (vd && typeof vd === 'object' && !Array.isArray(vd)) {
    vd.distances = asArray(vd.distances).filter(value => !isEmptyFormValue(value));
    if (!vd.distances.length) {
      delete config.verticalDistance;
      return;
    }
    if (isEmptyFormValue(vd.unit)) delete vd.unit;
    if (isEmptyFormValue(vd.referenceSurface)) delete vd.referenceSurface;
  }
}

function getSectionForKind(kind) {
  const p = props();
  if (kind === 'observations') return p.observations ??= [];
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
  if (field === 'time.interval.0' || field === 'time.interval.1' || field === 'dates.0' || field === 'dates.1') return trimmed || '..';
  if (['programAffiliations', 'applicationAreas', 'observingMethods', 'roles', 'observingSchedules', 'reportingSchedules', 'dataFormat', 'referenceTimeSource', 'additionalTitles', 'additionalIds', 'keywords', 'facilitySets'].includes(field)) {
    return splitValues(trimmed);
  }
  if (['emails', 'phones'].includes(field)) {
    return splitValues(trimmed);
  }
  if (field === 'internationalExchange') {
    if (trimmed === 'true') return true;
    if (trimmed === 'false') return false;
    return null;
  }
  if (['observedProperty', 'observedGeometry', 'observingMethod', 'operatingStatus', 'sourceOfObservation', 'exposure', 'facilityType', 'territory', 'climateZone', 'surfaceCover', 'surfaceRoughness', 'strategy', 'dataPolicy', 'levelOfData', 'uom', 'spatialReportingInterval', 'timeStampMeaning'].includes(field) || field.endsWith('.domain') || field.endsWith('.value') || field.endsWith('.unit') || field.endsWith('.referenceSurface')) {
    return valueOrJson(trimmed);
  }
  if (field === 'verticalDistance.distances.0') return valueOrNumber(trimmed);
  return trimmed;
}

function splitValues(value) {
  return value ? value.split(',').map(part => part.trim()).filter(Boolean) : [];
}

function valueOrJson(value) {
  if (value === '') return '';
  if (value.startsWith('{') || value.startsWith('[')) {
    try { return JSON.parse(value); } catch { return value; }
  }
  return value;
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
  if (typeof value === 'object') {
    if (!Array.isArray(value) && value.id !== undefined) return String(value.id);
    if (!Array.isArray(value) && value.value !== undefined && Object.keys(value).length <= 2) return String(value.value);
    return JSON.stringify(value);
  }
  return String(value);
}

function displayCompact(value) {
  if (value === undefined || value === null || value === '') return '';
  if (typeof value === 'object') return value.id !== undefined ? String(value.id) : JSON.stringify(value);
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
      observations: [],
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
  return asArray(props().observations).map((obs, index) => ({
    observations: entityId(obs) || index,
    configurations: asArray(obs.configurations),
  }));
}

function applyConfigurationsSectionJson(value) {
  const entries = ensureArray(value, 'configurations');
  const series = asArray(props().observations);
  entries.forEach((entry, index) => {
    const targetIndex = findObservationsIndexForConfigurationEntry(entry, index);
    if (targetIndex >= 0 && series[targetIndex]) {
      series[targetIndex].configurations = ensureArray(entry.configurations ?? [], 'configurations');
    }
  });
}

function findObservationsIndexForConfigurationEntry(entry, fallbackIndex) {
  const key = entry?.observations;
  if (key) {
    const found = asArray(props().observations).findIndex(obs => entityId(obs) === key);
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

function addInstrumentForObservations(seriesIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observations?.[seriesIndex];
  if (!obs) return;

  const instruments = props().instruments ??= [];
  const uid = uniqueUid('instrument', new Set(instruments.map(entityId).filter(Boolean)));
  const configs = obs.configurations ??= [];
  let configIndex = configs.findIndex(config => !config?.instrument);
  if (configIndex < 0) {
    configs.push({
      time: { interval: ['..', '..'] },
      id: `${entityId(obs) || 'observation'}-configuration-${configs.length + 1}`,
    });
    configIndex = configs.length - 1;
  }
  const config = configs[configIndex];
  config.instrument = uid;

  const observingMethods = [];
  if (config.observingMethod !== undefined && config.observingMethod !== '') {
    observingMethods.push(inputValue(config.observingMethod));
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
  if (kind === 'observations') section.push({
    id: `observation:new-${next}`,
    observedProperty: '',
    observedGeometry: '',
    observedFeature: { domain: '' },
    programAffiliations: [],
    applicationAreas: [],
    configurations: [],
  });
  if (kind === 'instrument') section.push({ id: uniqueUid('instrument', new Set(section.map(entityId).filter(Boolean))) });
  if (kind === 'contact') section.push({ identifier: uniqueUid('contact', new Set(section.map(entityId).filter(Boolean))), roles: [], emails: [] });
  renderAll();
}

function addConfiguration(seriesIndex) {
  syncFacilityForm();
  syncItemForms();
  const obs = props().observations?.[seriesIndex];
  if (!obs) return;
  obs.configurations ??= [];
  obs.configurations.push({
    id: `${entityId(obs) || 'observation'}-configuration-${obs.configurations.length + 1}`,
    time: { interval: ['..', '..'] },
  });
  state.pendingScrollTarget = configurationDomId(seriesIndex, obs.configurations.length - 1);
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
  props().observations?.[seriesIndex]?.configurations?.splice(configIndex, 1);
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

function closeOtherTopLevelSections(openSection) {
  if (!openSection?.matches?.('details.card') || !TOP_LEVEL_SECTION_IDS.includes(openSection.id)) return;
  TOP_LEVEL_SECTION_IDS.forEach(id => {
    if (id !== openSection.id) {
      const section = $(id);
      if (section) section.open = false;
    }
  });
}

function scrollToItem(targetId) {
  const target = $(targetId);
  if (!target) return;
  const topLevelDetails = target.matches('details.card') ? target : target.closest('details.card');
  if (topLevelDetails?.id) focusSection(topLevelDetails.id, { scroll: false });
  let ancestor = target.parentElement;
  while (ancestor) {
    if (ancestor.tagName === 'DETAILS') ancestor.open = true;
    ancestor = ancestor.parentElement;
  }
  const isTableRow = target.tagName === 'TR';
  target.scrollIntoView({ behavior: 'smooth', block: isTableRow ? 'center' : 'start', inline: 'nearest' });
  target.classList.add('flash');
  window.setTimeout(() => target.classList.remove('flash'), 1800);
}

function refreshRelationshipViews() {
  renderFacility();
  renderObservations();
  renderConfigurationsOverview();
  renderProceduresSchedules();
  renderInstruments();
  renderContacts();
  $('recordRaw').value = pretty(state.record);
}

function applyModal() {
  const value = parseJson($('modalJson').value, $('modalTitle').textContent);
  const target = state.modalTarget;
  let scrollTarget = null;
  let appliedLabel = 'JSON';
  if (target === 'facilityRaw') {
    Object.assign(state.record, pick(value, ['id', 'geometry', 'temporalGeometry', 'time', 'conformsTo']));
    Object.assign(props(), omit(value.properties ? value.properties : value, ['observations', 'instruments', 'contacts', 'schedules']));
    scrollTarget = 'facilitySection';
    appliedLabel = 'Facility JSON';
  } else if (target === 'observationsRaw') {
    props().observations = ensureArray(value, 'observations');
    scrollTarget = 'observationsSection';
    appliedLabel = 'Observations JSON';
  } else if (target === 'configurationsRaw') {
    applyConfigurationsSectionJson(value);
    scrollTarget = 'configurationsSection';
    appliedLabel = 'Configurations JSON';
  } else if (target === 'proceduresRaw') {
    applyProceduresSectionJson(value);
    scrollTarget = 'proceduresSection';
    appliedLabel = 'Procedures and schedules JSON';
  } else if (target === 'instrumentsRaw') {
    props().instruments = ensureArray(value, 'instruments');
    scrollTarget = 'instrumentsSection';
    appliedLabel = 'Instruments JSON';
  } else if (target === 'contactsRaw') {
    props().contacts = ensureArray(value, 'contacts');
    scrollTarget = 'contactsSection';
    appliedLabel = 'Contacts JSON';
  } else if (target?.startsWith('item:')) {
    const [, kind, indexText] = target.split(':');
    const index = Number(indexText);
    const section = getSectionForKind(kind);
    if (!Number.isInteger(index) || index < 0 || index >= section.length) {
      throw new Error(`Cannot apply ${kind} JSON: item ${indexText} no longer exists.`);
    }
    section.splice(index, 1, value);
    scrollTarget = itemDomId(kind, index);
    appliedLabel = `${kind} JSON`;
  } else if (target?.startsWith('config:')) {
    const [, seriesText, configText] = target.split(':');
    const seriesIndex = Number(seriesText);
    const configIndex = Number(configText);
    const configs = props().observations?.[seriesIndex]?.configurations;
    if (!Array.isArray(configs) || !configs[configIndex]) {
      throw new Error(`Cannot apply Configuration JSON: configuration ${seriesText}:${configText} no longer exists.`);
    }
    configs.splice(configIndex, 1, value);
    scrollTarget = configurationDomId(seriesIndex, configIndex);
    appliedLabel = 'Configuration JSON';
  } else if (target?.startsWith('procedure:')) {
    const [, kind, seriesText, procText] = target.split(':');
    const seriesIndex = Number(seriesText);
    const procIndex = Number(procText);
    const arrayName = kind === 'observing' ? 'observingProcedures' : 'reportingProcedures';
    const procedures = props().observations?.[seriesIndex]?.[arrayName];
    if (!Array.isArray(procedures) || !procedures[procIndex]) {
      throw new Error(`Cannot apply ${arrayName} JSON: procedure ${seriesText}:${procText} no longer exists.`);
    }
    procedures.splice(procIndex, 1, value);
    scrollTarget = procedureDomId(kind, seriesIndex, procIndex);
    appliedLabel = `${arrayName} JSON`;
  } else if (target?.startsWith('schedule:')) {
    const [, indexText] = target.split(':');
    const index = Number(indexText);
    const schedules = props().schedules ??= [];
    if (!Number.isInteger(index) || index < 0 || index >= schedules.length) {
      throw new Error(`Cannot apply Schedule JSON: schedule ${indexText} no longer exists.`);
    }
    schedules.splice(index, 1, value);
    scrollTarget = `schedule-${index}`;
    appliedLabel = 'Schedule JSON';
  } else {
    throw new Error('Cannot apply JSON: no editable target is active.');
  }
  state.modalTarget = null;
  if (scrollTarget) state.pendingScrollTarget = scrollTarget;
  $('jsonModal').close();
  renderAll();
  setStatus(`${appliedLabel} applied. Save changes or validate to persist it to the server-side record.`, 'warning');
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
$('addObservationBtn').addEventListener('click', () => addItem('observations'));
$('addInstrumentBtn').addEventListener('click', () => addItem('instrument'));
$('addContactBtn').addEventListener('click', () => addItem('contact'));
$('addTemporalGeometryBtn').addEventListener('click', () => addTemporalGeometryRow());
$('addTerritoryBtn').addEventListener('click', () => addFacilityCollectionRow('territory'));
$('addEnvironmentBtn').addEventListener('click', () => addFacilityCollectionRow('environment'));
$('addFacilityLinkBtn').addEventListener('click', () => addFacilityCollectionRow('facilityLink'));
$('addScheduleBtn').addEventListener('click', () => addSchedule());
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
if (oldAddDeployment) oldAddDeployment.addEventListener('click', () => alert('WMDR2 v0.4.0 no longer has facility-level deployments. Use configurations instead.'));

document.addEventListener('toggle', event => {
  const section = event.target;
  if (section?.matches?.('details.card') && section.open) closeOtherTopLevelSections(section);
}, true);

document.body.addEventListener('focusout', event => {
  const select = event.target.closest?.('.chip-add-select');
  if (!select) return;
  window.setTimeout(() => {
    if (!select.value && !select.contains(document.activeElement)) hideChipAddSelect(select);
  }, 120);
});

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

  const addVocabButton = event.target.closest('[data-toggle-add-vocab-target]');
  if (addVocabButton) {
    showChipAddSelect(addVocabButton, 'select[data-add-vocab-target]');
    return;
  }

  const addRefButton = event.target.closest('[data-toggle-add-ref-target]');
  if (addRefButton) {
    showChipAddSelect(addRefButton, 'select[data-add-ref-target]');
    return;
  }

  const removeVocab = event.target.closest('[data-remove-vocab-target]');
  if (removeVocab) {
    if (removeVocabularyChoice(removeVocab)) {
      syncFacilityForm();
      syncItemForms();
      renderAll();
    }
    return;
  }


  const removeText = event.target.closest('[data-remove-text-target]');
  if (removeText) {
    if (removeTextChoice(removeText)) {
      syncFacilityForm();
      syncItemForms();
      renderAll();
    }
    return;
  }

  const removeRef = event.target.closest('[data-remove-ref-target]');
  if (removeRef) {
    if (removeReferenceChoice(removeRef)) {
      syncFacilityForm();
      syncItemForms();
      renderAll();
    }
    return;
  }

  const deleteFacilityRow = event.target.closest('[data-delete-facility-row]');
  if (deleteFacilityRow) {
    const [kind, indexText] = deleteFacilityRow.dataset.deleteFacilityRow.split(':');
    deleteFacilityCollectionRow(kind, Number(indexText));
    return;
  }

  const addProcedureButton = event.target.closest('[data-add-procedure]');
  if (addProcedureButton) {
    const [kind, seriesText] = addProcedureButton.dataset.addProcedure.split(':');
    addProcedure(kind, Number(seriesText));
    return;
  }

  const deleteProcedureButton = event.target.closest('[data-delete-procedure]');
  if (deleteProcedureButton) {
    const [kind, seriesText, procText] = deleteProcedureButton.dataset.deleteProcedure.split(':');
    deleteProcedure(kind, Number(seriesText), Number(procText));
    return;
  }

  const deleteScheduleButton = event.target.closest('[data-delete-schedule]');
  if (deleteScheduleButton) {
    deleteSchedule(Number(deleteScheduleButton.dataset.deleteSchedule));
    return;
  }

  const addObsInstrument = event.target.closest('[data-add-observation-instrument]');
  if (addObsInstrument) {
    addInstrumentForObservations(Number(addObsInstrument.dataset.addObservationInstrument));
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
      facilityRaw: ['Facility JSON', { id: state.record.id, geometry: state.record.geometry, temporalGeometry: state.record.temporalGeometry, time: state.record.time, conformsTo: state.record.conformsTo, properties: omit(props(), ['observations', 'instruments', 'contacts', 'schedules']) }],
      observationsRaw: ['Observations JSON', props().observations ?? []],
      configurationsRaw: ['Configurations JSON', configurationsSectionJson()],
      proceduresRaw: ['Procedures and schedules JSON', proceduresSectionJson()],
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
    openModal(`config:${seriesIndex}:${configIndex}`, 'Configuration JSON', props().observations[seriesIndex].configurations[configIndex]);
  }

  const jsonProcedureButton = event.target.closest('[data-json-procedure]');
  if (jsonProcedureButton) {
    syncFacilityForm();
    syncItemForms();
    const [kind, seriesText, procText] = jsonProcedureButton.dataset.jsonProcedure.split(':');
    const seriesIndex = Number(seriesText);
    const procIndex = Number(procText);
    const obs = props().observations[seriesIndex];
    const arrayName = kind === 'observing' ? 'observingProcedures' : 'reportingProcedures';
    openModal(`procedure:${kind}:${seriesIndex}:${procIndex}`, `${arrayName} JSON`, obs[arrayName][procIndex]);
  }

  const jsonScheduleButton = event.target.closest('[data-json-schedule]');
  if (jsonScheduleButton) {
    syncFacilityForm();
    syncItemForms();
    const index = Number(jsonScheduleButton.dataset.jsonSchedule);
    openModal(`schedule:${index}`, 'Schedule JSON', props().schedules[index]);
  }
});


document.body.addEventListener('keydown', event => {
  const addTextInput = event.target.closest?.('[data-add-text-target]');
  if (!addTextInput || event.key !== 'Enter') return;
  event.preventDefault();
  if (appendTextChoice(addTextInput)) {
    syncFacilityForm();
    syncItemForms();
    renderAll();
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
  const refAppend = event.target.closest?.('select[data-add-ref-target]');
  if (refAppend) {
    if (appendReferenceChoice(refAppend)) {
      syncFacilityForm();
      syncItemForms();
      renderAll();
    }
    return;
  }

  const vocabAppend = event.target.closest?.('select[data-add-vocab-target]');
  if (vocabAppend) {
    if (appendVocabularyChoice(vocabAppend)) {
      syncFacilityForm();
      syncItemForms();
      renderAll();
    }
    return;
  }

  const changedByCalendar = applyDatePickerValue(event);
  if (!state.record) return;
  if (!changedByCalendar && (event.target.matches?.('input[data-date-text], input[data-field="time.interval.0"], input[data-field="time.interval.1"]'))) {
    syncDatePickerFromTextInput(event.target);
  }
  const field = event.target?.dataset?.field;
  if (!field) return;

  if (event.target.matches?.('[data-environment-surface-cover-scheme]')) {
    updateSurfaceCoverValueSelectForScheme(event.target);
  }

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
