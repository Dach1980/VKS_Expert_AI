// ============================================================
// Project Expert AI — REPORTS
// Отчёт формируется из фактических результатов проверки.
// ============================================================

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
    html += '<button class="btn btn-secondary btn-sm" onclick="downloadReport(' + report.id + ')">Скачать</button>';
    html += '<button class="delete-btn" onclick="deleteReport(' + report.id + ')" title="Удалить">🗑</button></div></div>';
  });
  list.innerHTML = html;
}

function createReport() {
  var violations = checksData.filter(function(c) { return c.type === 'violation'; });
  var compliant = checksData.filter(function(c) { return c.type === 'compliant'; });
  var unchecked = checksData.filter(function(c) { return c.type === 'unchecked'; });
  if (!checksData.length) { showToast('Нет результатов проверки для формирования отчёта', 'error'); return; }

  var report = {
    id: typeof nextReportId !== 'undefined' ? nextReportId++ : Date.now(),
    title: 'Отчёт проверки от ' + new Date().toLocaleDateString('ru-RU'),
    date: new Date().toISOString().split('T')[0],
    documents: new Set(checksData.map(function(c) { return c.docId; })).size,
    violations: violations.length,
    compliant: compliant.length,
    unchecked: unchecked.length,
    totalChecks: checksData.length,
    checks: checksData.map(function(c) { return Object.assign({}, c); }),
  };
  if (typeof reportsData === 'undefined') return;
  reportsData.unshift(report);
  currentReport = report;
  renderReports(); updateBadges();
  showToast('Отчёт успешно сформирован', 'success');
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

function buildReportText(report) {
  var lines = [
    'PROJECT EXPERT AI — ОТЧЁТ НОРМОКОНТРОЛЯ',
    '',
    'Название: ' + (report.title || ''),
    'Дата: ' + (report.date || ''),
    'Документов: ' + (report.documents || 0),
    'Проверок: ' + (report.totalChecks || 0),
    'Нарушений: ' + (report.violations || 0),
    'Соответствий: ' + (report.compliant || 0),
    'Не проверено: ' + (report.unchecked || 0),
    '',
    'РЕЗУЛЬТАТЫ',
    '============================================================',
  ];
  (report.checks || []).forEach(function(item, index) {
    lines.push('');
    lines.push((index + 1) + '. ' + (item.type === 'violation' ? 'НАРУШЕНИЕ' : item.type === 'compliant' ? 'СООТВЕТСТВИЕ' : 'НЕ ПРОВЕРЕНО'));
    lines.push('Документ: ' + (item.docName || ''));
    lines.push('Страница: ' + (item.page || '—'));
    lines.push('Лист: ' + (item.sheet || '—'));
    lines.push('Норматив: ' + (item.norm || '—'));
    lines.push('Уровень: ' + (item.severity || '—'));
    lines.push('Результат: ' + (item.title || ''));
    lines.push('Описание: ' + (item.description || ''));
    if (item.recommendation) lines.push('Рекомендация: ' + item.recommendation);
  });
  return lines.join('\n');
}

function downloadReport(id) {
  if (typeof reportsData === 'undefined') return;
  var report = reportsData.find(function(r) { return r.id === id; });
  if (!report) { showToast('Отчёт не найден', 'error'); return; }
  var blob = new Blob([buildReportText(report)], { type: 'text/plain;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var link = document.createElement('a');
  link.href = url; link.download = 'project-expert-ai-report-' + report.id + '.txt';
  document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(url);
  showToast('Подробный отчёт подготовлен для скачивания', 'success');
}

function deleteReport(id) {
  if (typeof reportsData === 'undefined') return;
  var report = reportsData.find(function(r) { return r.id === id; });
  reportsData = reportsData.filter(function(r) { return r.id !== id; });
  if (currentReport && currentReport.id === id) currentReport = null;
  renderReports(); updateBadges();
  showToast('Отчёт удалён: ' + (report ? report.title || '' : ''), 'success');
}

window.renderReports = renderReports;
window.createReport = createReport;
window.viewReport = viewReport;
window.downloadReport = downloadReport;
window.deleteReport = deleteReport;
