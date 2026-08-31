// ============================================================
// Project Expert AI — NORMS
// Реальная интеграция Registry / Storage / processing pipeline.
// ============================================================

const NORMS_API_BASE = 'http://127.0.0.1:8000/api/norms';
var normsPollTimers = {};

if (!Array.isArray(window.normsData)) window.normsData = [];

function getNormsData() { return window.normsData; }
function setNormsData(value) { window.normsData = Array.isArray(value) ? value : []; }

function normProgress(norm) {
  var p = norm && norm.processing ? norm.processing : {};
  if (p.vector_index && p.vector_metadata) return 100;
  if (p.chunks) return 75;
  if (p.structured) return 60;
  if (p.parsed) return 40;
  if (p.uploaded) return 20;
  return 0;
}

function escapeHtmlSafe(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function showNormToast(message, type) {
  if (typeof window.showToast === 'function') { window.showToast(message, type || 'info'); return; }
  console.log('[Project Expert AI][Norms]', message);
}

function getNormByIdLocal(id) {
  return getNormsData().find(function (norm) { return String(norm.id) === String(id); });
}

function renderNorms() {
  var grid = document.getElementById('normsGrid');
  if (!grid) return;
  var norms = getNormsData();
  if (!norms.length) {
    grid.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет нормативных документов. Перетащите PDF или нажмите на зону загрузки.</div>';
    return;
  }
  var html = '';
  norms.forEach(function (norm) {
    var status = norm.status || 'pending';
    var progress = norm.progress == null ? normProgress(norm) : norm.progress;
    var processing = norm.processing || {};
    var id = JSON.stringify(norm.id);
    html += '<div class="norm-card">';
    html += '<div class="norm-card-header"><div style="flex:1;"><div class="norm-card-title">' + escapeHtmlSafe(norm.title || norm.number || '') + '</div><div class="norm-card-subtitle">' + escapeHtmlSafe(norm.subtitle || '') + '</div></div></div>';
    html += '<div class="norm-card-meta"><span>📅 ' + escapeHtmlSafe(norm.date || norm.effective_from || '') + '</span><span>📄 ' + (processing.pages_count || 0) + ' стр.</span><span>📂 ' + escapeHtmlSafe((norm.sections || []).join(', ') || '—') + '</span></div>';
    if (status === 'indexing') {
      html += '<div class="progress-bar"><div class="progress-fill" style="width:' + progress + '%"></div></div><div style="margin-top:8px;font-size:12px;color:var(--accent);">Индексация: ' + progress + '%</div>';
    } else if (status === 'indexed') {
      html += '<div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div><div style="margin-top:8px;font-size:12px;color:var(--text-secondary);">Индексировано: 100%</div>';
    } else if (status === 'error') {
      html += '<div style="margin-top:12px;"><span class="status-badge error">Ошибка индексации</span></div>';
    } else {
      html += '<div style="margin-top:12px;"><span class="status-badge info">Ожидает индексации</span></div>';
    }
    html += '<div class="norm-card-actions">';
    if (status !== 'indexing' && status !== 'indexed') html += '<button class="btn btn-primary btn-sm" onclick="indexNorm(' + id + ')">Индексировать</button>';
    html += '<button class="btn btn-secondary btn-sm" onclick="showNormInfo(' + id + ')">Информация</button></div></div>';
  });
  grid.innerHTML = html;
}

async function loadNorms() {
  try {
    var response = await fetch(NORMS_API_BASE);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    var data = await response.json();
    setNormsData((data.documents || []).map(function (item) {
      var p = item.processing || {};
      return {
        id: item.document_id, number: item.number, title: item.number || item.document_id,
        subtitle: item.title || '', date: item.effective_from || '', effective_from: item.effective_from || '',
        status: p.vector_index && p.vector_metadata ? 'indexed' : 'pending', progress: normProgress(item),
        sections: [], fileName: item.paths && item.paths.pdf ? item.paths.pdf.split(/[\\/]/).pop() : '',
        version_id: item.version_id, processing: p, raw: item,
      };
    }));
    renderNorms();
    if (typeof window.updateBadges === 'function') window.updateBadges();
    return getNormsData();
  } catch (error) {
    console.error('[Project Expert AI] Не удалось загрузить нормы:', error);
    showNormToast('Не удалось получить нормативную базу: ' + error.message, 'error');
    return [];
  }
}

// Только нормативная зона. Не используем общие window.handleFiles/handleDropzoneClick,
// чтобы модуль «Нормы» не конфликтовал с модулем «Документация».
function handleNormDropzoneClick() {
  var input = document.createElement('input');
  input.type = 'file'; input.multiple = true; input.accept = '.pdf,application/pdf';
  input.addEventListener('change', function (event) {
    if (event.target.files && event.target.files.length) handleNormFiles(event.target.files);
  });
  input.click();
}

function handleNormDragOver(event) {
  event.preventDefault(); event.stopPropagation();
  if (event.currentTarget) event.currentTarget.classList.add('dragover');
}

function handleNormDragLeave(event) {
  event.preventDefault(); event.stopPropagation();
  if (event.currentTarget) event.currentTarget.classList.remove('dragover');
}

function handleNormDrop(event) {
  event.preventDefault(); event.stopPropagation();
  if (event.currentTarget) event.currentTarget.classList.remove('dragover');
  if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files.length) handleNormFiles(event.dataTransfer.files);
}

