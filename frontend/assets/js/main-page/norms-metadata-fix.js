// Project Expert AI — compatibility fix for legacy norm-version metadata.
// The uploaded PDF filename is authoritative whenever it contains an amendment number.
// This module never infers amendment numbers from version ordering.
(function installNormMetadataFix() {
  function changeNumberFromFilename(filename) {
    var text = String(filename || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ');
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

  function isBaseVersion(version) {
    var type = String(version && version.type || '').toLowerCase();
    if (type === 'base') return true;
    var filename = String(version && (version.original_filename || version.filename || version.file) || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ')
      .trim();
    if (!filename || changeNumberFromFilename(filename) !== null) return false;
    return /(?:^|\s)(?:базов(?:ая|ую)|без\s+изменений)(?:\s|$)/i.test(filename);
  }

  // Priority is deliberately strict:
  // 1. PDF filename — authoritative source.
  // 2. Base-version marker — explicitly means no amendment.
  // 3. Existing explicit metadata — compatibility fallback only when the filename
  //    does not contain an amendment number.
  // 4. Version id — compatibility fallback only when neither of the above exists.
  // Never derive an amendment number from array/order/effective dates.
  function inferredChangeNumber(version) {
    var filename = version && (version.original_filename || version.filename || version.file);
    var fromFilename = changeNumberFromFilename(filename);
    if (fromFilename !== null) return fromFilename;
    if (isBaseVersion(version)) return null;

    var explicit = version && version.change_number != null && String(version.change_number).trim() !== ''
      ? String(version.change_number).trim() : null;
    if (explicit !== null) return explicit;

    var fromVersionId = changeNumberFromVersionId(version);
    if (fromVersionId !== null) return fromVersionId;

    return null;
  }

  function changeNumber(version, fallback) {
    var inferred = inferredChangeNumber(version);
    if (inferred !== null) return inferred;
    if (fallback != null && String(fallback).trim() !== '' && !isBaseVersion(version)) return String(fallback).trim();
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

  function normalizeState() {
    var data = Array.isArray(window.normsData) ? window.normsData : [];
    var changed = false;

    data.forEach(function (norm) {
      var versions = Array.isArray(norm.versions) ? norm.versions : [];

      versions.forEach(function (version) {
        var filename = version && (version.original_filename || version.filename || version.file);
        var filenameChange = changeNumberFromFilename(filename);
        var change = inferredChangeNumber(version);

        // The filename is authoritative; a base PDF is explicitly amendment-free.
        if (filenameChange !== null) {
          if (String(version.change_number || '') !== filenameChange) {
            version.change_number = filenameChange;
            changed = true;
          }
        } else if (isBaseVersion(version)) {
          if (version.change_number != null) {
            version.change_number = null;
            changed = true;
          }
        } else if (change !== null) {
          if (String(version.change_number || '') !== change) {
            version.change_number = change;
            changed = true;
          }
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
        norm.current_change_number = changeNumber(currentVersion, norm.current_change_number);
        norm.version_id = currentVersion.version_id || currentVersion.id;
      }

      var canonical = canonicalTitle(norm.number || norm.id);
      if (canonical && norm.title !== canonical) {
        norm.title = canonical;
        changed = true;
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
        panel.querySelectorAll('.norm-version-row').forEach(function (row) {
          var filenameNode = row.querySelector('.norm-version-file-name');
          var label = row.querySelector('.norm-version-label');
          if (!filenameNode || !label) return;

          var filename = filenameNode.getAttribute('title') || filenameNode.textContent || '';
          var filenameChange = changeNumberFromFilename(filename);
          var text = filenameChange === null ? 'Без изменений' : 'Изменение №' + filenameChange;
          var currentText = label.textContent || '';
          var isCurrentRow = /·\s*действующая\s*$/i.test(currentText);
          label.textContent = text + (isCurrentRow ? ' · действующая' : ' · архивная');
        });
      }

      var card = document.querySelector('[data-norm-card="' + CSS.escape(String(norm.id)) + '"]');
      if (card) {
        var title = card.querySelector('.norm-card-title');
        var subtitle = card.querySelector('.norm-card-subtitle');
        var current = versions.find(function (v) { return isCurrent(v, norm); });
        var number = norm.number || norm.id;
        var change = current ? changeNumber(current, norm.current_change_number) : null;

        if (title) {
          title.textContent = number + (current
            ? (change === null ? ' — Без изменений' : ' — Изменение №' + change)
            : ' — Действующая редакция не выбрана');
        }
        if (subtitle) subtitle.textContent = canonicalTitle(number) || norm.title || number;
      }
    });
  }

  function normalizeAndPatch() {
    normalizeState();
    patchRenderedRows();
  }

  // The first pass is immediate; the short retry window covers asynchronous API loading.
  normalizeAndPatch();
  var attempts = 0;
  var timer = setInterval(function () {
    attempts += 1;
    normalizeAndPatch();
    if (attempts >= 40) clearInterval(timer);
  }, 300);

  console.log('[VKS Expert AI][Norms] metadata compatibility fix v11 loaded');
})();
