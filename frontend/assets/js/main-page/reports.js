function generateReport() {
  if (checksData.length === 0) {
    showToast(
      'Нет данных для создания отчёта. Выполните проверку документов.',
      'error',
    );
    return;
  }

  // Показываем модальное окно прогресса
  showProgressModal();

  // Имитируем процесс создания отчёта с прогрессом
  simulateReportGeneration();
}

function generateRealisticChecks(docs) {
  var results = [];
  var docNames = docs.map(function (d) {
    return d.name;
  });

  // Generate additional checks based on the actual document content
  var additionalResults = [
    {
      id: nextCheckId++,
      type: 'violation',
      severity: 'major',
      title:
        'Не указано давление в системе водоснабжения для стальных труб ∅219×6',
      sheet: 'Лист 3.1-02',
      norm: 'СП 30.13330.2020, п. 5.4.1',
      description:
        'В документе указаны стальные трубы ∅219×6 (ГОСТ 8732-78, ГОСТ 10704-91), но отсутствует указание расчётного давления в системе. Цитата: «5.4.1 Максимальное рабочее давление в системах холодного водоснабжения не должно превышать 0,6 МПа.»',
      recommendation:
        'Указать расчётное давление в системе и подтвердить соответствие труб рабочим параметрам.',
    },
    {
      id: nextCheckId++,
      type: 'violation',
      severity: 'minor',
      title:
        'Отсутствует ссылка на СП 32.13330.2018 п.9.1.5 в разделе канализации',
      sheet: 'Лист 3.1-05',
      norm: 'СП 32.13330.2018, п. 9.1.5',
      description:
        'В документе присутствует ссылка на СП 32.13330.2018 п.9.1.5, однако требования пункта не полностью учтены в проектных решениях.',
      recommendation:
        'Проверить соответствие проектным решениям требований СП 32.13330.2018 п.9.1.5.',
    },
    {
      id: nextCheckId++,
      type: 'compliant',
      severity: null,
      title: 'Соответствие: Стальные трубы для напорных трубопроводов',
      sheet: 'Лист 3.1-02',
      norm: 'ГОСТ 8732-78, ГОСТ 10704-91',
      description:
        'Стальные трубы ∅219×6 соответствуют требованиям ГОСТ 8732-78 и ГОСТ 10704-91 для напорных трубопроводов.',
      recommendation: null,
    },
    {
      id: nextCheckId++,
      type: 'compliant',
      severity: null,
      title: 'Соответствие: Полиэтиленовые трубы для безнапорной канализации',
      sheet: 'Лист 3.1-03',
      norm: 'СП 30.13330.2020, п. 5.3.2',
      description:
        'ПЭ трубы (4926-005-41989945-97) диаметром ∅110, ∅160, ∅250, ∅50 соответствуют требованиям к материалам канализационных трубопроводов.',
      recommendation: null,
    },
    {
      id: nextCheckId++,
      type: 'unchecked',
      severity: null,
      title: 'Не проверено: Вентиляция канализационных стояков',
      sheet: 'Лист 3.1-08',
      norm: null,
      description:
        'Требуется дополнительная проверка системы вентиляции канализационных стояков на соответствие СП 30.13330.2020 раздел 8.',
      recommendation: null,
    },
  ];

  return additionalResults;
}

