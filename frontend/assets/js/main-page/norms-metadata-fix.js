// Project Expert AI — compatibility fix for legacy norm-version metadata.
// Keeps amendment numbers owned by the uploaded PDF filename and repairs
// frontend state from older registry records that predate original_filename.

(function installNormMetadataFix() {
  function changeNumberFromFilename(filename) {
    var text = String(filename || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ')
      .replace(/[Ёё]/g, 'е');
    var match = text.match(/(?:\bизм(?:енение|енения)?\b|\bизменени[ея]\b|\bamendment\b)\s*\.?\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }

  function normalize() {
    var data = Array.isArray(window.normsData) ? window.normsData : [];
    var changed = false;

    data.forEach(function (norm) {
      var versions = Array.isArray(norm.versions) ? norm.versions : [];
      var selectedId = norm.version_id == null ? null : String(norm.version_id);

      versions.forEach(function (version) {
        var filename = String(version.original_filename || version.filename || '').trim();
        var change = changeNumberFromFilename(filename);
        if (change !== null && String(version.change_number || '') !== change) {
          version.change_number = change;
          changed = true;
        }

        // The API exposes the selected version at document level. Use it as
        // the authoritative UI signal when legacy records contain stale
        // status/current flags on individual versions.
        if (selectedId !== null) {
          var versionId = String(version.version_id || version.id || '');
          var shouldBeCurrent = versionId === selectedId;
          if (Boolean(version.current_selected_by_user) !== shouldBeCurrent ||
              (shouldBeCurrent && version.status !== 'current') ||
              (!shouldBeCurrent && version.status === 'current')) {
            version.current_selected_by_user = shouldBeCurrent;
            version.status = shouldBeCurrent ? 'current' : 'superseded';
            changed = true;
          }
        }
      });

      var current = versions.find(function (v) {
        return v.current_selected_by_user === true && v.status === 'current';
      });
      if (current) {
        var currentChange = current.change_number != null
          ? String(current.change_number)
          : changeNumberFromFilename(current.original_filename || current.filename);
        var next = currentChange === null ? null : String(currentChange);
        if (String(norm.current_change_number == null ? '' : norm.current_change_number) !== String(next == null ? '' : next)) {
          norm.current_change_number = next;
          changed = true;
        }
      }
    });

    if (changed && typeof window.renderNorms === 'function') {
      window.renderNorms();
    }
  }

  // norms.js loads its data asynchronously and also refreshes it after
  // activation/indexing. A short-lived observer repairs only legacy metadata
  // and then stops once the state is stable.
  var attempts = 0;
  var timer = setInterval(function () {
    attempts += 1;
    normalize();
    if (attempts >= 30) clearInterval(timer);
  }, 300);

  console.log('[VKS Expert AI][Norms] legacy metadata compatibility fix loaded');
})();
