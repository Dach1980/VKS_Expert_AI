// ===== RENDER: CHECKS =====
function renderChecks() {
  var list = document.getElementById('checksList');
  var filtered = checksData.slice();

  if (currentFilter !== 'all') {
    filtered = filtered.filter(function (c) {
      return c.type === currentFilter;
    });
  }
  if (currentSeverityFilter) {
    filtered = filtered.filter(function (c) {
      return c.severity === currentSeverityFilter;
    });
  }

  if (filtered.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет результатов для отображения.</div>';
    return;
  }

  // Группируем по документу
  var groupedByDoc = {};
  for (var i = 0; i < filtered.length; i++) {
    var check = filtered[i];
    var docKey = check.docId || 'unknown';
    if (!groupedByDoc[docKey]) {
      groupedByDoc[docKey] = {
        docName: check.docName || 'Неизвестный документ',
        checks: [],
      };
    }
    groupedByDoc[docKey].checks.push(check);
  }

  var html = '';

  // Для каждой группы документа
  for (var docId in groupedByDoc) {
    var group = groupedByDoc[docId];
    var violations = group.checks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var compliant = group.checks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var unchecked = group.checks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;

    html += '<div class="doc-check-group">';
    html += '<div class="doc-check-header">';
    html += '<div class="doc-check-title">';
    html +=
      '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">';
    html +=
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>';
    html += '</svg>';
    html += '<span>' + escapeHtml(group.docName) + '</span>';
    html += '</div>';
    html += '<div class="doc-check-stats">';
    if (violations > 0)
      html +=
        '<span class="stat-badge violation">' +
        violations +
        ' нарушений</span>';
    if (compliant > 0)
      html +=
        '<span class="stat-badge compliant">' +
        compliant +
        ' соответствий</span>';
    if (unchecked > 0)
      html +=
        '<span class="stat-badge unchecked">' +
        unchecked +
        ' не проверено</span>';
    html += '</div>';
    html += '</div>';

    // Карточки проверок для этого документа
    var severityColors = {
      critical: 'danger',
      major: 'warning',
      minor: 'info',
    };
    var severityLabels = {
      critical: 'Критическое',
      major: 'Значительное',
      minor: 'Незначительное',
    };

    for (var i = 0; i < group.checks.length; i++) {
      var check = group.checks[i];
      html += '<div class="violation-card">';
      html += '<div class="violation-header"><div>';
      html +=
        '<div class="violation-title">' + escapeHtml(check.title) + '</div>';
      html += '<div class="violation-meta">';
      html += '<span>📄 ' + escapeHtml(check.sheet) + '</span>';
      if (check.norm) {
        html += '<span>📋 ' + escapeHtml(check.norm) + '</span>';
      }
      if (check.severity && severityLabels[check.severity]) {
        html +=
          '<span class="status-badge ' +
          severityColors[check.severity] +
          '">' +
          severityLabels[check.severity] +
          '</span>';
      }
      html += '</div></div></div>';
      html +=
        '<div class="violation-description">' +
        escapeHtml(check.description) +
        '</div>';
      if (check.recommendation) {
        html +=
          '<div class="violation-recommendation"><strong>Рекомендация:</strong> ' +
          escapeHtml(check.recommendation) +
          '</div>';
      }

      // Отображение прикрепленного изображения
      if (check.image) {
        html += '<div class="violation-image-container">';
        html +=
          '<img src="' +
          check.image +
          '" class="violation-image" alt="Скриншот нарушения">';
        html +=
          '<button class="attach-image-btn" onclick="removeImage(' +
          check.id +
          ')" style="margin-top: 8px; background: #fee2e2; color: #dc2626;">';
        html +=
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';
        html +=
          '<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>';
        html += '</svg>';
        html += 'Удалить изображение';
        html += '</button>';
        html += '</div>';
      } else {
        // Кнопка прикрепления изображения
        html +=
          '<button class="attach-image-btn" onclick="attachImage(' +
          check.id +
          ')">';
        html +=
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';
        html +=
          '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"></path>';
        html += '</svg>';
        html += 'Прикрепить скриншот';
        html += '</button>';
      }

      html += '</div>';
    }

    html += '</div>';
  }

  list.innerHTML = html;
}

document
  .getElementById('sectionFilter')
  .addEventListener('change', function () {
    currentSectionFilter = this.value;
    renderChecks();
  });

document
  .getElementById('severityFilter')
  .addEventListener('change', function () {
    currentSeverityFilter = this.value;
    renderChecks();
  });
