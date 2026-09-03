const NORMS_API_BASE = 'http://127.0.0.1:8000/api/norms';
var normsPollTimers = {};
if (!Array.isArray(window.normsData)) window.normsData = [];

function getNormsData() { return window.normsData; }
function setNormsData(value) { window.normsData = Array.isArray(value) ? value : []; }
function getNormByIdLocal(id) { return getNormsData().find(function (n) { return String(n.id) === String(id); }); }
function esc(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;').replace(/'/g, '&#039;');
}
function toast(message, type) {
  if (typeof window.showToast === 'function') window.showToast(message, type || 'info');
  else console.log('[Norms]', message);
}

function changeNumberFromFilename(filename) {
  var stem = String(filename || '').replace(/[_-]+/g, ' ');
  var match = stem.match(/(?:\bизм(?:енение|енения)?\.?|\bизменени[ея]|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
  return match ? match[1] : null;
}
function versionFilename(version) {
  return String((version && (version.original_filename || version.filename)) || '').trim();
}
function versionChangeNumber(version) {
  if (version && version.change_number != null && String(version.change_number).trim() !== '') return String(version.change_number).trim();
  return changeNumberFromFilename(versionFilename(version));
}

// The API is the source of truth: status=current means this version is the
// selected current edition. Older code additionally required a frontend-only
// flag, which made the current version invisible in the card title.
function isUserCurrent(version) {
  return !!(version && String(version.status || '').toLowerCase() === 'current');
}
function versionLabel(version) {
  var change = versionChangeNumber(version);
  return (change === null ? 'Без изменений' : 'Изменение №' + change)
    + (isUserCurrent(version) ? ' · действующая' : ' · архивная');
}
function isIndexed(version) {
  var p = version && version.processing || {};
  return !!(p.vector_index && p.vector_metadata);
}
function isIndexing(version) {
  return !!(version && version.processing && version.processing.indexing);
}
function findVersion(norm, sourceId, versionId) {
  var versions = norm && Array.isArray(norm.versions) ? norm.versions : [];
  return versions.find(function (v) {
    return String(v.version_id || v.id) === String(versionId) && String(v.document_id || sourceId) === String(sourceId);
  }) || versions.find(function (v) { return String(v.version_id || v.id) === String(versionId); });
}
function pdfUrl(sourceId, versionId) {
  return NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '/' + encodeURIComponent(versionId) + '/pdf';
}
function searchIcon() {
  return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path></svg>';
}
function formatDisplayDate(value) {
  var text = String(value || '').trim();
  if (!text) return 'Дата не указана';
  var match = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? match[3] + '.' + match[2] + '.' + match[1] : text;
}
function renderIndexAction(norm, version) {
  var sid = version.document_id || norm.id;
  var vid = version.version_id || version.id;
  if (isIndexing(version)) return '<span class="status-badge info">Происходит индексация</span>';
  if (isIndexed(version)) return '<span class="status-badge success">Индексировано</span>';
  return '<button type="button" class="btn btn-primary btn-sm norm-version-index" data-card="' + esc(norm.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Индексировать</button>';
}
function renderCurrentAction(norm, version) {
  var sid = version.document_id || norm.id;
  var vid = version.version_id || version.id;
  if (isUserCurrent(version)) return '<span class="status-badge success">Действующая редакция</span>';
  return '<button type="button" class="btn btn-secondary btn-sm norm-version-activate" data-card="' + esc(norm.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Сделать действующей</button>';
}
function renderVersionActions(norm, version) {
  var sid = version.document_id || norm.id;
  var vid = version.version_id || version.id;
  return renderIndexAction(norm, version) + renderCurrentAction(norm, version)
    + '<button type="button" class="btn btn-danger btn-sm norm-version-delete" data-card="' + esc(norm.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Удалить</button>';
}
function toggleNormVersions(id) {
  var panel = document.getElementById('normVersions-' + id);
  if (!panel) return;
  var isOpen = !panel.hasAttribute('hidden');
  panel.toggleAttribute('hidden', isOpen);
}
function renderNormVersions(norm) {
  var versions = Array.isArray(norm.versions) ? norm.versions.slice() : [];
  if (!versions.length) return '';
  versions.sort(function (a, b) {
    if (isUserCurrent(a) && !isUserCurrent(b)) return -1;
    if (!isUserCurrent(a) && isUserCurrent(b)) return 1;
    return String(b.effective_from || '').localeCompare(String(a.effective_from || ''));
  });
  var html = '<div id="normVersions-' + esc(norm.id) + '" class="norm-versions-panel" hidden>'
    + '<div class="norm-versions-title">Загруженные документы</div>';
  versions.forEach(function (version) {
    var sid = version.document_id || norm.id;
    var vid = version.version_id || version.id;
    var processing = version.processing || {};
    var filename = versionFilename(version) || 'Имя файла не указано';
    var uploadDate = version.uploaded_at || version.upload_date || version.effective_from || version.change_date;
    var pages = processing.pages_count || version.pages_count || 0;
    var viewer = '<a class="norm-version-view" href="' + esc(pdfUrl(sid, vid)) + '" target="_blank" rel="noopener" title="Открыть PDF в новой странице" aria-label="Открыть PDF в новой странице">' + searchIcon() + '</a>';
    html += '<div class="norm-version-row">'
      + '<div class="norm-version-info-block">'
      + '<div class="norm-version-label">' + esc(versionLabel(version)) + '</div>'
      + '<div class="norm-version-filename">' + viewer
      + '<span class="norm-version-file-name" title="' + esc(filename) + '">' + esc(filename) + '</span></div>'
      + '<div class="norm-version-file-date"><span class="norm-version-meta-label">Дата загрузки:</span> ' + esc(formatDisplayDate(uploadDate)) + '</div>'
      + '<div class="norm-version-pages"><span class="norm-version-meta-label">Количество страниц:</span> 📄 ' + esc(pages) + '</div>'
      + '</div><div class="norm-version-actions">' + renderVersionActions(norm, version) + '</div></div>';
  });
  return html + '</div>';
}
function renderNorms() {
  var grid = document.getElementById('normsGrid');
  if (!grid) return;
  var html = '';
  getNormsData().forEach(function (norm) {
    var versions = Array.isArray(norm.versions) ? norm.versions : [];
    var current = versions.find(isUserCurrent) || null;
    var change = current ? versionChangeNumber(current) : (norm.current_change_number != null ? String(norm.current_change_number) : null);
    var changeText = current
      ? (change === null ? ' — Без изменений' : ' — Изменение №' + esc(change))
      : ' — Действующая редакция не выбрана';
    var pages = current ? ((current.processing || {}).pages_count || current.pages_count || 0) : 0;
    var status = current
      ? (isIndexing(current) ? '<span class="status-badge info">Происходит индексация</span>' : isIndexed(current) ? '<span class="status-badge success">Индексировано</span>' : '<span class="status-badge info">Ожидает индексации</span>')
      : '<span class="status-badge info">Действующая редакция не выбрана</span>';
    html += '<div class="norm-card" data-norm-card="' + esc(norm.id) + '">'
      + '<div class="norm-card-header"><div style="flex:1;min-width:0">'
      + '<div class="norm-card-title">' + esc(norm.number || norm.id) + esc(changeText) + '</div>'
      + '<div class="norm-card-subtitle">' + esc(norm.title || norm.number || '') + '</div></div></div>'
      + '<div class="norm-card-meta"><span>📄 ' + esc(pages) + ' стр.</span><span>📦 ' + esc(versions.length) + ' верс.</span></div>'
      + '<div class="norm-card-status">' + status + '</div>'
      + '<div class="norm-card-actions"><button type="button" class="btn btn-secondary btn-sm norm-documents" data-id="' + esc(norm.id) + '">Загруженные документы</button></div>'
      + renderNormVersions(norm) + '</div>';
  });
  grid.innerHTML = html || '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нормативные документы ещё не загружены.</div>';
  grid.querySelectorAll('.norm-documents').forEach(function (button) { button.onclick = function (event) { event.preventDefault(); event.stopPropagation(); toggleNormVersions(button.dataset.id); }; });
  grid.querySelectorAll('.norm-version-index').forEach(function (button) { button.onclick = function (event) { event.preventDefault(); event.stopPropagation(); indexNormVersion(button.dataset.card, button.dataset.source, button.dataset.version); }; });
  grid.querySelectorAll('.norm-version-activate').forEach(function (button) { button.onclick = function (event) { event.preventDefault(); event.stopPropagation(); activateNormVersion(button.dataset.card, button.dataset.source, button.dataset.version); }; });
  grid.querySelectorAll('.norm-version-delete').forEach(function (button) { button.onclick = function (event) { event.preventDefault(); event.stopPropagation(); deleteNormVersion(button.dataset.card, button.dataset.source, button.dataset.version); }; });
}
async function loadNorms(expandIds) {
  try {
    var response = await fetch(NORMS_API_BASE);
    var data = {};
    try { data = await response.json(); } catch (e) {}
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    setNormsData((data.documents || []).map(function (item) {
      var processing = item.processing || {};
      return { id: item.document_id, number: item.number, title: item.title, version_id: item.version_id,
        effective_from: item.effective_from, current_change_number: item.current_change_number, current_change_date: item.current_change_date,
        status: processing.error ? 'error' : processing.indexing ? 'indexing' : processing.vector_index && processing.vector_metadata ? 'indexed' : 'pending',
        processing: processing,
        versions: (item.versions || []).map(function (version) { return Object.assign({}, version, {
          original_filename: version.original_filename || version.filename || '', filename: version.filename || version.original_filename || ''
        }); }), raw: item };
    }));
    renderNorms();
    (expandIds || []).forEach(function (id) { var panel = document.getElementById('normVersions-' + id); if (panel) panel.removeAttribute('hidden'); });
    if (typeof window.updateKnowledgeBaseCounters === 'function') window.updateKnowledgeBaseCounters();
    return getNormsData();
  } catch (error) { toast('Не удалось получить нормативную базу: ' + error.message, 'error'); return []; }
}
async function indexNormVersion(cardId, sourceId, versionId) {
  var norm = getNormByIdLocal(cardId); if (!norm) return toast('Документ не найден', 'error');
  var version = findVersion(norm, sourceId, versionId); if (!version) return toast('Версия не найдена. Обновите список.', 'error');
  if (isIndexing(version)) return;
  try {
    var response = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '/' + encodeURIComponent(versionId) + '/index', { method: 'POST' });
    var data = {}; try { data = await response.json(); } catch (e) {}
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    version.processing = version.processing || {}; version.processing.indexing = true; renderNorms();
    toast('Происходит индексация: ' + (versionFilename(version) || versionId), 'info'); pollNormStatus(cardId, sourceId, versionId);
  } catch (error) { toast('Ошибка запуска индексации: ' + error.message, 'error'); }
}
async function activateNormVersion(cardId, sourceId, versionId) {
  var norm = getNormByIdLocal(cardId); if (!norm) return toast('Документ не найден', 'error');
  var version = findVersion(norm, sourceId, versionId); if (!version) return toast('Версия не найдена. Обновите список.', 'error');
  var filename = versionFilename(version) || versionId;
  if (!confirm('Сделать версию «' + filename + '» действующей?')) return;
  try {
    var response = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '/' + encodeURIComponent(versionId) + '/activate', { method: 'POST' });
    var data = {}; try { data = await response.json(); } catch (e) {}
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    toast('Версия назначена действующей', 'success'); await loadNorms([cardId]);
  } catch (error) { toast('Ошибка смены действующей версии: ' + error.message, 'error'); }
}
function indexNorm(id) { var norm = getNormByIdLocal(id); if (!norm || !norm.version_id) return toast('Сначала назначьте действующую версию', 'error'); indexNormVersion(norm.id, norm.id, norm.version_id); }
function pollNormStatus(cardId, sourceId, versionId) {
  var key = sourceId + ':' + versionId; if (normsPollTimers[key]) clearInterval(normsPollTimers[key]);
  normsPollTimers[key] = setInterval(async function () {
    try {
      var response = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '?version_id=' + encodeURIComponent(versionId));
      var data = await response.json(); if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
      var norm = getNormByIdLocal(cardId); if (!norm) return; var version = findVersion(norm, sourceId, versionId); if (!version) return;
      version.processing = data.processing || {};
      if (version.processing.error) { clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; toast('Индексация завершилась с ошибкой: ' + version.processing.error, 'error'); }
      else if (isIndexed(version)) { clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; toast('Индексация выбранной версии завершена', 'success'); }
      renderNorms(); var panel = document.getElementById('normVersions-' + cardId); if (panel) panel.removeAttribute('hidden');
    } catch (error) { console.warn('[Norms] status', error); }
  }, 1500);
}
function indexAllNorms() { getNormsData().forEach(function (norm) { var current = (norm.versions || []).find(isUserCurrent); if (current && !isIndexing(current) && !isIndexed(current)) indexNormVersion(norm.id, norm.id, current.version_id || current.id); }); }
async function deleteNormVersion(cardId, sourceId, versionId) {
  var norm = getNormByIdLocal(cardId); var version = findVersion(norm, sourceId, versionId); if (!norm || !version) return;
  var filename = versionFilename(version) || versionId; if (!confirm('Удалить загруженный файл «' + filename + '»?')) return;
  try {
    var response = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId || cardId) + '?version_id=' + encodeURIComponent(versionId), { method: 'DELETE' });
    var data = {}; try { data = await response.json(); } catch (e) {} if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    toast('Файл удалён: ' + filename, 'success'); await loadNorms();
  } catch (error) { toast('Ошибка удаления: ' + error.message, 'error'); }
}
function deleteNorm(id) { var norm = getNormByIdLocal(id); if (norm && norm.versions && norm.versions.length) deleteNormVersion(id, norm.id, norm.versions[0].version_id || norm.versions[0].id); }
function handleNormDropzoneClick() { var input = document.createElement('input'); input.type = 'file'; input.multiple = true; input.accept = '.pdf,application/pdf'; input.onchange = function (event) { handleNormFiles(event.target.files); }; input.click(); }
function handleNormDragOver(event) { event.preventDefault(); event.stopPropagation(); if (event.currentTarget) event.currentTarget.classList.add('dragover'); }
function handleNormDragLeave(event) { event.preventDefault(); event.stopPropagation(); if (event.currentTarget) event.currentTarget.classList.remove('dragover'); }
function handleNormDrop(event) { event.preventDefault(); event.stopPropagation(); if (event.currentTarget) event.currentTarget.classList.remove('dragover'); if (event.dataTransfer && event.dataTransfer.files.length) handleNormFiles(event.dataTransfer.files); }
async function handleNormFiles(files) { var queue = Array.from(files || []); if (!queue.length) return; var ok = 0, failed = 0; for (var i = 0; i < queue.length; i++) { try { await uploadNormFile(queue[i]); ok++; } catch (error) { failed++; } } await loadNorms(); toast('Загрузка завершена: ' + ok + ' из ' + queue.length + (failed ? ' (ошибок: ' + failed + ')' : ''), failed ? 'error' : 'success'); }
async function uploadNormFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) { toast('Файл «' + file.name + '» пропущен: поддерживается только PDF.', 'error'); throw new Error('format'); }
  var form = new FormData(); form.append('file', file, file.name);
  var response = await fetch(NORMS_API_BASE + '/upload', { method: 'POST', body: form }); var data = {}; try { data = await response.json(); } catch (e) {}
  if (response.status === 409) { toast(data.detail || ('Файл «' + file.name + '» уже загружен.'), 'warning'); throw new Error('duplicate'); }
  if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
  toast('Файл «' + file.name + '» загружен. Версия ожидает выбора действующей редакции.', 'success'); return data;
}
window.renderNorms = renderNorms; window.loadNorms = loadNorms; window.indexNorm = indexNorm; window.indexAllNorms = indexAllNorms;
window.handleNormDropzoneClick = handleNormDropzoneClick; window.handleNormDragOver = handleNormDragOver; window.handleNormDragLeave = handleNormDragLeave; window.handleNormDrop = handleNormDrop;
window.handleNormFiles = handleNormFiles; window.uploadNormFile = uploadNormFile; window.deleteNorm = deleteNorm; window.toggleNormVersions = toggleNormVersions;
console.log('[VKS Expert AI][Norms] norms.js v10 loaded');
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { loadNorms(); }, { once: true }); else loadNorms();
