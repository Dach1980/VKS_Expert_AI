// ===== REPORTS =====

// ===== RENDER REPORTS =====

function renderReports() {
  var list = document.getElementById('reportsList');

  if (!list) {
    return;
  }

  if (typeof reportsData === 'undefined' || reportsData.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:48px;color:var(--text-secondary);">' +
      'Нет сформированных отчётов.' +
      '</div>';

    return;
  }

  var html = '';

  for (var i = 0; i < reportsData.length; i++) {
    var report = reportsData[i];

    html += '<div class="report-item">';

    html += '<div class="report-icon">📄</div>';

    html += '<div class="report-info">';

    html +=
      '<div class="report-title">' +
      escapeHtml(report.title || report.name || 'Отчёт') +
      '</div>';

    html += '<div class="report-meta">';

    if (report.date) {
      html += '<span>' + escapeHtml(report.date) + '</span>';
    }

    if (report.documents !== undefined) {
      html += '<span>' + report.documents + ' документов</span>';
    }

    if (report.violations !== undefined) {
      html += '<span>' + report.violations + ' нарушений</span>';
    }

    html += '</div>';

    html += '</div>';

    html += '<div class="report-actions">';

    html +=
      '<button class="btn btn-secondary btn-sm" onclick="viewReport(' +
      report.id +
      ')">' +
      'Просмотр' +
      '</button>';

    html +=
      '<button class="btn btn-secondary btn-sm" onclick="downloadReport(' +
      report.id +
      ')">' +
      'Скачать' +
      '</button>';

    html +=
      '<button class="delete-btn" onclick="deleteReport(' +
      report.id +
      ')" title="Удалить">';

    html +=
      '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">';

    html +=
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 01-1 1h-4a1 1 0 01-1 1v3M4 7h16"></path>';

    html += '</svg>';

    html += '</button>';

    html += '</div>';

    html += '</div>';
  }

  list.innerHTML = html;
}

// ===== CREATE REPORT =====

function createReport() {
  var violations = checksData.filter(function (c) {
    return c.type === 'violation';
  });

  var compliant = checksData.filter(function (c) {
    return c.type === 'compliant';
  });

  var unchecked = checksData.filter(function (c) {
    return c.type === 'unchecked';
  });

  var report = {
    id: typeof nextReportId !== 'undefined' ? nextReportId++ : Date.now(),

    title: 'Отчёт проверки от ' + new Date().toISOString().split('T')[0],

    date: new Date().toISOString().split('T')[0],

    documents: docsData.length,

    violations: violations.length,

    compliant: compliant.length,

    unchecked: unchecked.length,

    totalChecks: checksData.length,
  };

  if (typeof reportsData === 'undefined') {
    return;
  }

  reportsData.unshift(report);

  renderReports();

  updateBadges();

  showToast('Отчёт успешно сформирован', 'success');
}

// ===== VIEW REPORT =====

function viewReport(id) {
  if (typeof reportsData === 'undefined') {
    return;
  }

  var report = reportsData.find(function (r) {
    return r.id === id;
  });

  if (!report) {
    showToast('Отчёт не найден', 'error');

    return;
  }

  var message =
    'Отчёт: ' +
    (report.title || '') +
    '\n\n' +
    'Документов: ' +
    (report.documents || 0) +
    '\n' +
    'Проверок: ' +
    (report.totalChecks || 0) +
    '\n' +
    'Нарушений: ' +
    (report.violations || 0) +
    '\n' +
    'Соответствий: ' +
    (report.compliant || 0) +
    '\n' +
    'Не проверено: ' +
    (report.unchecked || 0);

  alert(message);
}

// ===== DOWNLOAD REPORT =====

function downloadReport(id) {
  if (typeof reportsData === 'undefined') {
    return;
  }

  var report = reportsData.find(function (r) {
    return r.id === id;
  });

  if (!report) {
    showToast('Отчёт не найден', 'error');

    return;
  }

  var content =
    'ОТЧЁТ ПРОВЕРКИ\n\n' +
    'Название: ' +
    (report.title || '') +
    '\n' +
    'Дата: ' +
    (report.date || '') +
    '\n\n' +
    'Документов: ' +
    (report.documents || 0) +
    '\n' +
    'Проверок: ' +
    (report.totalChecks || 0) +
    '\n' +
    'Нарушений: ' +
    (report.violations || 0) +
    '\n' +
    'Соответствий: ' +
    (report.compliant || 0) +
    '\n' +
    'Не проверено: ' +
    (report.unchecked || 0);

  var blob = new Blob([content], {
    type: 'text/plain;charset=utf-8',
  });

  var url = URL.createObjectURL(blob);

  var link = document.createElement('a');

  link.href = url;

  link.download = 'report-' + report.id + '.txt';

  document.body.appendChild(link);

  link.click();

  document.body.removeChild(link);

  URL.revokeObjectURL(url);

  showToast('Отчёт подготовлен для скачивания', 'success');
}

// ===== DELETE REPORT =====

function deleteReport(id) {
  if (typeof reportsData === 'undefined') {
    return;
  }

  var report = reportsData.find(function (r) {
    return r.id === id;
  });

  reportsData = reportsData.filter(function (r) {
    return r.id !== id;
  });

  renderReports();

  updateBadges();

  showToast('Отчёт удалён: ' + (report ? report.title || '' : ''), 'success');
}
