const state = {
  record: null,
  recordId: null,
  validation: null,
  modalTarget: null,
};

const $ = (id) => document.getElementById(id);
const asArray = (value) => Array.isArray(value) ? value : [];
const pretty = (value) => JSON.stringify(value ?? null, null, 2);

const exampleRecord = {
  type: 'Feature',
  id: 'facility:0-20000-0-06725',
  geometry: { type: 'Point', coordinates: [7.8232, 46.4204, 1540] },
  temporalGeometry: {
    type: 'MovingPoint',
    coordinates: [[7.823197, 46.420453, 1538], [7.8232, 46.4204, 1540]],
    dates: ['2000-08-17', '2024-01-17'],
    methods: [[], ['gps']],
  },
  time: { interval: ['2000-08-17', '..'] },
  conformsTo: ['http://wigos.wmo.int/spec/wmdr/2/conf/core'],
  properties: {
    type: 'facility',
    title: 'Blatten',
    description: 'Example facility for OSCAR nextGen Node PoC.',
    wmoRegion: 'europe',
    keywords: ['0-20000-0-06725', 'Blatten'],
    contacts: [
      {
        organization: 'Example NMHS',
        name: 'Station metadata office',
        roles: ['owner', 'pointOfContact'],
        emails: ['metadata@example.invalid'],
      },
    ],
    observationSeries: [
      {
        id: 'observationSeries:12006',
        title: 'Horizontal wind speed at specified distance from reference surface',
        observedProperty: 12006,
        observedFeature: { domain: 'atmosphere', domainFeature: 'near-surface-air', featureName: '10 m air' },
        observedGeometry: 'point',
        programAffiliation: ['GOSGeneral'],
        observingConfigurations: [
          { date: '2020-01-01', deployment: 'deployment:wind-10m', observingMethod: 266, operatingStatus: 'operational' },
        ],
      },
    ],
    deployments: [
      {
        id: 'deployment:wind-10m',
        referenceSurface: 'localGround',
        verticalDistanceFromReferenceSurface: { value: 10, uom: 'm' },
        instrument: 'instrument:wind-sensor-1',
        sourceOfObservation: 'automaticReading',
      },
    ],
    instruments: [
      {
        id: 'instrument:wind-sensor-1',
        manufacturer: 'Example manufacturer',
        model: 'WindSensor X',
        observingMethods: [266],
      },
    ],
    reporting: [],
    schedules: [],
  },
};

