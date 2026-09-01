// ===== DASHBOARD =====

function renderDashboardTable() {
  var tbody = document.getElementById('recentChecksTable');
  if (!tbody) return;

  var recentChecks = checksData.filter(function (c) {
    return c.type === 'violation';
  }).slice(0, 5);

  if (recentChecks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);padding:24px;">Нет выполненных проверок</td></tr>';
    return;
  }

  var html = '';
  for (var i = 0; i < recentChecks.length; i++) {
    var c = recentChecks[i];
    var sevColor = c.severity === 'critical' ? 'danger' : c.severity === 'major' ? 'warning' : 'info';
    var severityLabel = c.severity === 'critical' ? 'Критическое' : c.severity === 'major' ? 'Значительное' : 'Незначительное';
    html += '<tr>';
    html += '<td>' + escapeHtml((c.title || '').substring(0, 50)) + ((c.title || '').length > 50 ? '...' : '') + '</td>';
    html += '<td>' + escapeHtml(c.section || 'ВК') + '</td>';
    html += '<td>' + escapeHtml(c.date || c.checked_at || '') + '</td>';
    html += '<td><span class="status-badge ' + sevColor + '">' + severityLabel + '</span></td>';
    html += '<td>' + (i + 1) + '</td>';
    html += '<td><button class="btn btn-secondary btn-sm" onclick="navigateTo(\'checks\')">Подробнее</button></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

function updateDashboardMetrics() {
  var data = Array.isArray(checksData) ? checksData : [];
  var violations = data.filter(function (c) { return c.type === 'violation'; }).length;
  var compliant = data.filter(function (c) { return c.type === 'compliant'; }).length;
  var unchecked = data.filter(function (c) { return c.type === 'unchecked'; }).length;
  var critical = data.filter(function (c) { return c.type === 'violation' && c.severity === 'critical'; }).length;
  var total = data.length;
  var compliancePercent = total > 0 ? ((compliant / total) * 100).toFixed(1) + '%' : '—';

  var metricChecks = document.getElementById('metricChecks');
  var metricViolations = document.getElementById('metricViolations');
  var metricCompliance = document.getElementById('metricCompliance');
  if (metricChecks) metricChecks.textContent = total;
  if (metricViolations) metricViolations.textContent = violations;
  if (metricCompliance) metricCompliance.textContent = compliancePercent;

  var cards = document.querySelectorAll('.metric-card');
  if (cards.length >= 4) {
    var timeValue = cards[3].querySelector('.metric-value');
    if (timeValue) {
      var durations = data.map(function (c) { return Number(c.duration_seconds || c.duration || 0); }).filter(function (v) { return v > 0; });
      timeValue.textContent = durations.length ? (durations.reduce(function (a, b) { return a + b; }, 0) / durations.length / 60).toFixed(1) + ' мин' : '—';
    }
    cards.forEach(function (card) {
      var change = card.querySelector('.metric-change');
      if (change) change.textContent = total ? 'По фактическим данным' : 'Нет данных';
    });
  }

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