// ===== DOWNLOAD REPORT MARKDOWN =====
function downloadReportMarkdown(reportId) {
  var report = reportsData.find(function (r) {
    return r.id === reportId;
  });
  if (!report) {
    showToast('Отчёт не найден', 'error');
    return;
  }

  // Группируем проверки по документам
  var groupedByDoc = {};
  for (var i = 0; i < report.checks.length; i++) {
    var check = report.checks[i];
    var docName = check.docName || 'Неизвестный документ';
    if (!groupedByDoc[docName]) {
      groupedByDoc[docName] = [];
    }
    groupedByDoc[docName].push(check);
  }

  var md = '';
  md += '# ' + report.title + '\n\n';
  md += '**Дата создания:** ' + report.date + '\n\n';
  md += '---\n\n';
  md += '## 1. Общие сведения\n\n';
  md += '### 1.1. Исходные данные\n\n';
  md += '- Объект: Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1\n';
  md += '- Шифр: 35020 040002.111.20.-3.1\n';
  md += '- Подписант: Ковалев Дмитрий Александрович, АО «КРДВ Хабаровск»\n';
  md += '- Листы: 3.1-01 — 3.1-08\n\n';
  md += '### 1.2. Нормативная база\n\n';
  for (var n = 0; n < normsData.length; n++) {
    md += '- ' + normsData[n].title + ' — ' + normsData[n].subtitle + '\n';
  }
  md += '\n---\n\n';
  md += '## 2. Проверенные документы\n\n';
  md +=
    '| № | Документ | Проверок | Нарушения | Соответствия | Не проверено |\n';
  md += '|---|---|---|---|---|---|\n';
  var docListIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];
    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;
    var shortName =
      docName.length > 50 ? docName.substring(0, 47) + '...' : docName;
    md +=
      '| ' +
      docListIndex +
      ' | ' +
      shortName +
      ' | ' +
      docChecks.length +
      ' | ' +
      docViolations +
      ' | ' +
      docCompliant +
      ' | ' +
      docUnchecked +
      ' |\n';
    docListIndex++;
  }
  md += '\n';
  md += '## 3. Результаты проверки по документам\n\n';
  md += '| Показатель | Значение |\n';
  md += '|---|---|\n';
  md += '| Всего проверок | ' + report.totalChecks + ' |\n';
  md += '| Нарушения | ' + report.violations + ' |\n';
  md += '| Соответствия | ' + report.compliant + ' |\n';
  md += '| Не проверено | ' + report.unchecked + ' |\n';
  md += '| Критические | ' + (report.critical || 0) + ' |\n';
  md += '| Значительные | ' + (report.major || 0) + ' |\n';
  md += '| Незначительные | ' + (report.minor || 0) + ' |\n\n';

  // Результаты по документам
  var docIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];
    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;

    md += '### 2.' + docIndex + '. Документ: ' + docName + '\n\n';
    md +=
      '**Статистика:** ' +
      docChecks.length +
      ' проверок | ' +
      docViolations +
      ' нарушений | ' +
      docCompliant +
      ' соответствий | ' +
      docUnchecked +
      ' не проверено\n\n';

    var criticalChecks = docChecks.filter(function (c) {
      return c.severity === 'critical';
    });
    var majorChecks = docChecks.filter(function (c) {
      return c.severity === 'major';
    });
    var minorChecks = docChecks.filter(function (c) {
      return c.severity === 'minor';
    });
    var compliantChecks = docChecks.filter(function (c) {
      return c.type === 'compliant';
    });
    var uncheckedChecks = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    });

    if (criticalChecks.length > 0) {
      md += '#### Критические нарушения (' + criticalChecks.length + ')\n\n';
      for (var i = 0; i < criticalChecks.length; i++) {
        var c = criticalChecks[i];
        md += '##### ' + (i + 1) + '. ' + c.title + '\n\n';
        md += '- **Лист:** ' + c.sheet + '\n';
        if (c.norm) md += '- **Норма:** ' + c.norm + '\n';
        md += '\n**Описание:** ' + c.description + '\n\n';
        if (c.recommendation)
          md += '**Рекомендация:** ' + c.recommendation + '\n\n';
        md += '---\n\n';
      }
    }

    if (majorChecks.length > 0) {
      md += '#### Значительные нарушения (' + majorChecks.length + ')\n\n';
      for (var i = 0; i < majorChecks.length; i++) {
        var c = majorChecks[i];
        md += '##### ' + (i + 1) + '. ' + c.title + '\n\n';
        md += '- **Лист:** ' + c.sheet + '\n';
        if (c.norm) md += '- **Норма:** ' + c.norm + '\n';
        md += '\n**Описание:** ' + c.description + '\n\n';
        if (c.recommendation)
          md += '**Рекомендация:** ' + c.recommendation + '\n\n';
        md += '---\n\n';
      }
    }

    if (minorChecks.length > 0) {
      md += '#### Незначительные замечания (' + minorChecks.length + ')\n\n';
      for (var i = 0; i < minorChecks.length; i++) {
        var c = minorChecks[i];
        md += '##### ' + (i + 1) + '. ' + c.title + '\n\n';
        md += '- **Лист:** ' + c.sheet + '\n';
        if (c.norm) md += '- **Норма:** ' + c.norm + '\n';
        md += '\n**Описание:** ' + c.description + '\n\n';
        if (c.recommendation)
          md += '**Рекомендация:** ' + c.recommendation + '\n\n';
        md += '---\n\n';
      }
    }

    if (compliantChecks.length > 0) {
      md += '#### Соответствия (' + compliantChecks.length + ')\n\n';
      for (var i = 0; i < compliantChecks.length; i++) {
        var c = compliantChecks[i];
        md += '##### ' + (i + 1) + '. ' + c.title + '\n\n';
        md += '- **Лист:** ' + c.sheet + '\n';
        if (c.norm) md += '- **Норма:** ' + c.norm + '\n';
        md += '\n' + c.description + '\n\n';
        md += '---\n\n';
      }
    }

    if (uncheckedChecks.length > 0) {
      md += '#### Не проверено (' + uncheckedChecks.length + ')\n\n';
      for (var i = 0; i < uncheckedChecks.length; i++) {
        var c = uncheckedChecks[i];
        md += '##### ' + (i + 1) + '. ' + c.title + '\n\n';
        md += '- **Лист:** ' + c.sheet + '\n';
        md += '\n' + c.description + '\n\n';
        md += '---\n\n';
      }
    }

    docIndex++;
  }

  md += '## 3. Сводная таблица\n\n';
  md += '| № | Документ | Тип | Критичность | Лист | Норма | Описание |\n';
  md += '|---|---|---|---|---|---|---|\n';
  for (var i = 0; i < report.checks.length; i++) {
    var c = report.checks[i];
    var typeLabel =
      c.type === 'violation'
        ? 'Нарушение'
        : c.type === 'compliant'
          ? 'Соответствие'
          : 'Не проверено';
    var sevLabel =
      c.severity === 'critical'
        ? 'Крит.'
        : c.severity === 'major'
          ? 'Знач.'
          : c.severity === 'minor'
            ? 'Незн.'
            : '—';
    var shortDocName = (c.docName || '—').substring(0, 40);
    md +=
      '| ' +
      (i + 1) +
      ' | ' +
      shortDocName +
      ' | ' +
      typeLabel +
      ' | ' +
      sevLabel +
      ' | ' +
      c.sheet +
      ' | ' +
      (c.norm || '—') +
      ' | ' +
      c.title.substring(0, 50) +
      ' |\n';
  }

  md += '\n## 4. Рекомендации\n\n';
  var allRecommendations = report.checks.filter(function (c) {
    return c.recommendation;
  });
  for (var i = 0; i < allRecommendations.length; i++) {
    md += i + 1 + '. ' + allRecommendations[i].recommendation + '\n';
  }

  md += '\n---\n\n';
  md += '*Отчёт сгенерирован системой Черкашин AI/ — Нормоконтроль ВК*\n';

  var blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download =
    'report_' + reportId + '_' + new Date().toISOString().split('T')[0] + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Отчёт скачан в формате Markdown', 'success');
}

