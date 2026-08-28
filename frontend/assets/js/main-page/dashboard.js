// ===== DASHBOARD =====

// ===== RENDER: DASHBOARD TABLE =====

function renderDashboardTable() {
  var tbody = document.getElementById('recentChecksTable');

  if (!tbody) {
    return;
  }

  var recentChecks = checksData
    .filter(function (c) {
      return c.type === 'violation';
    })
    .slice(0, 5);

  if (recentChecks.length === 0) {
    tbody.innerHTML =
      '<tr>' +
      '<td colspan="6" style="text-align:center;color:var(--text-secondary);padding:24px;">' +
      'Нет данных' +
      '</td>' +
      '</tr>';

    return;
  }

  var html = '';

  for (var i = 0; i < recentChecks.length; i++) {
    var c = recentChecks[i];

    var sevColor =
      c.severity === 'critical'
        ? 'danger'
        : c.severity === 'major'
          ? 'warning'
          : 'info';

    var severityLabel =
      c.severity === 'critical'
        ? 'Критическое'
        : c.severity === 'major'
          ? 'Значительное'
          : 'Незначительное';

    html += '<tr>';

    html +=
      '<td>' +
      escapeHtml((c.title || '').substring(0, 50)) +
      ((c.title || '').length > 50 ? '...' : '') +
      '</td>';

    html += '<td>' + escapeHtml(c.section || 'ВК') + '</td>';

    html += '<td>' + escapeHtml(c.date || '2026-05-21') + '</td>';

    html +=
      '<td>' +
      '<span class="status-badge ' +
      sevColor +
      '">' +
      severityLabel +
      '</span>' +
      '</td>';

    html += '<td>' + (i + 1) + '</td>';

    html +=
      '<td>' +
      '<button class="btn btn-secondary btn-sm" onclick="navigateTo(\'checks\')">' +
      'Подробнее' +
      '</button>' +
      '</td>';

    html += '</tr>';
  }

  tbody.innerHTML = html;
}

// ===== DASHBOARD METRICS =====

function updateDashboardMetrics() {
  var violations = checksData.filter(function (c) {
    return c.type === 'violation';
  }).length;

  var compliant = checksData.filter(function (c) {
    return c.type === 'compliant';
  }).length;

  var unchecked = checksData.filter(function (c) {
    return c.type === 'unchecked';
  }).length;

  var critical = checksData.filter(function (c) {
    return c.severity === 'critical';
  }).length;

  var total = checksData.length;

  var compliancePercent =
    total > 0 ? ((compliant / total) * 100).toFixed(1) : '0.0';

  var metricChecks = document.getElementById('metricChecks');
  var metricViolations = document.getElementById('metricViolations');
  var metricCompliance = document.getElementById('metricCompliance');

  var statCompliant = document.getElementById('statCompliant');
  var statViolations = document.getElementById('statViolations');
  var statUnchecked = document.getElementById('statUnchecked');
  var statCritical = document.getElementById('statCritical');

  if (metricChecks) {
    metricChecks.textContent = checksData.length;
  }

  if (metricViolations) {
    metricViolations.textContent = violations;
  }

  if (metricCompliance) {
    metricCompliance.textContent = compliancePercent + '%';
  }

  if (statCompliant) {
    statCompliant.textContent = compliant;
  }

  if (statViolations) {
    statViolations.textContent = violations;
  }

  if (statUnchecked) {
    statUnchecked.textContent = unchecked;
  }

  if (statCritical) {
    statCritical.textContent = critical;
  }
}

// ===== DASHBOARD REFRESH =====

function renderDashboard() {
  renderDashboardTable();
  updateDashboardMetrics();
}
