// ============================================================
// Project Expert AI — DOCUMENTATION
// Реальная загрузка PDF + существующий PDFPageProcessor.
// ============================================================

const DOCUMENTS_API_BASE = 'http://127.0.0.1:8000/api/documents';
const CHECKS_API_BASE = 'http://127.0.0.1:8000/api/checks';
var documentPollTimers = {};

function renderDocs() {
  var list = document.getElementById('docsList');
  if (!list) return;

  var selectAllLabel = document.getElementById('selectAllLabel');
  if (selectAllLabel) selectAllLabel.textContent = 'Выбрать все' + (docsData.length ? ' (' + docsData.length + ')' : '');

  if (!docsData.length) {
    list.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет документов. Перетащите PDF или нажмите на зону загрузки.</div>';
    return;
  }

  var html = '';
  docsData.forEach(function(doc) {
    var processing = doc.processing || {};
    var statusClass = doc.status === 'processed' ? 'success' : doc.status === 'error' ? 'danger' : 'info';
    var statusText = doc.status === 'processed' ? 'Обработан' : doc.status === 'error' ? 'Ошибка' : 'Обработка';
    var id = escapeHtml(String(doc.id));
    html += '<div class="doc-item">';
    html += '<input type="checkbox" class="doc-checkbox" ' + (doc.checked ? 'checked' : '') + ' onchange="toggleDocCheck(\'' + id + '\')">';
    html += '<div class="doc-icon">📄</div><div class="doc-info">';
    html += '<div class="doc-name">' + escapeHtml(doc.filename || doc.name || '') + '</div>';
    html += '<div class="doc-meta"><span>' + escapeHtml(doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : '') + '</span><span>' + (processing.pages_count || doc.pages || 0) + ' стр.</span></div>';
    if (doc.status === 'error') html += '<div style="margin-top:6px;color:#dc2626;font-size:12px;">' + escapeHtml(doc.error || 'Ошибка обработки') + '</div>';
    html += '</div><div class="doc-actions">';
    html += '<span class="status-badge ' + statusClass + '">' + statusText + '</span>';
    if (doc.status === 'processing') html += '<span style="font-size:12px;color:var(--text-secondary);">' + (processing.pages_count || 0) + ' стр.</span>';
    if (doc.status === 'processed') html += '<button class="btn btn-primary btn-sm" onclick="checkDocument(\'' + id + '\')">Проверить</button>';
    html += '<button class="delete-btn" onclick="deleteDoc(\'' + id + '\')" title="Удалить">🗑</button>';
    html += '</div></div>';
  });
  list.innerHTML = html;
}

async function loadDocs() {
  try {
    var response = await fetch(DOCUMENTS_API_BASE);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    var data = await response.json();
    docsData = (data.documents || []).map(function(item) {
      return Object.assign({}, item, { checked: false });
    });
    renderDocs();
    updateBadges();
  } catch (error) {
    console.error('[Project Expert AI][Documents] Load error:', error);
  }
}

function handleDocsDropzoneClick() {
  var input = document.createElement('input');
  input.type = 'file'; input.multiple = true; input.accept = '.pdf,application/pdf';
  input.addEventListener('change', function(e) { if (e.target.files.length) handleDocFiles(e.target.files); });
  input.click();
}

function handleDocDragOver(event) { event.preventDefault(); event.currentTarget.classList.add('dragover'); }
function handleDocDragLeave(event) { event.preventDefault(); event.currentTarget.classList.remove('dragover'); }
function handleDocDrop(event) { event.preventDefault(); event.currentTarget.classList.remove('dragover'); if (event.dataTransfer.files.length) handleDocFiles(event.dataTransfer.files); }

function handleDocFiles(files) {
  Array.from(files).forEach(uploadDocFile);
}

async function uploadDocFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Для проектной документации поддерживается только PDF', 'error'); return;
  }
  if (file.size > 100 * 1024 * 1024) {
    showToast('Размер PDF не должен превышать 100 МБ', 'error'); return;
  }
  var form = new FormData(); form.append('file', file, file.name);
  try {
    var response = await fetch(DOCUMENTS_API_BASE + '/upload', { method: 'POST', body: form });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    showToast('Документ загружен. Начата обработка.', 'success');
    await loadDocs();
    pollDocument(data.id);
  } catch (error) {
    console.error('[Project Expert AI][Documents] Upload error:', error);
    showToast('Ошибка загрузки: ' + error.message, 'error');
  }
}

