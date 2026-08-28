// ===== CHECKS =====

// ===== RENDER: CHECKS =====

function renderChecks() {
  var list = document.getElementById('checksList');

  if (!list) {
    return;
  }

  var filtered = checksData.slice();

  // Фильтр по типу результата
  if (currentFilter !== 'all') {
    filtered = filtered.filter(function (c) {
      return c.type === currentFilter;
    });
  }

  // Фильтр по разделу
  if (currentSectionFilter && currentSectionFilter !== 'all') {
    filtered = filtered.filter(function (c) {
      return (
        c.section === currentSectionFilter || c.sheet === currentSectionFilter
      );
    });
  }

  // Фильтр по severity
  if (currentSeverityFilter) {
    filtered = filtered.filter(function (c) {
      return c.severity === currentSeverityFilter;
    });
  }

  if (filtered.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:48px;color:var(--text-secondary);">' +
      'Нет результатов для отображения.' +
      '</div>';

    return;
  }

  // ===== GROUP BY DOCUMENT =====

  var groupedByDoc = {};

  for (var i = 0; i < filtered.length; i++) {
    var check = filtered[i];

    var docKey =
      check.docId !== undefined && check.docId !== null
        ? check.docId
        : 'unknown';

    if (!groupedByDoc[docKey]) {
      groupedByDoc[docKey] = {
        docName: check.docName || 'Неизвестный документ',

        checks: [],
      };
    }

    groupedByDoc[docKey].checks.push(check);
  }

  var html = '';

  // ===== DOCUMENT GROUPS =====

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

    // ===== DOCUMENT HEADER =====

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

    if (violations > 0) {
      html +=
        '<span class="stat-badge violation">' +
        violations +
        ' нарушений</span>';
    }

    if (compliant > 0) {
      html +=
        '<span class="stat-badge compliant">' +
        compliant +
        ' соответствий</span>';
    }

    if (unchecked > 0) {
      html +=
        '<span class="stat-badge unchecked">' +
        unchecked +
        ' не проверено</span>';
    }

    html += '</div>';

    html += '</div>';

    // ===== CHECK CARDS =====

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

    for (var j = 0; j < group.checks.length; j++) {
      var item = group.checks[j];

      html += '<div class="violation-card">';

      html += '<div class="violation-header"><div>';

      html +=
        '<div class="violation-title">' +
        escapeHtml(item.title || '') +
        '</div>';

      html += '<div class="violation-meta">';

      if (item.sheet) {
        html += '<span>📄 ' + escapeHtml(item.sheet) + '</span>';
      }

      if (item.norm) {
        html += '<span>📋 ' + escapeHtml(item.norm) + '</span>';
      }

      if (item.severity && severityLabels[item.severity]) {
        html +=
          '<span class="status-badge ' +
          severityColors[item.severity] +
          '">' +
          severityLabels[item.severity] +
          '</span>';
      }

      html += '</div>';

      html += '</div>';

      html += '</div>';

      // ===== DESCRIPTION =====

      html +=
        '<div class="violation-description">' +
        escapeHtml(item.description || '') +
        '</div>';

      // ===== RECOMMENDATION =====

      if (item.recommendation) {
        html +=
          '<div class="violation-recommendation">' +
          '<strong>Рекомендация:</strong> ' +
          escapeHtml(item.recommendation) +
          '</div>';
      }

      // ===== IMAGE =====

      if (item.image) {
        html += '<div class="violation-image-container">';

        html +=
          '<img src="' +
          item.image +
          '" class="violation-image" alt="Скриншот нарушения">';

        html +=
          '<button class="attach-image-btn" onclick="removeImage(' +
          item.id +
          ')" style="margin-top:8px;background:#fee2e2;color:#dc2626;">';

        html +=
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';

        html +=
          '<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>';

        html += '</svg>';

        html += 'Удалить изображение';

        html += '</button>';

        html += '</div>';
      } else {
        html +=
          '<button class="attach-image-btn" onclick="attachImage(' +
          item.id +
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

// ===== FILTERS =====

var sectionFilterEl = document.getElementById('sectionFilter');

if (sectionFilterEl) {
  sectionFilterEl.addEventListener('change', function () {
    currentSectionFilter = this.value;
    renderChecks();
  });
}

var severityFilterEl = document.getElementById('severityFilter');

if (severityFilterEl) {
  severityFilterEl.addEventListener('change', function () {
    currentSeverityFilter = this.value;
    renderChecks();
  });
}
