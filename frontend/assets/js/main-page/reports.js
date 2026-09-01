// ============================================================
// Project Expert AI — REPORTS
// Reports are generated from actual check results by the API.
// ============================================================

var REPORTS_API = 'http://127.0.0.1:8000/api/reports';

function renderReports() {
  var list = document.getElementById('reportsList');
  if (!list) return;
  if (typeof reportsData === 'undefined' || reportsData.length === 0) {
    list.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет сформированных отчётов.</div>';
    return;
  }
  var html = '';
  reportsData.forEach(function(report) {
    html += '<div class="report-item"><div class="report-icon">📄</div><div class="report-info">';
    html += '<div class="report-title">' + escapeHtml(report.title || report.name || 'Отчёт') + '</div><div class="report-meta">';
    html += '<span>' + escapeHtml(report.date || '') + '</span><span>' + (report.documents || 0) + ' документов</span><span>' + (report.violations || 0) + ' нарушений</span>';
    html += '</div></div><div class="report-actions">';
    html += '<button class="btn btn-secondary btn-sm" onclick="viewReport(' + report.id + ')">Просмотр</button>';
    html += '<button class="btn btn-secondary btn-sm" onclick="downloadReport(' + report.id + ', \'pdf\')">PDF</button>';
    html += '<button class="btn btn-secondary btn-sm" onclick="downloadReport(' + report.id + ', \'docx\')">Word</button>';
    html += '<button class="delete-btn" onclick="deleteReport(' + report.id + ')" title="Удалить">🗑</button></div></div>';
  });
  list.innerHTML = html;
}

function createReport() {
  var source = typeof currentReport !== 'undefined' && currentReport ? currentReport : null;
  var checks = typeof checksData !== 'undefined' ? checksData : [];
  if (!checks.length && !source) {
    showToast('Нет результатов проверки для формирования отчёта', 'error');
    return;
  }

  var violations = checks.filter(function(c) { return c.type === 'violation'; });
  var compliant = checks.filter(function(c) { return c.type === 'compliant'; });
  var unchecked = checks.filter(function(c) { return c.type === 'unchecked'; });
  var docs = {};
  checks.forEach(function(c) { docs[c.docId || 'unknown'] = true; });

  var report = source ? Object.assign({}, source) : {
    id: Date.now(),
    title: 'Отчёт проверки от ' + new Date().toLocaleDateString('ru-RU'),
    date: new Date().toISOString().split('T')[0],
    documents: Object.keys(docs).length,
    violations: violations.length,
    compliant: compliant.length,
    unchecked: unchecked.length,
    totalChecks: checks.length,
    checks: checks.map(function(c) { return Object.assign({}, c); })
  };

  if (typeof reportsData === 'undefined') return;
  reportsData.unshift(report);
  currentReport = report;
  renderReports();
  if (typeof updateBadges === 'function') updateBadges();
  showToast('Отчёт подготовлен. Его можно скачать в PDF или Word.', 'success');
}

function viewReport(id) {
  if (typeof reportsData === 'undefined') return;
  var report = reportsData.find(function(r) { return r.id === id; });
  if (!report) { showToast('Отчёт не найден', 'error'); return; }
  var message = 'Отчёт: ' + (report.title || '') + '\n\n' +
    'Документов: ' + (report.documents || 0) + '\n' +
    'Проверок: ' + (report.totalChecks || 0) + '\n' +
    'Нарушений: ' + (report.violations || 0) + '\n' +
    'Соответствий: ' + (report.compliant || 0) + '\n' +
    'Не проверено: ' + (report.unchecked || 0);
  alert(message);
}

function downloadReport(id, format) {
  if (typeof reportsData === 'undefined') return;
  var report = reportsData.find(function(r) { return r.id === id; });
  if (!report) { showToast('Отчёт не найден', 'error'); return; }
  var endpoint = format === 'docx' ? REPORTS_API + '/docx' : REPORTS_API + '/pdf';

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report)
  }).then(function(response) {
    if (!response.ok) {
      return response.text().then(function(text) {
        var detail = text;
        try { detail = JSON.parse(text).detail || text; } catch (_) {}
        throw new Error(detail || 'Ошибка формирования отчёта');
      });
    }
    return response.blob();
  }).then(function(blob) {
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = 'project-expert-ai-check-' + (report.document_id || report.id) + (format === 'docx' ? '.docx' : '.pdf');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('Отчёт скачан в формате ' + (format === 'docx' ? 'Word' : 'PDF'), 'success');
  }).catch(function(error) {
    console.error('[Reports] Export error:', error);
    showToast('Не удалось сформировать отчёт: ' + error.message, 'error');
  });
}

function deleteReport(id) {
  if (typeof reportsData === 'undefined') return;
  var report = reportsData.find(function(r) { return r.id === id; });
  reportsData = reportsData.filter(function(r) { return r.id !== id; });
  if (typeof currentReport !== 'undefined' && currentReport && currentReport.id === id) currentReport = null;
  renderReports();
  if (typeof updateBadges === 'function') updateBadges();
  showToast('Отчёт удалён: ' + (report ? report.title || '' : ''), 'success');
}

window.renderReports = renderReports;
window.createReport = createReport;
window.viewReport = viewReport;
window.downloadReport = downloadReport;
window.deleteReport = deleteReport;