function props() {
  state.record.properties ??= { type: 'facility', title: '' };
  state.record.properties.observationSeries ??= [];
  state.record.properties.deployments ??= [];
  state.record.properties.instruments ??= [];
  state.record.properties.contacts ??= [];
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
  const response = await fetch(path, {
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

async function loadRecord(record) {
  const result = await api('/api/records', { method: 'POST', body: JSON.stringify(record) });
  state.record = result.record;
  state.recordId = result.id;
  state.validation = result.validation;
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
  $('downloadLink').href = `/api/records/${encodeURIComponent(state.record.id)}/download`;
  renderFacility();
  renderObservationSeries();
  renderDeployments();
  renderInstruments();
  renderContacts();
  $('recordRaw').value = pretty(state.record);
  renderValidation();
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
  setStatus(valid ? (warnings.length ? 'Valid with warnings' : 'Valid WMDR2') : 'Invalid WMDR2', valid ? (warnings.length ? 'warning' : 'valid') : 'invalid');
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
  form.elements.wmoRegion.value = p.wmoRegion || '';
  const coords = state.record.geometry?.coordinates || [];
  form.elements.lon.value = coords[0] ?? '';
  form.elements.lat.value = coords[1] ?? '';
  form.elements.elev.value = coords[2] ?? '';
  const interval = state.record.time?.interval || [];
  form.elements.begin.value = interval[0] ?? '';
  form.elements.end.value = interval[1] ?? '';
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
  const lon = numberOrNull(form.elements.lon.value);
  const lat = numberOrNull(form.elements.lat.value);
  const elev = numberOrNull(form.elements.elev.value);
  if (lon !== null && lat !== null) {
    const coords = elev === null ? [lon, lat] : [lon, lat, elev];
    state.record.geometry = { type: 'Point', coordinates: coords };
  }
  const begin = form.elements.begin.value.trim() || '..';
  const end = form.elements.end.value.trim() || '..';
  state.record.time = { interval: [begin, end] };
}

function renderObservationSeries() {
  const series = asArray(props().observationSeries);
  $('observationCount').textContent = series.length;
  $('observationsList').innerHTML = series.map((obs, index) => itemHtml(
    obs.id || `observationSeries:${index + 1}`,
    observationSeriesFormHtml(obs, index),
    'observationSeries',
    index,
  )).join('') || '<p class="muted">No ObservationSeries yet.</p>';
}

function observationSeriesFormHtml(obs, index) {
  return `
    <div class="item-form" data-kind="observationSeries" data-index="${index}">
      <label>ID <input data-field="id" value="${escapeAttr(obs.id || '')}" /></label>
      <label>Observed property <input data-field="observedProperty" value="${escapeAttr(obs.observedProperty ?? '')}" /></label>
      <label class="wide">Title <input data-field="title" value="${escapeAttr(obs.title || '')}" /></label>
      <label>Domain <input data-field="observedFeature.domain" value="${escapeAttr(obs.observedFeature?.domain ?? '')}" /></label>
      <label>Observed geometry <input data-field="observedGeometry" value="${escapeAttr(obs.observedGeometry ?? '')}" /></label>
      <label>Domain feature <input data-field="observedFeature.domainFeature" value="${escapeAttr(obs.observedFeature?.domainFeature ?? '')}" /></label>
      <label>Feature name <input data-field="observedFeature.featureName" value="${escapeAttr(obs.observedFeature?.featureName ?? '')}" /></label>
      <label class="wide">Program affiliations, comma-separated <input data-field="programAffiliation" value="${escapeAttr(asArray(obs.programAffiliation).join(', '))}" /></label>
    </div>
    ${observationDeploymentLinksHtml(obs)}
    ${observationContactLinksHtml(obs)}`;
}

function observationDeploymentRefs(obs) {
  return [...new Set(asArray(obs.observingConfigurations).map(c => c?.deployment).filter(Boolean))];
}

function renderDeployments() {
  const deployments = asArray(props().deployments);
  $('deploymentCount').textContent = deployments.length;
  $('deploymentsList').innerHTML = deployments.map((dep, index) => itemHtml(
    dep.id || `deployment:${index + 1}`,
    deploymentFormHtml(dep, index),
    'deployment',
    index,
  )).join('') || '<p class="muted">No deployments yet.</p>';
}

function deploymentFormHtml(dep, index) {
  return `
    <div class="item-form" data-kind="deployment" data-index="${index}">
      <label>ID <input data-field="id" value="${escapeAttr(dep.id || '')}" /></label>
      <label>Source of observation <input data-field="sourceOfObservation" value="${escapeAttr(dep.sourceOfObservation ?? '')}" /></label>
      <label>Reference surface <input data-field="referenceSurface" value="${escapeAttr(dep.referenceSurface ?? '')}" /></label>
      <label>Height value <input data-field="verticalDistanceFromReferenceSurface.value" value="${escapeAttr(dep.verticalDistanceFromReferenceSurface?.value ?? '')}" /></label>
      <label>Height uom <input data-field="verticalDistanceFromReferenceSurface.uom" value="${escapeAttr(dep.verticalDistanceFromReferenceSurface?.uom ?? '')}" /></label>
      <label class="wide">Serial number <input data-field="serialNumber" value="${escapeAttr(dep.serialNumber || '')}" /></label>
    </div>
    ${deploymentCrossLinksHtml(dep)}`;
}

function renderInstruments() {
  const instruments = asArray(props().instruments);
  $('instrumentCount').textContent = instruments.length;
  $('instrumentsList').innerHTML = instruments.map((inst, index) => itemHtml(
    inst.id || `instrument:${index + 1}`,
    instrumentFormHtml(inst, index),
    'instrument',
    index,
  )).join('') || '<p class="muted">No instruments yet.</p>';
}

function instrumentFormHtml(inst, index) {
  return `
    <div class="item-form" data-kind="instrument" data-index="${index}">
      <label>ID <input data-field="id" value="${escapeAttr(inst.id || '')}" /></label>
      <label>Title <input data-field="title" value="${escapeAttr(inst.title || '')}" /></label>
      <label>Manufacturer <input data-field="manufacturer" value="${escapeAttr(inst.manufacturer || '')}" /></label>
      <label>Model <input data-field="model" value="${escapeAttr(inst.model || '')}" /></label>
      <label>Observing methods, comma-separated <input data-field="observingMethods" value="${escapeAttr(asArray(inst.observingMethods).join(', '))}" /></label>
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
          <button data-json-item="${kind}" data-index="${index}" type="button">JSON</button>
          <button data-delete-item="${kind}" data-index="${index}" type="button">Delete</button>
        </div>
      </div>
      ${formHtml}
    </article>`;
}

function indexById(kind) {
  return new Map(getSectionForKind(kind).map((item, index) => [item?.id, index]).filter(([id]) => Boolean(id)));
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
  return contact.name || contact.organization || contact.id || `Contact ${index + 1}`;
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
  const ownerLinks = contactsWithRole('owner').map(({ contact, index }) => contactLink(contact, index));
  return xrefRow('Owner contacts', ownerLinks, 'No contact has role owner');
}

function observationContactLinksHtml(_obs) {
  const links = contactsExceptRole('owner').map(({ contact, index }) => {
    const roles = contactRoleText(contact, 'owner');
    return contactLink(contact, index, roles || undefined);
  });
  return xrefRow('Contacts by role', links, 'No non-owner contact roles available');
}

function observationDeploymentLinksHtml(obs) {
  const deploymentIndex = indexById('deployment');
  const links = observationDeploymentRefs(obs).map(ref => linkToItem('deployment', deploymentIndex.get(ref), ref));
  return xrefRow('Linked deployments', links, 'No deployment refs in observingConfigurations');
}

function observationsUsingDeployment(deploymentId) {
  if (!deploymentId) return [];
  return asArray(props().observationSeries)
    .map((obs, index) => ({ obs, index }))
    .filter(({ obs }) => observationDeploymentRefs(obs).includes(deploymentId));
}

function deploymentsUsingInstrument(instrumentId) {
  if (!instrumentId) return [];
  return asArray(props().deployments)
    .map((deployment, index) => ({ deployment, index }))
    .filter(({ deployment }) => deployment?.instrument === instrumentId);
}

function deploymentCrossLinksHtml(dep) {
  const instrumentIndex = indexById('instrument');
  const instrumentLinks = dep.instrument
    ? [linkToItem('instrument', instrumentIndex.get(dep.instrument), dep.instrument)]
    : [];
  const observationLinks = observationsUsingDeployment(dep.id).map(({ obs, index }) =>
    linkToItem('observationSeries', index, obs.id || obs.title || `ObservationSeries ${index + 1}`)
  );
  return `
    ${xrefRow('Linked instrument', instrumentLinks, 'No instrument ref')}
    ${xrefRow('Referred from ObservationSeries', observationLinks, 'No ObservationSeries refers to this deployment')}`;
}

function instrumentCrossLinksHtml(inst) {
  const deploymentLinks = deploymentsUsingInstrument(inst.id).map(({ deployment, index }) =>
    linkToItem('deployment', index, deployment.id || `Deployment ${index + 1}`)
  );
  return xrefRow('Used by deployments', deploymentLinks, 'No deployment uses this instrument');
}

function renderContacts() {
  const contacts = asArray(props().contacts);
  $('contactCount').textContent = contacts.length;
  $('contactsList').innerHTML = contacts.map((contact, index) => itemHtml(
    contact.name || contact.organization || contact.id || `contact:${index + 1}`,
    contactFormHtml(contact, index),
    'contact',
    index,
  )).join('') || '<p class="muted">No contacts yet.</p>';
}

function contactFormHtml(contact, index) {
  return `
    <div class="item-form" data-kind="contact" data-index="${index}">
      <label>ID <input data-field="id" value="${escapeAttr(contact.id || '')}" /></label>
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
  document.querySelectorAll('[data-kind]').forEach(form => {
    const kind = form.dataset.kind;
    const index = Number(form.dataset.index);
    const target = getSectionForKind(kind)[index];
    if (!target) return;
    form.querySelectorAll('[data-field]').forEach(input => {
      if (input.dataset.field === 'configurationDeployments') {
        setObservationDeploymentRefs(target, splitValues(input.value));
      } else {
        setField(target, input.dataset.field, coerceField(input.dataset.field, input.value));
      }
    });
  });
}

function getSectionForKind(kind) {
  const p = props();
  if (kind === 'observationSeries') return p.observationSeries ??= [];
  if (kind === 'deployment') return p.deployments ??= [];
  if (kind === 'instrument') return p.instruments ??= [];
  if (kind === 'contact') return p.contacts ??= [];
  throw new Error(`Unknown item type ${kind}`);
}

function setObservationDeploymentRefs(obs, refs) {
  const existing = asArray(obs.observingConfigurations);
  const currentRefs = observationDeploymentRefs(obs);
  if (refs.join('|') === currentRefs.join('|')) return;
  obs.observingConfigurations = refs.map((deployment, index) => {
    const existingConfig = existing.find(c => c?.deployment === deployment) || existing[index] || {};
    return {
      date: existingConfig.date || '..',
      deployment,
      observingMethod: existingConfig.observingMethod ?? { nilReason: 'unknown' },
      ...omit(existingConfig, ['deployment']),
    };
  });
}

function setField(obj, path, value) {
  const parts = path.split('.');
  let target = obj;
  while (parts.length > 1) {
    const key = parts.shift();
    target[key] ??= {};
    target = target[key];
  }
  const finalKey = parts[0];
  if (value === '' || (Array.isArray(value) && !value.length)) {
    delete target[finalKey];
  } else {
    target[finalKey] = value;
  }
}

function coerceField(field, value) {
  const trimmed = String(value ?? '').trim();
  if (['programAffiliation', 'observingMethods', 'roles'].includes(field)) {
    return splitValues(trimmed).map(valueOrNumber);
  }
  if (['emails', 'phones'].includes(field)) {
    return splitValues(trimmed);
  }
  if (['observedProperty', 'observedGeometry', 'sourceOfObservation'].includes(field) || field.endsWith('.domain') || field.endsWith('.value')) {
    return valueOrNumber(trimmed);
  }
  return trimmed;
}

function splitValues(value) {
  return value ? value.split(',').map(part => part.trim()).filter(Boolean) : [];
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

function addItem(kind) {
  syncFacilityForm();
  syncItemForms();
  const section = getSectionForKind(kind);
  const next = section.length + 1;
  if (kind === 'observationSeries') section.push({ id: `observationSeries:new-${next}`, observedProperty: '', observedFeature: {} });
  if (kind === 'deployment') section.push({ id: `deployment:new-${next}` });
  if (kind === 'instrument') section.push({ id: `instrument:new-${next}` });
  if (kind === 'contact') section.push({ roles: [], emails: [] });
  renderAll();
}

function deleteItem(kind, index) {
  syncFacilityForm();
  syncItemForms();
  getSectionForKind(kind).splice(index, 1);
  renderAll();
}

function openModal(target, title, value) {
  state.modalTarget = target;
  $('modalTitle').textContent = title;
  $('modalJson').value = pretty(value);
  $('jsonModal').showModal();
}

function scrollToItem(targetId) {
  const target = $(targetId);
  if (!target) return;
  const details = target.closest('details');
  if (details) details.open = true;
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  target.classList.add('flash');
  window.setTimeout(() => target.classList.remove('flash'), 1600);
}

function refreshRelationshipViews() {
  renderFacility();
  renderObservationSeries();
  renderDeployments();
  renderInstruments();
  renderContacts();
  $('recordRaw').value = pretty(state.record);
}

function applyModal() {
  const value = parseJson($('modalJson').value, $('modalTitle').textContent);
  const target = state.modalTarget;
  if (target === 'facilityRaw') {
    Object.assign(state.record, pick(value, ['id', 'geometry', 'temporalGeometry', 'time', 'conformsTo']));
    Object.assign(props(), omit(value.properties ? value.properties : value, ['observationSeries', 'deployments', 'instruments', 'contacts', 'schedules', 'reporting']));
  } else if (target === 'observationSeriesRaw') props().observationSeries = ensureArray(value, 'observationSeries');
  else if (target === 'deploymentsRaw') props().deployments = ensureArray(value, 'deployments');
  else if (target === 'instrumentsRaw') props().instruments = ensureArray(value, 'instruments');
  else if (target === 'contactsRaw') props().contacts = ensureArray(value, 'contacts');
  else if (target?.startsWith('item:')) {
    const [, kind, indexText] = target.split(':');
    getSectionForKind(kind)[Number(indexText)] = value;
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

$('fileInput').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const form = new FormData();
    form.append('file', file);
    const result = await api('/api/records', { method: 'POST', body: form });
    state.record = result.record;
    state.recordId = result.id;
    state.validation = result.validation;
    renderAll();
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
$('saveBtn').addEventListener('click', () => saveFullRecord().catch(error => alert(error.message)));
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
$('addDeploymentBtn').addEventListener('click', () => addItem('deployment'));
$('addInstrumentBtn').addEventListener('click', () => addItem('instrument'));
$('addContactBtn').addEventListener('click', () => addItem('contact'));
$('modalCancelBtn').addEventListener('click', () => $('jsonModal').close());
$('modalApplyBtn').addEventListener('click', () => {
  try { applyModal(); } catch (error) { alert(error.message); }
});

document.body.addEventListener('click', event => {
  const xref = event.target.closest('[data-scroll-target]');
  if (xref) {
    event.preventDefault();
    scrollToItem(xref.dataset.scrollTarget);
    return;
  }

  const open = event.target.closest('[data-open-modal]');
  if (open) {
    if (!state.record) return;
    syncFacilityForm();
    syncItemForms();
    const target = open.dataset.openModal;
    const mapping = {
      facilityRaw: ['Facility JSON', { id: state.record.id, geometry: state.record.geometry, temporalGeometry: state.record.temporalGeometry, time: state.record.time, conformsTo: state.record.conformsTo, properties: omit(props(), ['observationSeries', 'deployments', 'instruments', 'contacts', 'schedules', 'reporting']) }],
      observationSeriesRaw: ['ObservationSeries JSON', props().observationSeries ?? []],
      deploymentsRaw: ['Deployments JSON', props().deployments ?? []],
      instrumentsRaw: ['Instruments JSON', props().instruments ?? []],
      contactsRaw: ['Contacts JSON', props().contacts ?? []],
    };
    openModal(target, mapping[target][0], mapping[target][1]);
  }

  const deleteButton = event.target.closest('[data-delete-item]');
  if (deleteButton) deleteItem(deleteButton.dataset.deleteItem, Number(deleteButton.dataset.index));

  const jsonButton = event.target.closest('[data-json-item]');
  if (jsonButton) {
    syncFacilityForm();
    syncItemForms();
    const kind = jsonButton.dataset.jsonItem;
    const index = Number(jsonButton.dataset.index);
    openModal(`item:${kind}:${index}`, `${kind} JSON`, getSectionForKind(kind)[index]);
  }
});

document.body.addEventListener('input', event => {
  if (!state.record) return;
  if (event.target.closest('#facilityForm') || event.target.closest('[data-kind]')) {
    syncFacilityForm();
    syncItemForms();
    $('recordRaw').value = pretty(state.record);
    $('recordTitle').textContent = props().title || state.record.id || 'Untitled facility';
    $('recordId').textContent = state.record.id || 'No id';
    $('downloadLink').href = `/api/records/${encodeURIComponent(state.record.id)}/download`;
  }
});

document.body.addEventListener('change', event => {
  if (!state.record) return;
  const field = event.target?.dataset?.field;
  if (!field) return;
  if (['configurationDeployments', 'instrument', 'id', 'roles', 'name', 'organization'].includes(field)) {
    syncFacilityForm();
    syncItemForms();
    refreshRelationshipViews();
  }
});
