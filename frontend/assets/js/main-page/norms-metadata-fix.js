// Project Expert AI — compatibility fix for legacy norm-version metadata.
// Amendment numbers are always derived from the uploaded PDF filename.
(function installNormMetadataFix() {
  function changeNumberFromFilename(filename) {
    var text = String(filename || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ');
    var match = text.match(/(?:\bизм(?:енение|енения)?\b|\bизменени[ея]\b|\bamendment\b)\s*\.?\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }

  function isCurrent(version, norm) {
    var selectedId = norm && norm.version_id != null ? String(norm.version_id) : '';
    var versionId = String(version && (version.version_id || version.id) || '');
    if (selectedId) return versionId === selectedId;
    return !!(version && String(version.status || '').toLowerCase() === 'current');
  }

  function labelFor(version, norm) {
    var filename = String(version.original_filename || version.filename || '');
    var change = version.change_number != null && String(version.change_number).trim() !== ''
      ? String(version.change_number).trim()
      : changeNumberFromFilename(filename);
    return (change === null ? 'Без изменений' : 'Изменение №' + change)
      + (isCurrent(version, norm) ? ' · действующая' : ' · архивная');
  }

  function normalizeState() {
    var data = Array.isArray(window.normsData) ? window.normsData : [];
    var changed = false;
    data.forEach(function (norm) {
      var versions = Array.isArray(norm.versions) ? norm.versions : [];
      versions.forEach(function (version) {
        var filename = String(version.original_filename || version.filename || '').trim();
        var change = changeNumberFromFilename(filename);
        if (change !== null && String(version.change_number || '') !== change) {
          version.change_number = change;
          changed = true;
        }
        var current = isCurrent(version, norm);
        if (current && version.status !== 'current') {
          version.status = 'current';
          changed = true;
        }
        if (!current && version.status === 'current') {
          version.status = 'superseded';
          changed = true;
        }
      });
      var currentVersion = versions.find(function (v) { return isCurrent(v, norm); });
      if (currentVersion) {
        var currentChange = currentVersion.change_number != null
          ? String(currentVersion.change_number)
          : changeNumberFromFilename(currentVersion.original_filename || currentVersion.filename);
        norm.current_change_number = currentChange;
        norm.version_id = currentVersion.version_id || currentVersion.id;
      }
    });
    if (changed && typeof window.renderNorms === 'function') window.renderNorms();
  }

  function patchRenderedRows() {
    var data = Array.isArray(window.normsData) ? window.normsData : [];
    data.forEach(function (norm) {
      var versions = Array.isArray(norm.versions) ? norm.versions : [];
      var panel = document.getElementById('normVersions-' + norm.id);
      if (panel) {
        var rows = panel.querySelectorAll('.norm-version-row');
        versions.forEach(function (version, index) {
          var row = rows[index];
          if (!row) return;
          var label = row.querySelector('.norm-version-label');
          if (label) label.textContent = labelFor(version, norm);
        });
      }
      var card = document.querySelector('[data-norm-card="' + CSS.escape(String(norm.id)) + '"]');
      if (card) {
        var title = card.querySelector('.norm-card-title');
        var current = versions.find(function (v) { return isCurrent(v, norm); });
        if (title) {
          var number = norm.number || norm.id;
          var change = current ? versionChangeNumber(current) : null;
          title.textContent = number + (current ? (change === null ? ' — Без изменений' : ' — Изменение №' + change) : ' — Действующая редакция не выбрана');
        }
      }
    });
  }

  function versionChangeNumber(version) {
    if (version && version.change_number != null && String(version.change_number).trim() !== '') return String(version.change_number).trim();
    return changeNumberFromFilename(version && (version.original_filename || version.filename));
  }

  function normalizeAndPatch() {
    normalizeState();
    patchRenderedRows();
  }

  var attempts = 0;
  var timer = setInterval(function () {
    attempts += 1;
    normalizeAndPatch();
    if (attempts >= 40) clearInterval(timer);
  }, 300);

  console.log('[VKS Expert AI][Norms] metadata compatibility fix v3 loaded');
})();