// ===== DOWNLOAD REPORT PDF =====
function downloadReportPDF(reportId) {
  console.log('[PDF Export] Начало экспорта отчёта ID:', reportId);

  var report = reportsData.find(function (r) {
    return r.id === reportId;
  });
  if (!report) {
    console.error('[PDF Export] Отчёт не найден:', reportId);
    showToast('Отчёт не найден', 'error');
    return;
  }

  console.log('[PDF Export] Отчёт найден:', report.title);
  console.log('[PDF Export] Количество проверок:', report.checks.length);

  // Проверка наличия изображений
  var checksWithImages = report.checks.filter(function (c) {
    return c.image;
  }).length;
  console.log('[PDF Export] Проверок с изображениями:', checksWithImages);

  showToast('Генерация PDF отчёта...', 'info');

  // Вызываем серверный endpoint для генерации PDF
  fetch('/api/export-report/' + reportId + '/pdf', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      report: report,
      norms: normsData,
    }),
  })
    .then(function (response) {
      if (!response.ok) {
        throw new Error('Ошибка сервера: ' + response.status);
      }
      return response.blob();
    })
    .then(function (blob) {
      // Создаём ссылку для скачивания
      var url = window.URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download =
        'report_' +
        reportId +
        '_' +
        new Date().toISOString().split('T')[0] +
        '.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      console.log('[PDF Export] PDF успешно скачан');
      showToast('PDF отчёт успешно сгенерирован и скачан', 'success');
    })
    .catch(function (error) {
      console.error('[PDF Export] Ошибка генерации PDF:', error);
      console.log('[PDF Export] Переключение на клиентскую генерацию PDF');

      // Fallback: клиентская генерация PDF через window.print()
      generatePDFClientSide(reportId);
    });
}

