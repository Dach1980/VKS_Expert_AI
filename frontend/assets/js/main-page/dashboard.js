// ===== RENDER: DASHBOARD TABLE =====
function renderDashboardTable() {
  var tbody = document.getElementById('recentChecksTable');
  var recentChecks = checksData
    .filter(function (c) {
      return c.type === 'violation';
    })
    .slice(0, 5);
  if (recentChecks.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);padding:24px;">Нет данных</td></tr>';
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
    html += '<tr>';
    html += '<td>' + escapeHtml(c.title.substring(0, 50)) + '...</td>';
    html += '<td>ВК</td>';
    html += '<td>2026-05-21</td>';
    html +=
      '<td><span class="status-badge ' +
      sevColor +
      '">' +
      (c.severity || 'info') +
      '</span></td>';
    html += '<td>' + (i + 1) + '</td>';
    html +=
      '<td><button class="btn btn-secondary btn-sm" onclick="navigateTo(\'checks\')">Подробнее</button></td>';
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

  document.getElementById('metricChecks').textContent =
    247 + checksData.length - 10;
  document.getElementById('metricViolations').textContent = 38 + violations - 6;
  document.getElementById('metricCompliance').textContent =
    compliancePercent + '%';

  document.getElementById('statCompliant').textContent = 156 + compliant - 3;
  document.getElementById('statViolations').textContent = 38 + violations - 6;
  document.getElementById('statUnchecked').textContent = 53 + unchecked - 1;
  document.getElementById('statCritical').textContent = 7 + critical - 2;
}
