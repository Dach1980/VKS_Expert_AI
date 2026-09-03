// Project Expert AI — authoritative filename-based amendment labels.
// The PDF filename is the only source used for the visible amendment number.
(function () {
  function amendmentFromFilename(value) {
    var text = String(value || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ')
      .trim();
    var match = text.match(/(?:\bизм(?:енение|енения)?\.?|\bизменени[ея]\.?|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }

  function filenameOf(version) {
    return String(version && (version.original_filename || version.filename || version.file) || '').trim();
  }

  function amendmentOf(version) {
    var fromFilename = amendmentFromFilename(filenameOf(version));
    if (fromFilename !== null) return fromFilename;
    return version && version.change_number != null && String(version.change_number).trim() !== ''
      ? String(version.change_number).trim()
      : null;
  }

  function isCurrent(version) {
    return !!(version && String(version.status || '').toLowerCase() === 'current');
  }

  function normalize(data) {
    var result = [];
    var groups = new Map();
    (Array.isArray(data) ? data : []).forEach(function (item) {
      var key = String(item.number || item.id || '').replace(/\s+/g, ' ').trim().toLowerCase();
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });

    groups.forEach(function (items) {
      items.sort(function (a, b) {
        return (Array.isArray(b.versions) ? b.versions.length : 0) - (Array.isArray(a.versions) ? a.versions.length : 0);
      });
      var base = Object.assign({}, items[0]);
      var versions = [];
      items.forEach(function (item) {
        (Array.isArray(item.versions) ? item.versions : []).forEach(function (sourceVersion) {
          var version = Object.assign({}, sourceVersion);
          version.document_id = version.document_id || item.document_id || item.id;
          version.version_id = version.version_id || version.id;
          var filename = filenameOf(version);
          var filenameChange = amendmentFromFilename(filename);
          if (filenameChange !== null) version.change_number = filenameChange;
          versions.push(version);
        });
      });

      var unique = new Map();
      versions.forEach(function (version) {
        unique.set(String(version.document_id) + ':' + String(version.version_id), version);
      });
      versions = Array.from(unique.values());

      var current = versions.find(isCurrent) || null;
      base.document_id = base.document_id || base.id;
      base.id = base.document_id;
      base.versions = versions;
      base.version_id = current ? (current.version_id || current.id) : null;
      base.current_change_number = current ? amendmentOf(current) : null;
      base.effective_from = current ? (current.effective_from || null) : null;
      base.processing = current ? (current.processing || {}) : {};
      result.push(base);
    });
    return result;
  }

  function patchVisibleLabels() {
    document.querySelectorAll('.norm-version-row').forEach(function (row) {
      var filenameNode = row.querySelector('.norm-version-file-name');
      var label = row.querySelector('.norm-version-label');
      if (!filenameNode || !label) return;
      var filename = filenameNode.getAttribute('title') || filenameNode.textContent || '';
      var change = amendmentFromFilename(filename);
      var current = /·\s*действующая\s*$/i.test(label.textContent || '');
      label.textContent = (change === null ? 'Без изменений' : 'Изменение №' + change)
        + (current ? ' · действующая' : ' · архивная');
    });

    document.querySelectorAll('.norm-card').forEach(function (card) {
      var title = card.querySelector('.norm-card-title');
      if (!title) return;
      var currentRow = Array.from(card.querySelectorAll('.norm-version-row')).find(function (row) {
        var label = row.querySelector('.norm-version-label');
        return label && /·\s*действующая\s*$/i.test(label.textContent || '');
      });
      if (!currentRow) return;
      var filenameNode = currentRow.querySelector('.norm-version-file-name');
      if (!filenameNode) return;
      var filename = filenameNode.getAttribute('title') || filenameNode.textContent || '';
      var change = amendmentFromFilename(filename);
      var number = String(title.textContent || '').split(' — ')[0].trim();
      title.textContent = number + (change === null ? ' — Без изменений' : ' — Изменение №' + change);
    });
  }

  function install() {
    if (window.__authoritativeNormFilenameFix) return;
    window.__authoritativeNormFilenameFix = true;

    if (typeof window.loadNorms === 'function') {
      var originalLoadNorms = window.loadNorms;
      window.loadNorms = async function (expandIds) {
        var data = await originalLoadNorms(expandIds);
        var normalized = normalize(data);
        window.normsData = normalized;
        if (typeof window.renderNorms === 'function') window.renderNorms();
        (expandIds || []).forEach(function (id) {
          var panel = document.getElementById('normVersions-' + id);
          if (panel) panel.removeAttribute('hidden');
        });
        patchVisibleLabels();
        return normalized;
      };
    }

    var observer = new MutationObserver(function () { patchVisibleLabels(); });
    var root = document.getElementById('normsGrid') || document.body;
    if (root) observer.observe(root, { childList: true, subtree: true, characterData: true });
    patchVisibleLabels();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
  setTimeout(install, 0);
  setTimeout(install, 500);
})();
