// Project Expert AI — final answer presentation only.
// This file changes how the already generated answer is rendered in the UI.
// It does not call, alter, or reconfigure the RAG pipeline.

(function () {
  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function inline(value) {
    return escapeHtml(value)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  function installStyles() {
    if (document.getElementById('vksFinalAnswerStyles')) return;
    const style = document.createElement('style');
    style.id = 'vksFinalAnswerStyles';
    style.textContent = `
      .vks-final-answer { line-height: 1.65; }
      .vks-final-answer h3 { margin: 18px 0 9px; font-size: 16px; font-weight: 700; }
      .vks-final-answer h3:first-child { margin-top: 0; }
      .vks-final-answer p { margin: 7px 0; }
      .vks-final-answer .final-lead { margin: 8px 0 15px; padding: 13px 15px; border-radius: 10px; background: var(--bg-secondary, rgba(127,127,127,.08)); font-weight: 600; }
      .vks-final-answer .final-source { margin: 8px 0 14px; padding: 11px 13px; border-left: 3px solid var(--border-color, rgba(127,127,127,.35)); }
      .vks-final-answer .final-table-wrap { overflow-x: auto; margin: 10px 0 15px; }
      .vks-final-answer table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .vks-final-answer th, .vks-final-answer td { padding: 9px 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); text-align: left; vertical-align: top; }
      .vks-final-answer th { font-weight: 700; background: var(--bg-secondary, rgba(127,127,127,.08)); }
      .vks-final-answer .final-conclusion { margin-top: 18px; padding: 13px 15px; border-radius: 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); }
      .vks-final-answer .final-conclusion-title { font-weight: 700; margin-bottom: 6px; }
      .vks-final-answer ul { margin: 8px 0 10px 20px; }
      .vks-final-answer li { margin: 4px 0; }
    `;
    document.head.appendChild(style);
  }

  function splitSections(answer) {
    const text = String(answer == null ? '' : answer).trim();
    const normalized = text
      .replace(/\r/g, '')
      .replace(/\*\*Источники\*\*[\s\S]*$/i, '')
      .trim();

    const conclusionMatch = normalized.match(/(?:^|\n)\s*Краткий вывод\s*([\s\S]*?)(?=\n\s*(?:Расчет\s*\/\s*требования|Требования|Источник\s*СП)\b|$)/i);
    const requirementsMatch = normalized.match(/(?:^|\n)\s*(?:Расчет\s*\/\s*требования|Требования)\s*([\s\S]*?)(?=\n\s*Источник\s*СП\b|$)/i);
    const sourceMatch = normalized.match(/(?:^|\n)\s*Источник\s*СП\s*([\s\S]*)$/i);

    return {
      lead: conclusionMatch ? conclusionMatch[1].trim() : '',
      requirements: requirementsMatch ? requirementsMatch[1].trim() : normalized,
      source: sourceMatch ? sourceMatch[1].trim() : ''
    };
  }

  function extractRequirementRows(text) {
    const rows = [];
    const lines = String(text || '').split('\n').map(line => line.trim()).filter(Boolean);

    lines.forEach(line => {
      if (/^\|.*\|$/.test(line)) return;
      const match = line.match(/^(\d+(?:\.\d+){1,4})\s+(.+)$/);
      if (match) {
        rows.push([match[1], match[2].trim()]);
      }
    });

    if (!rows.length && text) {
      rows.push(['—', text.replace(/\s+/g, ' ').trim()]);
    }
    return rows;
  }

  function renderRequirementContent(text) {
    const rows = extractRequirementRows(text);
    if (!rows.length) return '';

    return '<div class="final-table-wrap"><table><thead><tr><th>Пункт</th><th>Требование</th></tr></thead><tbody>' +
      rows.map(row => `<tr><td>${inline(row[0])}</td><td>${inline(row[1])}</td></tr>`).join('') +
      '</tbody></table></div>';
  }

  function renderFinalAnswer(answer) {
    installStyles();
    const sections = splitSections(answer);
    const lead = sections.lead || 'Ответ сформирован на основании найденного нормативного контекста.';
    const requirements = sections.requirements || '';
    const source = sections.source || '';

    let html = '<div class="vks-final-answer">';
    html += '<h3>Краткий вывод</h3>';
    html += `<div class="final-lead">${inline(lead)}</div>`;

    if (requirements) {
      html += '<h3>Требования</h3>';
      html += renderRequirementContent(requirements);
    }

    if (source) {
      html += '<h3>Источник СП</h3>';
      html += `<div class="final-source">${inline(source.replace(/\n+/g, ' '))}</div>`;
    }

    html += '<div class="final-conclusion">';
    html += '<div class="final-conclusion-title">Выводы</div>';
    html += `<div>${inline(lead)}</div>`;
    if (requirements) {
      const rows = extractRequirementRows(requirements);
      if (rows.length === 1 && rows[0][0] === '—') {
        html += `<div style="margin-top:6px">${inline(rows[0][1])}</div>`;
      } else if (rows.length > 0) {
        html += '<ul>' + rows.map(row => `<li><strong>${inline(row[0])}</strong> — ${inline(row[1])}</li>`).join('') + '</ul>';
      }
    }
    html += '</div></div>';
    return html;
  }

  // vks-chat.js is loaded immediately before this file. Override only the
  // presentation function; all API/RAG calls remain in the original module.
  if (typeof window.renderAnswer === 'function') {
    window.renderAnswer = renderFinalAnswer;
  }
})();
