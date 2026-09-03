// Project Expert AI — final UI guard for normative amendment labels.
// The uploaded PDF filename is the authoritative source for the amendment number.
(function installNormAmendmentLabelFix() {
  function amendmentFromFilename(filename) {
    var text = String(filename || '')
      .replace(/[\u00A0\u202F]/g, ' ')
      .replace(/[_-]+/g, ' ');
    var match = text.match(/(?:\bизм(?:енение|енения)?\.?|\bизменени[ея]\.?|\bamendment)\s*№?\s*\.?\s*(\d+)\b/i);
    return match ? match[1] : null;
  }

  function patchGrid() {
    var grid = document.getElementById('normsGrid');
    if (!grid) return;

    grid.querySelectorAll('.norm-card').forEach(function (card) {
      var currentRow = card.querySelector('.norm-version-row');
      var title = card.querySelector('.norm-card-title');
      var rows = card.querySelectorAll('.norm-version-row');

      rows.forEach(function (row) {
        var filenameNode = row.querySelector('.norm-version-file-name');
        var label = row.querySelector('.norm-version-label');
        if (!filenameNode || !label) return;

        var filename = filenameNode.getAttribute('title') || filenameNode.textContent || '';
        var change = amendmentFromFilename(filename);
        var current = /·\s*действующая\s*$/i.test(label.textContent || '');
        var next = (change === null ? 'Без изменений' : 'Изменение №' + change)
          + (current ? ' · действующая' : ' · архивная');
        if (label.textContent !== next) label.textContent = next;
      });

      if (title && currentRow) {
        var currentFilenameNode = currentRow.querySelector('.norm-version-file-name');
        var currentFilename = currentFilenameNode
          ? (currentFilenameNode.getAttribute('title') || currentFilenameNode.textContent || '')
          : '';
        var currentChange = amendmentFromFilename(currentFilename);
        var baseNumber = String(title.textContent || '').replace(/\s*[—-]\s*(?:Без изменений|Изменение\s*№\s*\d+|Действующая редакция не выбрана).*$/i, '').trim();
        var nextTitle = baseNumber + (currentChange === null
          ? ' — Без изменений'
          : ' — Изменение №' + currentChange);
        if (title.textContent !== nextTitle) title.textContent = nextTitle;
      }
    });
  }

  function install() {
    var grid = document.getElementById('normsGrid');
    if (!grid) {
      setTimeout(install, 100);
      return;
    }
    patchGrid();
    var observer = new MutationObserver(function () { patchGrid(); });
    observer.observe(grid, { childList: true, subtree: true, characterData: true });
    window.patchNormAmendmentLabels = patchGrid;
    console.log('[Project Expert AI][Norms] final amendment label guard loaded');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})();
