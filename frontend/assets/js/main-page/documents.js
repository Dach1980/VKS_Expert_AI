// ===== RENDER: DOCS =====
function renderDocs() {
  var list = document.getElementById('docsList');
  var checkedCount = docsData.filter(function (d) {
    return d.checked;
  }).length;
  document.getElementById('selectAllLabel').textContent =
    'Выбрать все' + (docsData.length > 0 ? ' (' + docsData.length + ')' : '');

  if (docsData.length === 0) {
    list.innerHTML =
      '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет документов. Перетащите файлы или нажмите на зону загрузки.</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < docsData.length; i++) {
    var doc = docsData[i];
    var statusClass = doc.status === 'checked' ? 'success' : 'info';
    var statusText = doc.status === 'checked' ? 'Проверен' : 'Новый';
    html += '<div class="doc-item">';
    html +=
      '<input type="checkbox" class="doc-checkbox" ' +
      (doc.checked ? 'checked' : '') +
      ' onchange="toggleDocCheck(' +
      doc.id +
      ')">';
    html += '<div class="doc-icon">📄</div>';
    html += '<div class="doc-info">';
    html += '<div class="doc-name">' + escapeHtml(doc.name) + '</div>';
    html += '<div class="doc-meta">';
    html += '<span>' + doc.size + '</span>';
    html += '<span>' + doc.date + '</span>';
    html += '<span>' + doc.sheets + ' листов</span>';
    html += '<span>' + doc.section + '</span>';
    html += '</div>';
    html += '</div>';
    html += '<div class="doc-actions">';
    html +=
      '<span class="status-badge ' +
      statusClass +
      '">' +
      statusText +
      '</span>';
    html +=
      '<button class="delete-btn" onclick="deleteDoc(' +
      doc.id +
      ')" title="Удалить">';
    html +=
      '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">';
    html +=
      '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>';
    html += '</svg></button>';
    html += '</div>';
    html += '</div>';
  }
  list.innerHTML = html;
}

function deleteDoc(id) {
  var doc = docsData.find(function (d) {
    return d.id === id;
  });
  docsData = docsData.filter(function (d) {
    return d.id !== id;
  });
  renderDocs();
  updateBadges();
  showToast(
    'Документ удалён: ' + (doc ? doc.name.substring(0, 30) + '...' : ''),
    'success',
  );
}

// ===== DOC CHECKBOX =====
function toggleDocCheck(id) {
  var doc = docsData.find(function (d) {
    return d.id === id;
  });
  if (doc) {
    doc.checked = !doc.checked;
    renderDocs();
  }
}

function toggleSelectAllDocs() {
  var selectAll = document.getElementById('selectAllDocs').checked;
  docsData.forEach(function (doc) {
    doc.checked = selectAll;
  });
  renderDocs();
}

// ===== CHECK SELECTED DOCS =====
function checkSelectedDocs() {
  var checkedDocs = docsData.filter(function (d) {
    return d.checked;
  });

  if (checkedDocs.length === 0) {
    showToast('Выберите хотя бы один документ для проверки', 'error');
    return;
  }

  showToast(
    'Начата проверка ' + checkedDocs.length + ' документ(ов)...',
    'info',
  );

  // Generate additional realistic check results based on the document content
  var additionalChecks = generateRealisticChecks(checkedDocs);

  setTimeout(function () {
    // Mark docs as checked
    checkedDocs.forEach(function (doc) {
      doc.status = 'checked';
      doc.checked = false;
    });

    // Add new checks
    for (var i = 0; i < additionalChecks.length; i++) {
      checksData.push(additionalChecks[i]);
    }

    renderDocs();
    renderChecks();
    renderDashboardTable();
    updateBadges();
    updateDashboardMetrics();
    navigateTo('checks');
    showToast(
      'Проверка завершена. Добавлено результатов: ' + additionalChecks.length,
      'success',
    );
  }, 1500);
}
