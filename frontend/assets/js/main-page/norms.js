// ============================================================
// VKS EXPERT AI — NORMS
// Real Registry/Storage API integration
// ============================================================

// The Registry is the source of truth for normative documents.
// Remove legacy demo norms from state.js without changing project documents.
normsData = [];
var normsPollTimers = {};

function normProgress(norm) {
  var p = norm.processing || {};
  if (p.vector_index && p.vector_metadata) return 100;
  if (p.chunks) return 75;
  if (p.structured) return 60;
  if (p.parsed) return 40;
  if (p.uploaded) return 20;
  return 0;
}

function renderNorms() {
  var grid = document.getElementById('normsGrid');
  if (!grid) return;

  if (!normsData.length) {
    grid.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет нормативных документов. Перетащите PDF или нажмите на зону загрузки.</div>';
    return;
  }

  var html = '';
  normsData.forEach(function (norm) {
    var status = norm.status || 'pending';
    var progress = norm.progress == null ? normProgress(norm) : norm.progress;
    var processing = norm.processing || {};
    var id = JSON.stringify(norm.id);

    html += '<div class="norm-card">';
    html += '<div class="norm-card-header"><div style="flex:1;">';
    html += '<div class="norm-card-title">' + escapeHtml(norm.title || norm.number || '') + '</div>';
    html += '<div class="norm-card-subtitle">' + escapeHtml(norm.subtitle || '') + '</div>';
    html += '</div></div>';
    html += '<div class="norm-card-meta">';
    html += '<span>📅 ' + escapeHtml(norm.date || norm.effective_from || '') + '</span>';
    html += '<span>📄 ' + (processing.pages_count || 0) + ' стр.</span>';
    html += '<span>📂 ' + escapeHtml((norm.sections || []).join(', ') || '—') + '</span>';
    html += '</div>';

    if (status === 'indexing') {
      html += '<div class="progress-bar"><div class="progress-fill" style="width:' + progress + '%"></div></div>';
      html += '<div style="margin-top:8px;font-size:12px;color:var(--accent);">Индексация: ' + progress + '%</div>';
    } else if (status === 'indexed') {
      html += '<div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div>';
      html += '<div style="margin-top:8px;font-size:12px;color:var(--text-secondary);">Индексировано: 100%</div>';
    } else {
      html += '<div style="margin-top:12px;"><span class="status-badge info">Ожидает индексации</span></div>';
    }

    html += '<div class="norm-card-actions">';
    if (status !== 'indexing' && status !== 'indexed') {
      html += '<button class="btn btn-primary btn-sm" onclick="indexNorm(' + id + ')">Индексировать</button>';
    }
    html += '<button class="btn btn-secondary btn-sm" onclick="showNormInfo(' + id + ')">Информация</button>';
    html += '</div></div>';
  });
  grid.innerHTML = html;
}

function loadNorms() {
  return fetch('/api/norms')
    .then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    })
    .then(function (data) {
      normsData = (data.documents || []).map(function (item) {
        var p = item.processing || {};
        return {
          id: item.document_id,
          number: item.number,
          title: item.number || item.document_id,
          subtitle: item.title || '',
          date: item.effective_from || '',
          effective_from: item.effective_from || '',
          status: p.vector_index && p.vector_metadata ? 'indexed' : 'pending',
          progress: normProgress(item),
          sections: [],
          fileName: item.paths && item.paths.pdf ? item.paths.pdf.split(/[\\/]/).pop() : '',
          version_id: item.version_id,
          processing: p,
          raw: item
        };
      });
      renderNorms();
      if (typeof updateBadges === 'function') updateBadges();
      return normsData;
    })
    .catch(function (error) {
      console.error('[VKS Expert AI] Не удалось загрузить нормы:', error);
      showToast('Не удалось получить нормативную базу', 'error');
      throw error;
    });
}

function handleDropzoneClick(type) {
  var input = document.createElement('input');
  input.type = 'file';
  input.multiple = true;
  input.accept = type === 'norms' ? '.pdf' : '.pdf,.dwg,.docx';
  input.addEventListener('change', function (e) {
    if (e.target.files && e.target.files.length) handleFiles(e.target.files, type);
  });
  input.click();
}