function pollDocument(id) {
  if (documentPollTimers[id]) clearInterval(documentPollTimers[id]);
  documentPollTimers[id] = setInterval(async function() {
    try {
      var response = await fetch(DOCUMENTS_API_BASE + '/' + encodeURIComponent(id));
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      var index = docsData.findIndex(function(d) { return d.id === id; });
      if (index >= 0) docsData[index] = Object.assign({}, data, { checked: docsData[index].checked });
      renderDocs();
      if (data.status === 'processed' || data.status === 'error') {
        clearInterval(documentPollTimers[id]); delete documentPollTimers[id];
        if (data.status === 'processed') showToast('Обработка завершена: ' + (data.pages || 0) + ' страниц', 'success');
        else showToast('Ошибка обработки документа', 'error');
      }
    } catch (error) { console.warn('[Project Expert AI][Documents] Status error:', error); }
  }, 2000);
}

function deleteDoc(id) {
  var doc = docsData.find(function(d) { return d.id === id; });
  if (!doc || !confirm('Удалить документ «' + (doc.filename || doc.name || '') + '»?')) return;
  fetch(DOCUMENTS_API_BASE + '/' + encodeURIComponent(id), { method: 'DELETE' })
    .then(function(r) { return r.json().then(function(d) { if (!r.ok) throw new Error(d.detail || ('HTTP ' + r.status)); return d; }); })
    .then(function() { docsData = docsData.filter(function(d) { return d.id !== id; }); renderDocs(); updateBadges(); showToast('Документ удалён', 'success'); })
    .catch(function(error) { showToast('Ошибка удаления: ' + error.message, 'error'); });
}

function toggleDocCheck(id) {
  var doc = docsData.find(function(d) { return String(d.id) === String(id); });
  if (!doc) return; doc.checked = !doc.checked; renderDocs();
}

function toggleSelectAllDocs() {
  var checkbox = document.getElementById('selectAllDocs');
  if (!checkbox) return;
  docsData.forEach(function(doc) { doc.checked = checkbox.checked; }); renderDocs();
}

async function checkDocument(id) {
  var doc = docsData.find(function(d) { return String(d.id) === String(id); });
  if (!doc || doc.status !== 'processed') { showToast('Документ ещё не готов к проверке', 'error'); return; }
  showToast('LM Studio выполняет инженерную проверку…', 'info');
  try {
    var response = await fetch(CHECKS_API_BASE + '/' + encodeURIComponent(id), { method: 'POST' });
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    var results = data.results || [];
    results.forEach(function(item) { item.id = getNextCheckId(); checksData.push(item); });
    doc.status = 'checked'; doc.checked = false;
    renderDocs(); renderChecks(); renderDashboardTable(); updateBadges(); updateDashboardMetrics();
    navigateTo('checks');
    showToast('Проверка завершена. Результатов: ' + results.length, 'success');
  } catch (error) {
    console.error('[Project Expert AI][Documents] Check error:', error);
    showToast('Ошибка проверки: ' + error.message, 'error');
  }
}

function checkSelectedDocs() {
  var selected = docsData.filter(function(d) { return d.checked && d.status === 'processed'; });
  if (!selected.length) { showToast('Выберите обработанный документ для проверки', 'error'); return; }
  Promise.all(selected.map(function(d) { return checkDocument(d.id); }));
}

// Explicit public handlers used by the main-page dropzone.
window.handleDocsDropzoneClick = handleDocsDropzoneClick;
window.handleDocDragOver = handleDocDragOver;
window.handleDocDragLeave = handleDocDragLeave;
window.handleDocDrop = handleDocDrop;
window.handleDocFiles = handleDocFiles;

// Legacy dropzone callbacks used by index.html.
window.handleDropzoneClick = function(type) {
  if (type === 'docs') return handleDocsDropzoneClick();
  if (type === 'norms' && window.handleNormDropzoneClick) return window.handleNormDropzoneClick();
};
window.handleDragOver = function(event) {
  if (event.currentTarget && event.currentTarget.id === 'docsDropzone') return handleDocDragOver(event);
  if (window.handleNormDragOver) return window.handleNormDragOver(event);
};
window.handleDragLeave = function(event) {
  if (event.currentTarget && event.currentTarget.id === 'docsDropzone') return handleDocDragLeave(event);
  if (window.handleNormDragLeave) return window.handleNormDragLeave(event);
};
window.handleDrop = function(event, type) {
  if (type === 'docs') return handleDocDrop(event);
  if (type === 'norms' && window.handleNormDrop) return window.handleNormDrop(event);
};
window.handleFiles = function(files, type) {
  if (type === 'docs') return handleDocFiles(files);
  if (type === 'norms' && window.handleNormFiles) return window.handleNormFiles(files);
};

window.loadDocs = loadDocs;
window.renderDocs = renderDocs;
window.handleDocFiles = handleDocFiles;
window.uploadDocFile = uploadDocFile;
window.checkDocument = checkDocument;
window.checkSelectedDocs = checkSelectedDocs;
window.deleteDoc = deleteDoc;
window.toggleDocCheck = toggleDocCheck;
window.toggleSelectAllDocs = toggleSelectAllDocs;

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadDocs, { once: true }); else loadDocs();