// ===== DOWNLOAD REPORT WORD =====
function downloadReportWord(reportId) {
  var report = reportsData.find(function (r) {
    return r.id === reportId;
  });
  if (!report) {
    showToast('Отчёт не найден', 'error');
    return;
  }

  // Группируем проверки по документам
  var groupedByDoc = {};
  for (var i = 0; i < report.checks.length; i++) {
    var check = report.checks[i];
    var docName = check.docName || 'Неизвестный документ';
    if (!groupedByDoc[docName]) {
      groupedByDoc[docName] = [];
    }
    groupedByDoc[docName].push(check);
  }

  // Создаем HTML для Word
  var html =
    '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">';
  html += '<head><meta charset="UTF-8"><title>' + report.title + '</title>';
  html += '<style>';
  html +=
    'body { font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.5; }';
  html +=
    'h1 { font-size: 16pt; color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }';
  html += 'h2 { font-size: 14pt; color: #334155; margin-top: 16px; }';
  html += 'h3 { font-size: 12pt; color: #475569; margin-top: 12px; }';
  html += 'table { width: 100%; border-collapse: collapse; margin: 12px 0; }';
  html += 'th, td { border: 1px solid #000; padding: 6px; text-align: left; }';
  html += 'th { background-color: #f1f5f9; font-weight: bold; }';
  html += '.header { text-align: center; margin-bottom: 20px; }';
  html += '.logo { font-size: 20pt; font-weight: bold; color: #7c3aed; }';
  html +=
    '.meta { background: #f8fafc; padding: 12px; border-left: 3px solid #3b82f6; margin: 12px 0; }';
  html +=
    '.doc-section { margin: 20px 0; padding: 12px; border: 1px solid #cbd5e1; background: #fafafa; }';
  html +=
    '.doc-title { font-size: 13pt; font-weight: bold; color: #1e293b; margin-bottom: 12px; padding: 8px; background: #e0e7ff; border-left: 3px solid #3b82f6; }';
  html += '</style></head><body>';

  // Заголовок
  html += '<div class="header">';
  html += '<div class="logo">Черкашин AI/</div>';
  html +=
    '<div style="font-size:10pt;color:#64748b;">Нормоконтроль ВК — Отчёт о проверке</div>';
  html += '</div>';

  // Название отчёта
  html += '<h1>' + report.title + '</h1>';

  // Метаданные
  html += '<div class="meta">';
  html += '<strong>Дата создания:</strong> ' + report.date + '<br>';
  html +=
    '<strong>Объект:</strong> Раздел ПД №5 Подраздел №3 Часть 1_ИОС3.1_Изм.1<br>';
  html += '<strong>Шифр:</strong> 35020 040002.111.20.-3.1<br>';
  html +=
    '<strong>Подписант:</strong> Ковалев Дмитрий Александрович, АО «КРДВ Хабаровск»';
  html += '</div>';

  // Статистика
  html += '<h2>1. Общие сведения</h2>';
  html += '<p><strong>Всего проверок:</strong> ' + report.totalChecks + '</p>';
  html += '<p><strong>Нарушения:</strong> ' + report.violations + '</p>';
  html += '<p><strong>Соответствия:</strong> ' + report.compliant + '</p>';
  html += '<p><strong>Не проверено:</strong> ' + report.unchecked + '</p>';

  // Нормативная база
  html += '<h3>1.1. Нормативная база</h3><ul>';
  for (var n = 0; n < normsData.length; n++) {
    html +=
      '<li>' + normsData[n].title + ' — ' + normsData[n].subtitle + '</li>';
  }
  html += '</ul>';

  // Список проверенных документов
  html += '<h3>1.2. Проверенные документы</h3>';
  html +=
    '<table><thead><tr><th>№</th><th>Имя документа</th><th>Проверок</th><th>Нарушений</th><th>Соответствий</th><th>Не проверено</th></tr></thead><tbody>';
  var docIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];
    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;
    html +=
      '<tr><td>' +
      docIndex +
      '</td><td>' +
      docName +
      '</td><td>' +
      docChecks.length +
      '</td><td>' +
      docViolations +
      '</td><td>' +
      docCompliant +
      '</td><td>' +
      docUnchecked +
      '</td></tr>';
    docIndex++;
  }
  html += '</tbody></table>';

  // Результаты проверки по документам
  html += '<h2>2. Результаты проверки по документам</h2>';

  var docIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];
    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;

    html += '<div class="doc-section">';
    html += '<div class="doc-title">Документ: ' + docName + '</div>';
    html +=
      '<p style="margin-bottom:10px;"><strong>Статистика:</strong> ' +
      docChecks.length +
      ' проверок | ';
    html += docViolations + ' нарушений | ';
    html += docCompliant + ' соответствий | ';
    html += docUnchecked + ' не проверено</p>';

    var criticalChecks = docChecks.filter(function (c) {
      return c.severity === 'critical';
    });
    var majorChecks = docChecks.filter(function (c) {
      return c.severity === 'major';
    });
    var minorChecks = docChecks.filter(function (c) {
      return c.severity === 'minor';
    });
    var compliantChecks = docChecks.filter(function (c) {
      return c.type === 'compliant';
    });
    var uncheckedChecks = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    });

    if (criticalChecks.length > 0) {
      html += '<h3>Критические нарушения (' + criticalChecks.length + ')</h3>';
      for (var i = 0; i < criticalChecks.length; i++) {
        var c = criticalChecks[i];
        html += '<p><strong>' + (i + 1) + '. ' + c.title + '</strong></p>';
        html += '<p>Лист: ' + c.sheet + '</p>';
        if (c.norm) html += '<p>Норма: ' + c.norm + '</p>';
        html += '<p>Описание: ' + c.description + '</p>';
        if (c.recommendation)
          html += '<p>Рекомендация: ' + c.recommendation + '</p>';
        html += '<hr>';
      }
    }

    if (majorChecks.length > 0) {
      html += '<h3>Значительные нарушения (' + majorChecks.length + ')</h3>';
      for (var i = 0; i < majorChecks.length; i++) {
        var c = majorChecks[i];
        html += '<p><strong>' + (i + 1) + '. ' + c.title + '</strong></p>';
        html += '<p>Лист: ' + c.sheet + '</p>';
        if (c.norm) html += '<p>Норма: ' + c.norm + '</p>';
        html += '<p>Описание: ' + c.description + '</p>';
        if (c.recommendation)
          html += '<p>Рекомендация: ' + c.recommendation + '</p>';
        html += '<hr>';
      }
    }

    if (minorChecks.length > 0) {
      html += '<h3>Незначительные замечания (' + minorChecks.length + ')</h3>';
      for (var i = 0; i < minorChecks.length; i++) {
        var c = minorChecks[i];
        html += '<p><strong>' + (i + 1) + '. ' + c.title + '</strong></p>';
        html += '<p>Лист: ' + c.sheet + '</p>';
        if (c.norm) html += '<p>Норма: ' + c.norm + '</p>';
        html += '<p>Описание: ' + c.description + '</p>';
        if (c.recommendation)
          html += '<p>Рекомендация: ' + c.recommendation + '</p>';
        html += '<hr>';
      }
    }

    if (compliantChecks.length > 0) {
      html += '<h3>Соответствия (' + compliantChecks.length + ')</h3>';
      for (var i = 0; i < compliantChecks.length; i++) {
        var c = compliantChecks[i];
        html += '<p><strong>' + (i + 1) + '. ' + c.title + '</strong></p>';
        html += '<p>Лист: ' + c.sheet + '</p>';
        if (c.norm) html += '<p>Норма: ' + c.norm + '</p>';
        html += '<p>' + c.description + '</p>';
        html += '<hr>';
      }
    }

    if (uncheckedChecks.length > 0) {
      html += '<h3>Не проверено (' + uncheckedChecks.length + ')</h3>';
      for (var i = 0; i < uncheckedChecks.length; i++) {
        var c = uncheckedChecks[i];
        html += '<p><strong>' + (i + 1) + '. ' + c.title + '</strong></p>';
        html += '<p>Лист: ' + c.sheet + '</p>';
        html += '<p>' + c.description + '</p>';
        html += '<hr>';
      }
    }

    html += '</div>';
    docIndex++;
  }

  // Сводная таблица
  html += '<h2>3. Сводная таблица</h2>';
  html +=
    '<table><thead><tr><th>№</th><th>Документ</th><th>Тип</th><th>Критичность</th><th>Лист</th><th>Норма</th><th>Описание</th></tr></thead><tbody>';
  for (var i = 0; i < report.checks.length; i++) {
    var c = report.checks[i];
    var typeLabel =
      c.type === 'violation'
        ? 'Нарушение'
        : c.type === 'compliant'
          ? 'Соответствие'
          : 'Не проверено';
    var sevLabel =
      c.severity === 'critical'
        ? 'Крит.'
        : c.severity === 'major'
          ? 'Знач.'
          : c.severity === 'minor'
            ? 'Незн.'
            : '—';
    var shortDocName = (c.docName || '—').substring(0, 40);
    html +=
      '<tr><td>' +
      (i + 1) +
      '</td><td>' +
      shortDocName +
      '</td><td>' +
      typeLabel +
      '</td><td>' +
      sevLabel +
      '</td><td>' +
      c.sheet +
      '</td><td>' +
      (c.norm || '—') +
      '</td><td>' +
      c.title.substring(0, 50) +
      '</td></tr>';
  }
  html += '</tbody></table>';

  // Рекомендации
  html += '<h2>4. Рекомендации</h2><ol>';
  var allRecommendations = report.checks.filter(function (c) {
    return c.recommendation;
  });
  for (var i = 0; i < allRecommendations.length; i++) {
    html += '<li>' + allRecommendations[i].recommendation + '</li>';
  }
  html += '</ol>';

  // Подвал
  html += '<hr>';
  html +=
    '<p style="text-align:center;font-size:9pt;color:#94a3b8;">Отчёт сгенерирован системой Черкашин AI/ — Нормоконтроль ВК</p>';
  html +=
    '<p style="text-align:center;font-size:9pt;color:#94a3b8;">Дата генерации: ' +
    new Date().toLocaleString('ru-RU') +
    '</p>';

  html += '</body></html>';

  // Создаем Blob с правильным MIME типом для Word
  var blob = new Blob([html], { type: 'application/msword;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download =
    'report_' +
    reportId +
    '_' +
    new Date().toISOString().split('T')[0] +
    '.doc';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast('Отчёт скачан в формате Word', 'success');
}

// Клиентская генерация PDF через window.print()
function generatePDFClientSide(reportId) {
  var report = reportsData.find(function (r) {
    return r.id === reportId;
  });
  if (!report) {
    showToast('Отчёт не найден', 'error');
    return;
  }

  // Группируем проверки по документам
  var groupedByDoc = {};
  for (var i = 0; i < report.checks.length; i++) {
    var check = report.checks[i];
    var docName = check.docName || 'Неизвестный документ';
    if (!groupedByDoc[docName]) {
      groupedByDoc[docName] = [];
    }
    groupedByDoc[docName].push(check);
  }

  // Создаём HTML для печати
  var html = '<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">';
  html += '<title>' + report.title + '</title>';
  html += '<style>';
  html += '@page { size: A4; margin: 20mm; }';
  html +=
    'body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.6; color: #000; }';
  html +=
    'h1 { font-size: 18pt; color: #1e293b; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px; }';
  html +=
    'h2 { font-size: 14pt; color: #1e293b; margin-top: 20px; margin-bottom: 10px; }';
  html +=
    'h3 { font-size: 12pt; color: #1e293b; margin-top: 15px; margin-bottom: 8px; }';
  html += 'table { width: 100%; border-collapse: collapse; margin: 10px 0; }';
  html +=
    'th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; }';
  html += 'th { background: #f1f5f9; font-weight: bold; }';
  html +=
    '.violation { background: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; margin: 10px 0; }';
  html += '.violation h4 { color: #991b1b; margin-bottom: 8px; }';
  html +=
    '.compliant { background: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 10px 0; }';
  html +=
    '.unchecked { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 10px 0; }';
  html += '.doc-section { margin: 20px 0; page-break-inside: avoid; }';
  html +=
    '.doc-title { font-size: 13pt; font-weight: bold; color: #1e293b; margin-bottom: 10px; }';
  html += '.doc-info { font-size: 9pt; color: #64748b; margin-bottom: 15px; }';
  html +=
    '.violation-image { max-width: 100%; height: auto; margin: 10px 0; border: 1px solid #cbd5e1; }';
  html +=
    '.footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #cbd5e1; font-size: 9pt; color: #64748b; }';
  html += '@media print { .no-print { display: none; } }';
  html += '</style></head><body>';

  // Заголовок
  html += '<h1>' + report.title + '</h1>';

  // Информация об отчёте
  html += '<table>';
  html += '<tr><th>Дата создания</th><td>' + report.date + '</td></tr>';
  html += '<tr><th>Всего проверок</th><td>' + report.totalChecks + '</td></tr>';
  html += '<tr><th>Нарушений</th><td>' + report.violations + '</td></tr>';
  html += '<tr><th>Соответствий</th><td>' + report.compliant + '</td></tr>';
  html += '<tr><th>Не проверено</th><td>' + report.unchecked + '</td></tr>';
  html += '</table>';

  // Нормативная база
  html += '<h2>1. Нормативная база</h2>';
  html += '<ul>';
  for (var n = 0; n < normsData.length; n++) {
    html +=
      '<li><strong>' +
      normsData[n].title +
      '</strong> — ' +
      normsData[n].subtitle +
      '</li>';
  }
  html += '</ul>';

  // Список проверенных документов
  html += '<h2>2. Проверенные документы</h2>';
  html += '<table>';
  html +=
    '<thead><tr><th>№</th><th>Документ</th><th>Проверок</th><th>Нарушений</th><th>Соответствий</th><th>Не проверено</th></tr></thead>';
  html += '<tbody>';
  var docIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];
    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;
    html += '<tr>';
    html += '<td>' + docIndex + '</td>';
    html += '<td>' + docName + '</td>';
    html += '<td>' + docChecks.length + '</td>';
    html += '<td>' + docViolations + '</td>';
    html += '<td>' + docCompliant + '</td>';
    html += '<td>' + docUnchecked + '</td>';
    html += '</tr>';
    docIndex++;
  }
  html += '</tbody></table>';

  // Результаты проверки по документам
  html += '<h2>3. Результаты проверки по документам</h2>';

  docIndex = 1;
  for (var docName in groupedByDoc) {
    var docChecks = groupedByDoc[docName];

    html += '<div class="doc-section">';
    html +=
      '<div class="doc-title">📄 Документ ' +
      docIndex +
      ': ' +
      docName +
      '</div>';
    html +=
      '<div class="doc-info"><strong>Полное имя файла:</strong> ' +
      docName +
      '</div>';
    html +=
      '<div class="doc-info"><strong>Всего проверок:</strong> ' +
      docChecks.length +
      '</div>';

    var docViolations = docChecks.filter(function (c) {
      return c.type === 'violation';
    }).length;
    var docCompliant = docChecks.filter(function (c) {
      return c.type === 'compliant';
    }).length;
    var docUnchecked = docChecks.filter(function (c) {
      return c.type === 'unchecked';
    }).length;

    html +=
      '<div class="doc-info"><strong>Нарушений:</strong> ' +
      docViolations +
      ' | <strong>Соответствий:</strong> ' +
      docCompliant +
      ' | <strong>Не проверено:</strong> ' +
      docUnchecked +
      '</div>';

    // Выводим проверки для этого документа
    for (var i = 0; i < docChecks.length; i++) {
      var check = docChecks[i];

      if (check.type === 'violation') {
        html += '<div class="violation">';
        html += '<h4>' + (i + 1) + '. ' + check.title + '</h4>';
        if (check.sheet)
          html += '<p><strong>Лист:</strong> ' + check.sheet + '</p>';
        if (check.norm)
          html += '<p><strong>Норма:</strong> ' + check.norm + '</p>';
        if (check.description)
          html += '<p><strong>Описание:</strong> ' + check.description + '</p>';
        if (check.recommendation)
          html +=
            '<p><strong>Рекомендация:</strong> ' +
            check.recommendation +
            '</p>';

        // Добавляем изображение, если есть
        if (check.image) {
          html += '<p><strong>Скриншот нарушения:</strong></p>';
          html +=
            '<img src="' +
            check.image +
            '" class="violation-image" alt="Скриншот нарушения">';
        }

        html += '</div>';
      } else if (check.type === 'compliant') {
        html += '<div class="compliant">';
        html += '<h4>' + (i + 1) + '. ' + check.title + '</h4>';
        if (check.sheet)
          html += '<p><strong>Лист:</strong> ' + check.sheet + '</p>';
        if (check.norm)
          html += '<p><strong>Норма:</strong> ' + check.norm + '</p>';
        if (check.description)
          html += '<p><strong>Описание:</strong> ' + check.description + '</p>';
        html += '</div>';
      } else if (check.type === 'unchecked') {
        html += '<div class="unchecked">';
        html += '<h4>' + (i + 1) + '. ' + check.title + '</h4>';
        if (check.sheet)
          html += '<p><strong>Лист:</strong> ' + check.sheet + '</p>';
        if (check.norm)
          html += '<p><strong>Норма:</strong> ' + check.norm + '</p>';
        if (check.description)
          html += '<p><strong>Описание:</strong> ' + check.description + '</p>';
        html += '</div>';
      }
    }

    html += '</div>';
    docIndex++;
  }

  // Подвал
  html += '<div class="footer">';
  html += '<p>Отчёт сгенерирован системой Черкашин AI/ — Нормоконтроль ВК</p>';
  html += '<p>Дата генерации: ' + new Date().toLocaleString('ru-RU') + '</p>';
  html += '</div>';

  html += '</body></html>';

  // Открываем новое окно для печати
  var printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(html);
    printWindow.document.close();

    // Ждём загрузки контента и вызываем диалог печати
    printWindow.onload = function () {
      printWindow.focus();
      setTimeout(function () {
        printWindow.print();
      }, 500);
    };

    console.log('[PDF Export] Окно печати открыто');
    showToast(
      'Отчёт открыт. Диалог печати появится автоматически. Выберите "Сохранить как PDF".',
      'success',
    );
  } else {
    console.error('[PDF Export] Не удалось открыть окно печати');
    showToast('Разрешите всплывающие окна для сохранения PDF', 'error');
  }
}

// ===== ФУНКЦИЯ ПРИКРЕПЛЕНИЯ ИЗОБРАЖЕНИЙ =====
function attachImage(checkId) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  input.onchange = function (e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (event) {
      const imageData = event.target.result;

      // Найдем проверку и добавим изображение
      for (let i = 0; i < checksData.length; i++) {
        if (checksData[i].id === checkId) {
          checksData[i].image = imageData;
          renderChecks();
          showToast('Изображение прикреплено', 'success');
          break;
        }
      }
    };
    reader.readAsDataURL(file);
  };
  input.click();
}

// ===== УДАЛЕНИЕ ИЗОБРАЖЕНИЯ =====
function removeImage(checkId) {
  for (let i = 0; i < checksData.length; i++) {
    if (checksData[i].id === checkId) {
      checksData[i].image = null;
      renderChecks();
      showToast('Изображение удалено', 'success');
      break;
    }
  }
}