function handleDrop(e, type) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files.length) handleFiles(e.dataTransfer.files, type);
}

function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.classList.remove('dragover');
}

function handleFiles(files, type) {
  if (type !== 'norms') {
    var docs = [];
    for (var i = 0; i < files.length; i++) {
      var file = files[i];
      docs.push({
        id: nextDocId++,
        name: file.name,
        size: formatFileSize(file.size),
        date: new Date().toISOString().split('T')[0],
        status: 'new',
        sheets: 0,
        section: 'ВК',
        checked: false
      });
    }
    docsData = docsData.concat(docs);
    if (typeof renderDocs === 'function') renderDocs();
    if (typeof updateBadges === 'function') updateBadges();
    showToast('Добавлено файлов: ' + docs.length, 'success');
    return;
  }

  var uploads = [];
  for (var j = 0; j < files.length; j++) uploads.push(uploadNormFile(files[j]));
  Promise.all(uploads).then(function () { return loadNorms(); }).catch(function () {});
}

function uploadNormFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Для нормативной базы допускается только PDF', 'error');
    return Promise.reject(new Error('Not a PDF'));
  }

  var form = new FormData();
  form.append('file', file, file.name);

  return fetch('/api/norms/upload', { method: 'POST', body: form })
    .then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
        return data;
      });
    })
    .then(function (data) {
      showToast('Норма загружена: ' + data.number, 'success');
      return data;
    })
    .catch(function (error) {
      console.error('[VKS Expert AI] Upload error:', error);
      showToast('Ошибка загрузки: ' + error.message, 'error');
      throw error;
    });
}

function indexNorm(id) {
  var norm = getNormById(id);
  if (!norm || !norm.version_id) {
    showToast('Версия нормативного документа не найдена', 'error');
    return;
  }

  norm.status = 'indexing';
  norm.progress = 20;
  renderNorms();

  fetch('/api/norms/' + encodeURIComponent(norm.id) + '/' + encodeURIComponent(norm.version_id) + '/index', { method: 'POST' })
    .then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
        return data;
      });
    })
    .then(function () {
      showToast('Полная индексация запущена', 'info');
      pollNormStatus(norm.id, norm.version_id);
    })
    .catch(function (error) {
      norm.status = 'pending';
      renderNorms();
      showToast('Ошибка запуска индексации: ' + error.message, 'error');
    });
}

function pollNormStatus(documentId, versionId) {
  var key = documentId + ':' + versionId;
  if (normsPollTimers[key]) clearInterval(normsPollTimers[key]);

  normsPollTimers[key] = setInterval(function () {
    fetch('/api/norms/' + encodeURIComponent(documentId) + '?version_id=' + encodeURIComponent(versionId))
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (data) {
        var norm = getNormById(documentId);
        if (!norm) return;
        norm.raw = data;
        norm.processing = data.processing || {};
        norm.progress = normProgress(data);
        norm.status = norm.processing.vector_index && norm.processing.vector_metadata ? 'indexed' : 'indexing';
        renderNorms();
        if (norm.status === 'indexed') {
          clearInterval(normsPollTimers[key]);
          delete normsPollTimers[key];
          showToast('Индексация завершена: ' + norm.number, 'success');
        }
      })
      .catch(function (error) {
        console.warn('[VKS Expert AI] Status polling error:', error);
      });
  }, 3000);
}

function indexAllNorms() {
  var pending = normsData.filter(function (norm) { return norm.status !== 'indexed' && norm.status !== 'indexing'; });
  if (!pending.length) {
    showToast('Все документы уже индексированы', 'info');
    return;
  }
  pending.forEach(function (norm) { indexNorm(norm.id); });
}

function showNormInfo(id) {
  var norm = getNormById(id);
  if (!norm) return;
  var p = norm.processing || {};
  alert('Документ: ' + (norm.number || '') + '\nНазвание: ' + (norm.subtitle || '') + '\nВерсия: ' + (norm.version_id || '') + '\nСтраниц: ' + (p.pages_count || 0) + '\nСтатус: ' + (norm.status || 'pending'));
}

function deleteNorm(id) {
  showToast('Удаление нормативных документов пока не реализовано', 'info');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function () { loadNorms(); });
} else {
  loadNorms();
}