function handleNormFiles(files) {
  var uploads = [];
  for (var i = 0; i < files.length; i += 1) uploads.push(uploadNormFile(files[i]));
  Promise.all(uploads).then(loadNorms).catch(function () {});
}

function uploadNormFile(file) {
  if (!file || !file.name || !file.name.toLowerCase().endsWith('.pdf')) {
    showNormToast('Для нормативной базы допускается только PDF', 'error');
    return Promise.reject(new Error('Not a PDF'));
  }
  if (file.size > 50 * 1024 * 1024) {
    showNormToast('Размер PDF не должен превышать 50 МБ', 'error');
    return Promise.reject(new Error('File too large'));
  }
  var form = new FormData(); form.append('file', file, file.name);
  return fetch(NORMS_API_BASE + '/upload', { method: 'POST', body: form })
    .then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
        return data;
      });
    })
    .then(function (data) {
      showNormToast('Норма загружена: ' + (data.number || file.name), 'success');
      return data;
    })
    .catch(function (error) {
      console.error('[Project Expert AI] Upload error:', error);
      showNormToast('Ошибка загрузки: ' + error.message, 'error');
      throw error;
    });
}

function indexNorm(id) {
  var norm = getNormByIdLocal(id);
  if (!norm || !norm.version_id) { showNormToast('Версия нормативного документа не найдена', 'error'); return; }
  norm.status = 'indexing'; norm.progress = Math.max(20, norm.progress || 0); renderNorms();
  fetch(NORMS_API_BASE + '/' + encodeURIComponent(norm.id) + '/' + encodeURIComponent(norm.version_id) + '/index', { method: 'POST' })
    .then(function (response) {
      return response.json().then(function (data) { if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status)); return data; });
    })
    .then(function () { showNormToast('Полная индексация запущена', 'info'); pollNormStatus(norm.id, norm.version_id); })
    .catch(function (error) { norm.status = 'pending'; renderNorms(); showNormToast('Ошибка запуска индексации: ' + error.message, 'error'); });
}

function pollNormStatus(documentId, versionId) {
  var key = documentId + ':' + versionId;
  if (normsPollTimers[key]) clearInterval(normsPollTimers[key]);
  normsPollTimers[key] = setInterval(function () {
    fetch(NORMS_API_BASE + '/' + encodeURIComponent(documentId) + '?version_id=' + encodeURIComponent(versionId))
      .then(function (response) { if (!response.ok) throw new Error('HTTP ' + response.status); return response.json(); })
      .then(function (data) {
        var norm = getNormByIdLocal(documentId); if (!norm) return;
        norm.raw = data; norm.processing = data.processing || {}; norm.progress = normProgress(data);
        if (norm.processing.error) { norm.status = 'error'; clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; showNormToast('Индексация завершилась с ошибкой', 'error'); }
        else if (norm.processing.vector_index && norm.processing.vector_metadata) { norm.status = 'indexed'; norm.progress = 100; clearInterval(normsPollTimers[key]); delete normsPollTimers[key]; showNormToast('Индексация завершена: ' + norm.number, 'success'); }
        else norm.status = 'indexing';
        renderNorms();
      })
      .catch(function (error) { console.warn('[Project Expert AI] Status polling error:', error); });
  }, 3000);
}

function indexAllNorms() {
  var pending = getNormsData().filter(function (norm) { return norm.status !== 'indexed' && norm.status !== 'indexing'; });
  if (!pending.length) { showNormToast('Все документы уже индексированы', 'info'); return; }
  pending.forEach(function (norm) { indexNorm(norm.id); });
}

function showNormInfo(id) {
  var norm = getNormByIdLocal(id); if (!norm) return;
  var p = norm.processing || {};
  alert('Документ: ' + (norm.number || '') + '\nНазвание: ' + (norm.subtitle || '') + '\nВерсия: ' + (norm.version_id || '') + '\nСтраниц: ' + (p.pages_count || 0) + '\nСтатус: ' + (norm.status || 'pending'));
}

function deleteNorm(id) { showNormToast('Удаление нормативных документов пока не реализовано', 'info'); }

window.renderNorms = renderNorms;
window.loadNorms = loadNorms;
window.handleNormDropzoneClick = handleNormDropzoneClick;
window.handleNormDragOver = handleNormDragOver;
window.handleNormDragLeave = handleNormDragLeave;
window.handleNormDrop = handleNormDrop;
window.handleNormFiles = handleNormFiles;
window.uploadNormFile = uploadNormFile;
window.indexNorm = indexNorm;
window.pollNormStatus = pollNormStatus;
window.indexAllNorms = indexAllNorms;
window.showNormInfo = showNormInfo;
window.deleteNorm = deleteNorm;

console.log('[Project Expert AI] norms.js loaded');
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { loadNorms(); }, { once: true });
else loadNorms();
