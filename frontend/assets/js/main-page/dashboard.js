// ===== DASHBOARD =====

function getDashboardChecksData() {
  // state.js may be loaded before or after the renderer during application
  // bootstrap. Always use the public runtime state and never assume that a
  // module-local `checksData` variable already exists.
  if (Array.isArray(window.checksData)) return window.checksData;
  return [];
}

function renderDashboardTable() {
  var tbody = document.getElementById('recentChecksTable');
  if (!tbody) return;

  var data = getDashboardChecksData();
  var recentChecks = data.filter(function (c) {
    return c && (c.type === 'violation' || c.type === 'compliant' || c.type === 'unchecked');
  }).slice(0, 5);

  if (recentChecks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);padding:24px;">Нет выполненных проверок</td></tr>';
    return;
  }

  var html = '';
  for (var i = 0; i < recentChecks.length; i++) {
    var c = recentChecks[i];
    var sevColor = c.type === 'violation'
      ? (c.severity === 'critical' ? 'danger' : c.severity === 'major' ? 'warning' : 'info')
      : c.type === 'compliant' ? 'success' : 'warning';
    var severityLabel = c.type === 'violation'
      ? (c.severity === 'critical' ? 'Критическое' : c.severity === 'major' ? 'Значительное' : 'Незначительное')
      : c.type === 'compliant' ? 'Соответствие' : 'Не проверено';

    html += '<tr>'
      + '<td>' + escapeHtml((c.docName || c.title || '').substring(0, 50)) + '</td>'
      + '<td>' + escapeHtml(c.section || 'ВК') + '</td>'
      + '<td>' + escapeHtml(c.date || c.checked_at || '') + '</td>'
      + '<td><span class="status-badge ' + sevColor + '">' + severityLabel + '</span></td>'
      + '<td>' + (c.type === 'violation' ? '1' : '0') + '</td>'
      + '<td><button class="btn btn-secondary btn-sm" onclick="navigateTo(\'checks\')">Подробнее</button></td>'
      + '</tr>';
  }

  tbody.innerHTML = html;
}

function updateDashboardMetrics() {
  var data = getDashboardChecksData();
  var violations = data.filter(function (c) { return c && c.type === 'violation'; }).length;
  var compliant = data.filter(function (c) { return c && c.type === 'compliant'; }).length;
  var unchecked = data.filter(function (c) { return c && c.type === 'unchecked'; }).length;
  var critical = data.filter(function (c) { return c && c.type === 'violation' && c.severity === 'critical'; }).length;
  var total = data.length;
  var evaluated = compliant + violations;
  var compliancePercent = evaluated > 0 ? ((compliant / evaluated) * 100).toFixed(1) + '%' : '—';

  var metricChecks = document.getElementById('metricChecks');
  var metricViolations = document.getElementById('metricViolations');
  var metricCompliance = document.getElementById('metricCompliance');
  var metricDuration = document.getElementById('metricDuration');

  if (metricChecks) metricChecks.textContent = total;
  if (metricViolations) metricViolations.textContent = violations;
  if (metricCompliance) metricCompliance.textContent = compliancePercent;

  if (metricDuration) {
    var durations = data.map(function (c) {
      return Number(c && (c.duration_seconds || c.duration) || 0);
    }).filter(function (v) { return v > 0; });
    metricDuration.textContent = durations.length
      ? (durations.reduce(function (a, b) { return a + b; }, 0) / durations.length / 60).toFixed(1) + ' мин'
      : '—';
  }

  document.querySelectorAll('.metric-change').forEach(function (el) {
    el.textContent = total ? 'По фактическим данным' : 'Нет данных';
    el.className = 'metric-change';
  });

  var statCompliant = document.getElementById('statCompliant');
  var statViolations = document.getElementById('statViolations');
  var statUnchecked = document.getElementById('statUnchecked');
  var statCritical = document.getElementById('statCritical');

  if (statCompliant) statCompliant.textContent = compliant;
  if (statViolations) statViolations.textContent = violations;
  if (statUnchecked) statUnchecked.textContent = unchecked;
  if (statCritical) statCritical.textContent = critical;
}

function renderDashboard() {
  renderDashboardTable();
  updateDashboardMetrics();
}

window.renderDashboardTable = renderDashboardTable;
window.updateDashboardMetrics = updateDashboardMetrics;
window.renderDashboard = renderDashboard;
