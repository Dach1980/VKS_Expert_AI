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

  function cleanText(value) {
    return String(value == null ? '' : value)
      .replace(/\r/g, ' ')
      .replace(/\*\*/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function installStyles() {
    if (document.getElementById('vksFinalAnswerStyles')) return;
    const style = document.createElement('style');
    style.id = 'vksFinalAnswerStyles';
    style.textContent = `
      .vks-final-answer { line-height: 1.65; }
      .vks-final-answer h3 { margin: 18px 0 9px; font-size: 16px; font-weight: 700; }
      .vks-final-answer h3:first-child { margin-top: 0; }
      .vks-final-answer .final-lead { margin: 8px 0 15px; padding: 13px 15px; border-radius: 10px; background: var(--bg-secondary, rgba(127,127,127,.08)); font-weight: 600; }
      .vks-final-answer .final-table-wrap { overflow-x: auto; margin: 10px 0 15px; }
      .vks-final-answer table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .vks-final-answer th, .vks-final-answer td { padding: 9px 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); text-align: left; vertical-align: top; }
      .vks-final-answer th { font-weight: 700; background: var(--bg-secondary, rgba(127,127,127,.08)); }
      .vks-final-answer .final-source { margin: 8px 0 14px; padding: 11px 13px; border-left: 3px solid var(--border-color, rgba(127,127,127,.35)); }
      .vks-final-answer .final-conclusion { margin-top: 18px; padding: 13px 15px; border-radius: 10px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); }
      .vks-final-answer .final-conclusion-title { font-weight: 700; margin-bottom: 6px; }
      .sources-block { margin-top: 18px; }
      .sources-table-wrap { overflow-x: auto; margin-top: 9px; }
      .sources-table { width: 100%; border-collapse: collapse; font-size: 13px; }
      .sources-table th, .sources-table td { padding: 8px 9px; border: 1px solid var(--border-color, rgba(127,127,127,.22)); text-align: left; }
      .sources-table th { font-weight: 700; background: var(--bg-secondary, rgba(127,127,127,.08)); }
      .rag-final-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
      .rag-final-card { padding: 9px 10px; border: 1px solid var(--border-color, rgba(127,127,127,.18)); border-radius: 9px; }
      .rag-final-card-label { font-size: 11px; opacity: .7; }
      .rag-final-card-value { margin-top: 2px; font-weight: 700; }
      .rag-final-section { margin-top: 14px; }
      .rag-final-item { padding: 8px 0; border-top: 1px solid var(--border-color, rgba(127,127,127,.14)); }
      .rag-final-item:first-child { border-top: 0; }
      .rag-final-muted { opacity: .7; }
      .rag-final-method { font-size: 11px; opacity: .65; }
      @media (max-width: 700px) { .rag-final-summary { grid-template-columns: 1fr; } }
    `;
    document.head.appendChild(style);
  }

  function extractSections(answer) {
    const text = String(answer == null ? '' : answer).replace(/\r/g, ' ').trim();
    const withoutSources = text.replace(/\*{0,2}Источники\*{0,2}[\s\S]*$/i, '').trim();
    const labels = [
      { name: 'lead', re: /\*{0,2}Краткий вывод\*{0,2}\s*/i },
      { name: 'requirements', re: /\*{0,2}(?:Расчет\s*\/\s*требования|Требования)\*{0,2}\s*/i },
      { name: 'source', re: /\*{0,2}Источник\s*СП\*{0,2}\s*/i }
    ];
    const matches = labels.map(label => {
      const match = label.re.exec(withoutSources);
      return match ? { name: label.name, start: match.index, end: match.index + match[0].length } : null;
    }).filter(Boolean).sort((a, b) => a.start - b.start);

    const result = { lead: '', requirements: '', source: '' };
    matches.forEach((match, index) => {
      const next = matches[index + 1];
      result[match.name] = withoutSources.slice(match.end, next ? next.start : withoutSources.length).trim();
    });
    return result;
  }

  function extractRequirementRows(text) {
    const cleaned = cleanText(text);
    if (!cleaned) return [];
    const rows = [];
    const pattern = /(\d+(?:\.\d+){1,4})\s+(.+?)(?=\s+\d+(?:\.\d+){1,4}\s+|$)/g;
    let match;
    while ((match = pattern.exec(cleaned)) !== null) rows.push([match[1], match[2].trim()]);
    if (!rows.length) rows.push(['—', cleaned]);
    return rows;
  }

  function renderRequirements(text) {
    const rows = extractRequirementRows(text);
    if (!rows.length) return '';
    return '<div class="final-table-wrap"><table><thead><tr><th>Пункт</th><th>Требование</th></tr></thead><tbody>' +
      rows.map(row => `<tr><td>${inline(row[0])}</td><td>${inline(row[1])}</td></tr>`).join('') +
      '</tbody></table></div>';
  }

  function renderFinalAnswer(answer) {
    installStyles();
    const sections = extractSections(answer);
    const rows = extractRequirementRows(sections.requirements);
    const lead = cleanText(sections.lead) || (rows.length ? cleanText(rows[0][1]) : 'Ответ сформирован на основании найденного нормативного контекста.');
    const source = cleanText(sections.source);

    let html = '<div class="vks-final-answer">';
    html += '<h3>Краткий вывод</h3>';
    html += `<div class="final-lead">${inline(lead)}</div>`;

    if (rows.length) {
      html += '<h3>Требования</h3>';
      html += renderRequirements(sections.requirements);
    }

    if (source) {
      html += '<h3>Источник СП</h3>';
      html += `<div class="final-source">${inline(source)}</div>`;
    }

    html += '<div class="final-conclusion">';
    html += '<div class="final-conclusion-title">Вывод</div>';
    if (rows.length === 1 && rows[0][0] !== '—') {
      html += `<div>Требование <strong>${inline(rows[0][0])}</strong>: ${inline(rows[0][1])}</div>`;
    } else {
      html += `<div>${inline(lead)}</div>`;
    }
    html += '</div></div>';
    return html;
  }

  function selectRelevantSources(sources, answer) {
    if (!Array.isArray(sources) || !sources.length) return [];
    const sections = extractSections(answer);
    const rows = extractRequirementRows(sections.requirements);
    const point = rows.length && rows[0][0] !== '—' ? rows[0][0] : '';
    const ranked = sources.map((source, index) => {
      const content = String(source?.content || source?.text || '');
      let priority = Number(source?.score || 0);
      if (point && content.includes(point)) priority += 100;
      return { source, index, priority };
    }).sort((a, b) => b.priority - a.priority || a.index - b.index);
    const selected = ranked[0]?.source;
    return selected ? [selected] : [];
  }

  function renderDiagnostics(diagnostics, notice) {
    if (!diagnostics) return;
    const retrieved = Array.isArray(diagnostics.retrieved) ? diagnostics.retrieved : [];
    const accepted = Array.isArray(diagnostics.accepted) ? diagnostics.accepted : [];
    const rejected = Array.isArray(diagnostics.rejected) ? diagnostics.rejected : [];
    const intent = diagnostics.intent || {};
    const confidence = Number(diagnostics.evidence_confidence || 0).toFixed(3);

    const block = document.createElement('details');
    block.className = 'rag-debug-panel';
    block.open = false;
    block.innerHTML = `
      <summary>Диагностика RAG</summary>
      <div class="rag-debug-body">
        ${notice ? `<div class="rag-debug-notice">${escapeHtml(notice)}</div>` : ''}
        <div class="rag-final-summary">
          <div class="rag-final-card"><div class="rag-final-card-label">Найдено</div><div class="rag-final-card-value">${retrieved.length}</div></div>
          <div class="rag-final-card"><div class="rag-final-card-label">Принято</div><div class="rag-final-card-value">${accepted.length}</div></div>
          <div class="rag-final-card"><div class="rag-final-card-label">Уверенность</div><div class="rag-final-card-value">${confidence}</div></div>
        </div>
        <div class="rag-final-section"><b>Найденные фрагменты</b>${retrieved.map((item, index) => `
          <div class="rag-final-item">
            <div><strong>#${index + 1}</strong> · ${escapeHtml(formatSourceDocument(item))} · стр. ${escapeHtml(item.page || 0)} · score ${Number(item.score || 0).toFixed(3)}</div>
            <div class="rag-final-method">Способ поиска: ${escapeHtml(item.source === 'lexical' ? 'точное совпадение терминов' : item.source === 'faiss' ? 'семантический поиск' : item.source || 'поиск')}</div>
            <div class="rag-debug-text">${formatContent(item.content)}</div>
          </div>`).join('') || '<div class="rag-final-muted">Фрагменты не найдены.</div>'}</div>
        <div class="rag-final-section"><b>Проверенные фрагменты</b>${accepted.map(item => `
          <div class="rag-final-item">${escapeHtml(formatSourceDocument(item))} · стр. ${escapeHtml(item.page || 0)}<div class="rag-debug-text">${formatContent(item.content)}</div></div>`).join('') || '<div class="rag-final-muted">Нет принятых фрагментов.</div>'}</div>
        <div class="rag-final-section"><b>Отклонённые фрагменты</b><div class="rag-final-muted">${rejected.length ? `${rejected.length} фрагмента не прошли проверку релевантности.` : 'Нет отклонённых фрагментов.'}</div></div>
        <div class="rag-final-section"><b>Параметры запроса</b><div class="rag-final-item"><b>Intent:</b> ${escapeHtml(JSON.stringify(intent))}</div><div class="rag-final-item"><b>Расширенный запрос:</b><pre>${escapeHtml(diagnostics.enhanced_query || '')}</pre></div></div>
      </div>`;

    const aiMessages = document.querySelectorAll('#chatMessages .message.ai');
    const target = aiMessages[aiMessages.length - 1];
    if (target) target.querySelector('.message-content')?.appendChild(block);
  }

  // Presentation-only overrides. API calls and RAG processing remain untouched.
  if (typeof window.renderAnswer === 'function') window.renderAnswer = renderFinalAnswer;
  if (typeof window.addDiagnosticsToChat === 'function') window.addDiagnosticsToChat = renderDiagnostics;
  if (typeof window.addMessageToChat === 'function') {
    const originalAddMessageToChat = window.addMessageToChat;
    window.addMessageToChat = function (role, content, sources = null) {
      if (role === 'ai' && Array.isArray(sources)) sources = selectRelevantSources(sources, content);
      return originalAddMessageToChat(role, content, sources);
    };
  }
})();
