const NORMS_API_BASE = 'http://127.0.0.1:8000/api/norms';
var normsPollTimers = {};
if (!Array.isArray(window.normsData)) window.normsData = [];
function getNormsData() { return window.normsData; }
function setNormsData(v) { window.normsData = Array.isArray(v) ? v : []; }
function getNormByIdLocal(id) { return getNormsData().find(function (n) { return String(n.id) === String(id); }); }
function esc(v) { return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;').replace(/'/g, '&#039;'); }
function toast(m, t) { if (typeof window.showToast === 'function') window.showToast(m, t || 'info'); else console.log('[Norms]', m); }
function changeNumberFromFilename(filename) {
  var stem = String(filename || '').replace(/[_-]+/g, ' ');
  var match = stem.match(/(?:\bизм\.?|\bизменени(?:е|я)|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
  return match ? match[1] : null;
}
function versionLabel(v) {
  var suffix = v.status === 'current' ? ' · действующая' : ' · архивная';
  var filename = String(v.original_filename || v.filename || '');
  var change = changeNumberFromFilename(filename);
  if (change !== null) return 'Изменение №' + esc(change) + suffix;
  return 'Без изменений' + suffix;
}
function indexed(v) { var p = v && v.processing || {}; return !!(p.vector_index && p.vector_metadata); }
function indexing(v) { return !!(v && v.processing && v.processing.indexing); }
function toggleNormVersions(id) { var p = document.getElementById('normVersions-' + id); if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none'; }
function pdfUrl(sourceId, versionId) { return NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '/' + encodeURIComponent(versionId) + '/pdf'; }
function findVersion(n, sourceId, versionId) { var vs = n && Array.isArray(n.versions) ? n.versions : []; return vs.find(function (v) { return String(v.version_id || v.id) === String(versionId); }); }
function searchIcon() { return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path></svg>'; }
function renderVersionActions(n, v, sid, vid) {
  var state = indexing(v) ? '<span class="status-badge info">Происходит индексация</span>' : indexed(v) ? '<span class="status-badge success">Индексировано</span>' : '<button type="button" class="btn btn-primary btn-sm norm-version-index" data-card="' + esc(n.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Индексировать</button>';
  var active = v.status === 'current' ? '<span class="status-badge success">Действующая редакция</span>' : '<button type="button" class="btn btn-secondary btn-sm norm-version-activate" data-card="' + esc(n.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Сделать действующей</button>';
  var del = '<button type="button" class="btn btn-danger btn-sm norm-version-delete" data-card="' + esc(n.id) + '" data-source="' + esc(sid) + '" data-version="' + esc(vid) + '">Удалить</button>';
  return state + active + del;
}
function renderNormVersions(n) {
  var vs = Array.isArray(n.versions) ? n.versions.slice() : [];
  if (!vs.length) return '';
  vs.sort(function (a, b) { if (a.status === 'current') return -1; if (b.status === 'current') return 1; return String(b.effective_from || '').localeCompare(String(a.effective_from || '')); });
  var h = '<div id="normVersions-' + esc(n.id) + '" class="norm-versions-panel" style="display:none"><div class="norm-versions-title">Загруженные документы</div>';
  vs.forEach(function (v) {
    var sid = v.document_id || n.id, vid = v.version_id || v.id, p = v.processing || {}, date = v.change_date || v.effective_from || 'Дата не указана', pages = p.pages_count || v.pages_count || 0;
    var filename = v.original_filename || v.filename || vid;
    var viewer = '<a class="norm-version-view" href="' + esc(pdfUrl(sid, vid)) + '" target="_blank" rel="noopener" title="Открыть PDF в новой странице" aria-label="Открыть PDF в новой странице">' + searchIcon() + '</a>';
    h += '<div class="norm-version-row"><div class="norm-version-info-block"><strong>' + versionLabel(v) + '</strong><div class="norm-version-filename"><span class="norm-version-file-date">' + esc(date) + ' · </span>' + viewer + '<span class="norm-version-file-name" title="' + esc(filename) + '">' + esc(filename) + '</span></div><div class="norm-version-pages">📄 ' + pages + ' стр.</div></div><div class="norm-version-actions">' + renderVersionActions(n, v, sid, vid) + '</div></div>';
  });
  return h + '</div>';
}
function renderNorms() {
  var grid = document.getElementById('normsGrid'); if (!grid) return;
  var ns = getNormsData(), h = '';
  ns.forEach(function (n) {
    var p = n.processing || {}, cv = (n.versions || []).find(function (v) { return v.status === 'current'; });
    var pages = cv ? ((cv.processing || {}).pages_count || cv.pages_count || 0) : p.pages_count || 0;
    var currentFilename = cv ? (cv.original_filename || cv.filename || '') : '';
    var currentChange = changeNumberFromFilename(currentFilename);
    var change = cv ? (currentChange !== null ? ' — Изменение №' + esc(currentChange) : ' — Без изменений') : '';
    var status = cv ? (indexing(cv) ? '<span class="status-badge info">Происходит индексация</span>' : indexed(cv) ? '<span class="status-badge success">Индексировано</span>' : '<span class="status-badge info">Ожидает индексации</span>') : '<span class="status-badge info">Действующая редакция не выбрана</span>';
    h += '<div class="norm-card" data-norm-card="' + esc(n.id) + '"><div class="norm-card-header" data-card-toggle="' + esc(n.id) + '"><div style="flex:1;min-width:0"><div class="norm-card-title">' + esc(n.number || n.id) + change + '</div><div class="norm-card-subtitle">' + esc(n.title || n.number || '') + '</div></div></div><div class="norm-card-meta"><span>📄 ' + pages + ' стр.</span><span>📦 ' + ((n.versions || []).length) + ' верс.</span></div><div style="margin-top:8px">' + status + '</div><div class="norm-card-actions"><button type="button" class="btn btn-secondary btn-sm norm-documents" data-id="' + esc(n.id) + '">Загруженные документы</button></div>' + renderNormVersions(n) + '</div>';
  });
  grid.innerHTML = h;
  grid.querySelectorAll('[data-card-toggle]').forEach(function (x) { x.onclick = function () { toggleNormVersions(x.dataset.cardToggle); }; });
  grid.querySelectorAll('.norm-documents').forEach(function (b) { b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); toggleNormVersions(b.dataset.id); }; });
  grid.querySelectorAll('.norm-version-index').forEach(function (b) { b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); indexNormVersion(b.dataset.card, b.dataset.source, b.dataset.version); }; });
  grid.querySelectorAll('.norm-version-activate').forEach(function (b) { b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); activateNormVersion(b.dataset.card, b.dataset.source, b.dataset.version); }; });
  grid.querySelectorAll('.norm-version-delete').forEach(function (b) { b.onclick = function (e) { e.preventDefault(); e.stopPropagation(); deleteNormVersion(b.dataset.card, b.dataset.source, b.dataset.version); }; });
}
async function loadNorms(expandIds) {
  try {
    var r = await fetch(NORMS_API_BASE), d = await r.json();
    if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status));
    setNormsData((d.documents || []).map(function (x) { var p = x.processing || {}; return { id: x.document_id, number: x.number, title: x.title, effective_from: x.effective_from, current_change_number: x.current_change_number, current_change_date: x.current_change_date, status: p.error ? 'error' : p.indexing ? 'indexing' : p.vector_index && p.vector_metadata ? 'indexed' : 'pending', version_id: x.version_id, versions: x.versions || [], processing: p, raw: x }; }));
    renderNorms();
    (expandIds || []).forEach(function (id) { var el = document.getElementById('normVersions-' + id); if (el) el.style.display = 'block'; });
    if (typeof window.updateKnowledgeBaseCounters === 'function') window.updateKnowledgeBaseCounters();
    return getNormsData();
  } catch (e) { toast('Не удалось получить нормативную базу: ' + e.message, 'error'); return []; }
}
function indexNormVersion(cardId, sourceId, versionId) {
  var n = getNormByIdLocal(cardId); if (!n) return toast('Документ не найден', 'error');
  var v = findVersion(n, sourceId, versionId); if (!v) return toast('Выбранная версия не найдена. Обновите список.', 'error');
  var sid = v.document_id || sourceId || cardId, vid = v.version_id || v.id;
  fetch(NORMS_API_BASE + '/' + encodeURIComponent(sid) + '/' + encodeURIComponent(vid) + '/index', { method: 'POST' }).then(async function (r) { var d = {}; try { d = await r.json(); } catch (e) {} if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status)); v.processing = v.processing || {}; v.processing.indexing = true; return d; }).then(function () { toast('Происходит индексация: ' + (v.original_filename || v.filename || vid), 'info'); renderNorms(); pollNormStatus(cardId, sid, vid); }).catch(function (e) { toast('Ошибка запуска индексации: ' + e.message, 'error'); });
}
function activateNormVersion(cardId, sourceId, versionId) {
  var n = getNormByIdLocal(cardId); if (!n) return toast('Документ не найден', 'error');
  var v = findVersion(n, sourceId, versionId); if (!v) return toast('Выбранная версия не найдена. Обновите список.', 'error');
  var sid = v.document_id || sourceId || cardId, vid = v.version_id || v.id;
  if (!confirm('Сделать версию «' + (v.original_filename || v.filename || vid) + '» действующей?')) return;
  fetch(NORMS_API_BASE + '/' + encodeURIComponent(sid) + '/' + encodeURIComponent(vid) + '/activate', { method: 'POST' }).then(async function (r) { var d = {}; try { d = await r.json(); } catch (e) {} if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status)); return d; }).then(function () { toast('Версия назначена действующей', 'success'); return loadNorms([cardId]); }).catch(function (e) { toast('Ошибка смены действующей версии: ' + e.message, 'error'); });
}
function indexNorm(id) { var n = getNormByIdLocal(id); if (!n || !n.version_id) return toast('Сначала назначьте действующую версию', 'error'); var v = findVersion(n, n.id, n.version_id); if (v && indexing(v)) return; indexNormVersion(n.id, n.id, n.version_id); }
function pollNormStatus(cardId, sourceId, versionId) {
  var key = sourceId + ':' + versionId; if (normsPollTimers[key]) clearInterval(normsPollTimers[key]);
  normsPollTimers[key] = setInterval(async function () { try { var r = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId) + '?version_id=' + encodeURIComponent(versionId)); var d = await r.json(); var n = getNormByIdLocal(cardId); if (!n) { clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; return; } var v = findVersion(n, sourceId, versionId); if (v) v.processing = d.processing || {}; if (v && v.processing && v.processing.error) { clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; toast('Индексация завершилась с ошибкой: ' + v.processing.error, 'error'); } else if (v && indexed(v)) { clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; toast('Индексация выбранной версии завершена', 'success'); } renderNorms(); var panel = document.getElementById('normVersions-' + cardId); if (panel) panel.style.display = 'block'; } catch (e) { console.warn('[Norms] status', e); } }, 1500);
}
function indexAllNorms() { getNormsData().forEach(function (n) { if (n.version_id) { var v = findVersion(n, n.id, n.version_id); if (v && !indexing(v) && !indexed(v)) indexNorm(n.id); } }); }
async function deleteNormVersion(cardId, sourceId, versionId) {
  var n = getNormByIdLocal(cardId), v = findVersion(n, sourceId, versionId); if (!n || !v) return;
  var name = v.original_filename || v.filename || versionId;
  if (!confirm('Удалить загруженный файл «' + name + '»?')) return;
  try { var r = await fetch(NORMS_API_BASE + '/' + encodeURIComponent(sourceId || cardId) + '?version_id=' + encodeURIComponent(versionId), { method: 'DELETE' }); var d = {}; try { d = await r.json(); } catch (e) {} if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status)); toast('Файл удалён: ' + name, 'success'); await loadNorms(); } catch (e) { toast('Ошибка удаления: ' + e.message, 'error'); }
}
function deleteNorm(id) { var n = getNormByIdLocal(id); if (n && n.versions && n.versions.length) deleteNormVersion(id, n.id, n.versions[0].version_id || n.versions[0].id); }
function handleNormDropzoneClick() { var i = document.createElement('input'); i.type = 'file'; i.multiple = true; i.accept = '.pdf,application/pdf'; i.onchange = function (e) { handleNormFiles(e.target.files); }; i.click(); }
function handleNormDragOver(e) { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.add('dragover'); }
function handleNormDragLeave(e) { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.remove('dragover'); }
function handleNormDrop(e) { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.remove('dragover'); if (e.dataTransfer.files.length) handleNormFiles(e.dataTransfer.files); }
async function handleNormFiles(files) { var queue = Array.from(files || []), ok = 0, failed = 0; for (var i = 0; i < queue.length; i++) { try { await uploadNormFile(queue[i]); ok++; } catch (e) { failed++; } } await loadNorms(); if (queue.length > 1) toast('Загрузка завершена: ' + ok + ' из ' + queue.length + (failed ? ' (ошибок: ' + failed + ')' : ''), failed ? 'error' : 'success'); }
async function uploadNormFile(file) {
  var maxSize = 50 * 1024 * 1024;
  if (!file.name.toLowerCase().endsWith('.pdf')) { toast('Файл «' + file.name + '» пропущен: поддерживается только PDF.', 'error'); throw new Error('unsupported format'); }
  if (file.size > maxSize) { toast('Файл «' + file.name + '» пропущен: размер превышает 50 МБ.', 'error'); throw new Error('file too large'); }
  var f = new FormData(); f.append('file', file, file.name);
  try { var r = await fetch(NORMS_API_BASE + '/upload', { method: 'POST', body: f }); var d = {}; try { d = await r.json(); } catch (e) {} if (!r.ok) { var err = new Error(d.detail || ('HTTP ' + r.status)); err.status = r.status; throw err; } toast('Версия загружена: ' + (d.filename || file.name), 'success'); return d; } catch (e) { toast(e.status === 409 ? ('Файл уже загружен: ' + e.message) : 'Ошибка загрузки «' + file.name + '»: ' + e.message, 'error'); throw e; }
}
window.renderNorms = renderNorms; window.loadNorms = loadNorms; window.handleNormDropzoneClick = handleNormDropzoneClick; window.handleNormDragOver = handleNormDragOver; window.handleNormDragLeave = handleNormDragLeave; window.handleNormDrop = handleNormDrop; window.handleNormFiles = handleNormFiles; window.uploadNormFile = uploadNormFile; window.indexNorm = indexNorm; window.indexNormVersion = indexNormVersion; window.activateNormVersion = activateNormVersion; window.pollNormStatus = pollNormStatus; window.indexAllNorms = indexAllNorms; window.deleteNorm = deleteNorm; window.deleteNormVersion = deleteNormVersion;
