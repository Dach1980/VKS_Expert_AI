// Project Expert AI — one logical Norms card per canonical document number.
(function () {
  function numberGroup(value) {
    var text = String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
    var match = text.match(/(?:сп|гост(?: р)?|снип|тр|фз)\s*[0-9]+\.[0-9]+/i);
    return match ? match[0].replace(/\s+/g, ' ').trim() : text;
  }
  function isCurrent(version) {
    return !!(version && String(version.status || '').toLowerCase() === 'current' && version.current_selected_by_user === true);
  }
  function changeNumber(version) {
    if (version && version.change_number != null && String(version.change_number).trim() !== '') {
      return String(version.change_number).trim();
    }
    var filename = String((version && (version.original_filename || version.filename || version.file)) || '');
    var match = filename.replace(/[_-]+/g, ' ').match(/(?:\bизм(?:енение|енения)?\.?|\bизменени[ея]|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }
  function normalize(data) {
    var groups = new Map();
    (Array.isArray(data) ? data : []).forEach(function (item) {
      var key = numberGroup(item.number || item.id);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    var result = [];
    groups.forEach(function (items) {
      items.sort(function (a, b) { return (Array.isArray(b.versions) ? b.versions.length : 0) - (Array.isArray(a.versions) ? a.versions.length : 0); });
      var base = Object.assign({}, items[0]);
      var versions = [];
      items.forEach(function (item) {
        (Array.isArray(item.versions) ? item.versions : []).forEach(function (version) {
          var copy = Object.assign({}, version);
          copy.document_id = copy.document_id || item.document_id || item.id;
          copy.version_id = copy.version_id || copy.id;
          versions.push(copy);
        });
      });
      var byVersion = new Map();
      versions.forEach(function (version) { byVersion.set(String(version.document_id) + ':' + String(version.version_id), version); });
      versions = Array.from(byVersion.values());
      var current = versions.filter(isCurrent);
      base.document_id = base.document_id || base.id;
      base.id = base.document_id;
      base.versions = versions;
      base.version_id = current.length === 1 ? current[0].version_id : null;
      base.current_change_number = current.length === 1 ? changeNumber(current[0]) : null;
      base.effective_from = current.length === 1 ? (current[0].effective_from || null) : null;
      base.processing = current.length === 1 ? (current[0].processing || {}) : {};
      result.push(base);
    });
    return result;
  }
  function install() {
    if (window.__normsRegistryFixInstalled || typeof window.loadNorms !== 'function') return !!window.__normsRegistryFixInstalled;
    window.__normsRegistryFixInstalled = true;
    var originalLoad = window.loadNorms;
    window.loadNorms = async function (expandIds) {
      var data = await originalLoad(expandIds);
      var normalized = normalize(data);
      window.normsData = normalized;
      if (typeof window.renderNorms === 'function') window.renderNorms();
      if (typeof window.updateKnowledgeBaseCounters === 'function') window.updateKnowledgeBaseCounters();
      (expandIds || []).forEach(function (id) {
        var panel = document.getElementById('normVersions-' + id);
        if (panel) panel.removeAttribute('hidden');
      });
      return normalized;
    };
    return true;
  }
  if (!install()) {
    document.addEventListener('DOMContentLoaded', install, { once: true });
    setTimeout(install, 0);
  }
})();