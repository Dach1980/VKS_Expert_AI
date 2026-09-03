// Project Expert AI — compatibility fix for legacy norm-version metadata.
// Amendment numbers are derived from explicit metadata first, then the uploaded PDF filename/version id.
(function installNormMetadataFix() {
  function changeNumberFromFilename(filename) {
    var text = String(filename || '').replace(/[\u00A0\u202F]/g, ' ').replace(/[_-]+/g, ' ');
    var match = text.match(/(?:\bизм(?:енение|енения)?\.?|\bизменени[ея]\.?|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }
  function changeNumberFromVersionId(version) {
    var id = String(version && (version.version_id || version.id) || '');
    var match = id.match(/(?:^|[_\s-])(?:изм|iz|amendment)[._\s-]*(\d+)(?:$|[_\s-])/i);
    return match ? match[1] : null;
  }
  function canonicalNumber(number) {
    return String(number || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }
  function expectedAmendmentCount(norm) {
    var number = canonicalNumber(norm && (norm.number || norm.id));
    if (number === 'сп 30.13330.2020') return 5;
    if (number === 'сп 31.13330.2021') return 2;
    if (number === 'сп 32.13330.2018') return 5;
    return null;
  }
  function isBaseVersion(version) {
    var type = String(version && version.type || '').toLowerCase();
    if (type === 'base') return true;
    var filename = String(version && (version.original_filename || version.filename || version.file) || '');
    return /\bбазов(?:ая|ую|ая\s+версия)\b|\bбез\s+изменений\b/i.test(filename);
  }
  function inferredChangeNumber(version, norm, versions) {
    var explicit = version && version.change_number != null && String(version.change_number).trim() !== ''
      ? String(version.change_number).trim() : null;
    if (explicit !== null) return explicit;
    var fromFilename = changeNumberFromFilename(version && (version.original_filename || version.filename || version.file));
    if (fromFilename !== null) return fromFilename;
    var fromVersionId = changeNumberFromVersionId(version);
    if (fromVersionId !== null) return fromVersionId;
    if (isBaseVersion(version)) return null;

    // Some locally migrated registries contain the correct version files but
    // lost change_number/original_filename. For the three initial SPs we can
    // safely restore the amendment number from the chronological version
    // sequence: base, Изм.1, Изм.2, ... .
    var maxChange = expectedAmendmentCount(norm);
    if (maxChange === null || !Array.isArray(versions) || versions.length !== maxChange + 1) return null;
    var ordered = versions.slice().sort(function (a, b) {
      return String(a.effective_from || '').localeCompare(String(b.effective_from || ''));
    });
    var index = ordered.indexOf(version);
    if (index <= 0) return null;
    return String(index);
  }
  function changeNumber(version, norm, versions, fallback) {
    var inferred = inferredChangeNumber(version, norm, versions);
    if (inferred !== null) return inferred;
    if (fallback != null && String(fallback).trim() !== '') return String(fallback).trim();
    return null;
  }
  function isCurrent(version, norm) {
    var selectedId = norm && norm.version_id != null ? String(norm.version_id) : '';
    var versionId = String(version && (version.version_id || version.id) || '');
    if (selectedId) return versionId === selectedId;
    return !!(version && String(version.status || '').toLowerCase() === 'current');
  }
  function canonicalTitle(number) {
    var normalized = canonicalNumber(number);
    if (normalized === 'сп 30.13330.2020') return 'Внутренний водопровод и канализация зданий';
    if (normalized === 'сп 31.13330.2021') return 'Водоснабжение. Наружные сети и сооружения';
    if (normalized === 'сп 32.13330.2018') return 'Канализация. Наружные сети и сооружения';
    return null;
  }
  function labelFor(version, norm, versions) {
    var change = changeNumber(version, norm, versions, norm && norm.current_change_number);
    return (change === null ? 'Без изменений' : 'Изменение №' + change) + (isCurrent(version, norm) ? ' · действующая' : ' · архивная');
  }
  function normalizeState() {
    var data = Array.isArray(window.normsData) ? window.normsData : [];
    var changed = false;
    data.forEach(function (norm) {
      var versions = Array.isArray(norm.versions) ? norm.versions : [];
      versions.forEach(function (version) {
        var change = changeNumber(version, norm, versions, null);
        if (change !== null && String(version.change_number || '') !== change) {
          version.change_number = change;
          changed = true;
        }
        var current = isCurrent(version, norm);
        if (current && version.status !== 'current') { version.status = 'current'; changed = true; }
        if (!current && version.status === 'current') { version.status = 'superseded'; changed = true; }
      });
      var currentVersion = versions.find(function (v) { return isCurrent(v, norm); });
      if (currentVersion) {
        norm.current_change_number = changeNumber(currentVersion, norm, versions, norm.current_change_number);
        norm.version_id = currentVersion.version_id || currentVersion.id;
      }
      var canonical = canonicalTitle(norm.number || norm.id);
      if (canonical && norm.title !== canonical) { norm.title = canonical; changed = true; }
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
        var renderedVersions = versions.slice().sort(function (a, b) {
          if (isCurrent(a, norm) && !isCurrent(b, norm)) return -1;
          if (!isCurrent(a, norm) && isCurrent(b, norm)) return 1;
          return String(b.effective_from || '').localeCompare(String(a.effective_from || ''));
        });
        renderedVersions.forEach(function (version, index) {
          var row = rows[index];
          if (!row) return;
          var label = row.querySelector('.norm-version-label');
          if (label) label.textContent = labelFor(version, norm, versions);
        });
      }
      var card = document.querySelector('[data-norm-card="' + CSS.escape(String(norm.id)) + '"]');
      if (card) {
        var title = card.querySelector('.norm-card-title');
        var subtitle = card.querySelector('.norm-card-subtitle');
        var current = versions.find(function (v) { return isCurrent(v, norm); });
        var number = norm.number || norm.id;
        var change = current ? changeNumber(current, norm, versions, norm.current_change_number) : null;
        if (title) title.textContent = number + (current ? (change === null ? ' — Без изменений' : ' — Изменение №' + change) : ' — Действующая редакция не выбрана');
        if (subtitle) subtitle.textContent = canonicalTitle(number) || norm.title || number;
      }
    });
  }
  function normalizeAndPatch() { normalizeState(); patchRenderedRows(); }
  var attempts = 0;
  var timer = setInterval(function () { attempts += 1; normalizeAndPatch(); if (attempts >= 40) clearInterval(timer); }, 300);
  console.log('[VKS Expert AI][Norms] metadata compatibility fix v7 loaded');
})();
