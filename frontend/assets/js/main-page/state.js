// ============================================================
// VKS EXPERT AI
// state.js
// Единое состояние приложения
// ============================================================

// ============================================================
// CURRENT APPLICATION STATE
// ============================================================

// Текущий раздел приложения
var currentSection = 'dashboard';

// Фильтры проверок
var currentFilter = 'all';
var currentSeverityFilter = '';
var currentSectionFilter = 'all';

// ============================================================
// DOCUMENTS
// ============================================================

// Следующий ID документа
var nextDocId = 1;

// Загруженные проектные документы
var docsData = [
  {
    id: nextDocId++,
    name: 'ОВ.pdf',
    size: '2.4 МБ',
    date: '2026-05-21',
    status: 'checked',
    sheets: 24,
    section: 'ОВ',
    checked: false,
  },
  {
    id: nextDocId++,
    name: 'ВК.pdf',
    size: '1.8 МБ',
    date: '2026-05-21',
    status: 'checked',
    sheets: 18,
    section: 'ВК',
    checked: false,
  },
  {
    id: nextDocId++,
    name: 'ЭОМ.pdf',
    size: '3.1 МБ',
    date: '2026-05-20',
    status: 'new',
    sheets: 32,
    section: 'ЭОМ',
    checked: false,
  },
];

// ============================================================
// NORMATIVE DOCUMENTS
// ============================================================

// Следующий ID нормативного документа
var nextNormId = 1;

// Нормативная база
var normsData = [
  {
    id: nextNormId++,
    title: 'СП 30.13330.2020',
    subtitle: 'Внутренний водопровод и канализация зданий',
    date: '2026-05-20',
    points: 486,
    status: 'indexed',
    progress: 100,
    sections: ['ВК'],
    fileName: 'СП 30.13330.2020.pdf',
  },
  {
    id: nextNormId++,
    title: 'СП 60.13330.2020',
    subtitle: 'Отопление, вентиляция и кондиционирование воздуха',
    date: '2026-05-18',
    points: 712,
    status: 'indexed',
    progress: 100,
    sections: ['ОВ'],
    fileName: 'СП 60.13330.2020.pdf',
  },
  {
    id: nextNormId++,
    title: 'СП 256.1325800.2016',
    subtitle: 'Электроустановки жилых и общественных зданий',
    date: '2026-05-15',
    points: 634,
    status: 'pending',
    progress: 0,
    sections: ['ЭОМ'],
    fileName: 'СП 256.1325800.2016.pdf',
  },
];

// ============================================================
// CHECK RESULTS
// ============================================================

// Результаты проверок проектной документации
var checksData = [
  {
    id: 1,
    type: 'violation',
    docId: 2,
    docName: 'ВК.pdf',
    title:
      'Диаметр участка внутреннего водопровода не соответствует расчетному значению',
    description:
      'В проектной документации указан диаметр участка трубопровода, не соответствующий расчетному расходу воды.',
    recommendation:
      'Проверить гидравлический расчет и привести диаметр участка трубопровода в соответствие с расчетными параметрами.',
    sheet: 'ВК-3',
    norm: 'СП 30.13330.2020',
    severity: 'major',
    image: null,
  },
  {
    id: 2,
    type: 'violation',
    docId: 2,
    docName: 'ВК.pdf',
    title: 'Отсутствует необходимая арматура на вводе внутреннего водопровода',
    description:
      'На схеме внутреннего водопровода отсутствует обозначение необходимой запорной арматуры.',
    recommendation:
      'Проверить схему ввода и предусмотреть необходимую запорную арматуру.',
    sheet: 'ВК-2',
    norm: 'СП 30.13330.2020',
    severity: 'critical',
    image: null,
  },
  {
    id: 3,
    type: 'compliant',
    docId: 2,
    docName: 'ВК.pdf',
    title: 'Система внутреннего водопровода соответствует требованиям',
    description:
      'Проверяемые параметры системы соответствуют требованиям применяемого нормативного документа.',
    recommendation: '',
    sheet: 'ВК-4',
    norm: 'СП 30.13330.2020',
    severity: 'minor',
    image: null,
  },
  {
    id: 4,
    type: 'violation',
    docId: 1,
    docName: 'ОВ.pdf',
    title: 'Не обеспечено требуемое размещение отопительного оборудования',
    description:
      'Размещение оборудования требует дополнительной проверки на соответствие проектным и нормативным требованиям.',
    recommendation:
      'Проверить размещение оборудования и соответствующие нормативные ограничения.',
    sheet: 'ОВ-5',
    norm: 'СП 60.13330.2020',
    severity: 'major',
    image: null,
  },
  {
    id: 5,
    type: 'compliant',
    docId: 1,
    docName: 'ОВ.pdf',
    title: 'Расчетные параметры отопительной системы соответствуют требованиям',
    description:
      'Проверенные расчетные параметры соответствуют установленным требованиям.',
    recommendation: '',
    sheet: 'ОВ-3',
    norm: 'СП 60.13330.2020',
    severity: 'minor',
    image: null,
  },
  {
    id: 6,
    type: 'unchecked',
    docId: 3,
    docName: 'ЭОМ.pdf',
    title: 'Проверка раздела ЭОМ не выполнена',
    description:
      'Документ загружен в систему, но автоматизированная проверка требований еще не выполнялась.',
    recommendation: 'Запустить проверку документа.',
    sheet: 'ЭОМ-1',
    norm: 'СП 256.1325800.2016',
    severity: 'minor',
    image: null,
  },
  {
    id: 7,
    type: 'violation',
    docId: 2,
    docName: 'ВК.pdf',
    title: 'Не указана необходимая информация на схеме системы канализации',
    description:
      'На представленном листе отсутствует часть информации, необходимой для проверки проектного решения.',
    recommendation:
      'Дополнить графическую часть необходимыми обозначениями и параметрами.',
    sheet: 'ВК-7',
    norm: 'СП 30.13330.2020',
    severity: 'minor',
    image: null,
  },
  {
    id: 8,
    type: 'compliant',
    docId: 2,
    docName: 'ВК.pdf',
    title: 'Проверка уклонов трубопроводов выполнена успешно',
    description:
      'Проверенные значения уклонов соответствуют требованиям нормативной документации.',
    recommendation: '',
    sheet: 'ВК-8',
    norm: 'СП 30.13330.2020',
    severity: 'minor',
    image: null,
  },
  {
    id: 9,
    type: 'violation',
    docId: 1,
    docName: 'ОВ.pdf',
    title: 'Не подтверждено соответствие расчетного воздухообмена',
    description:
      'В проектных материалах отсутствует достаточное обоснование принятого значения воздухообмена.',
    recommendation:
      'Проверить расчет воздухообмена и добавить необходимые расчетные обоснования.',
    sheet: 'ОВ-8',
    norm: 'СП 60.13330.2020',
    severity: 'major',
    image: null,
  },
  {
    id: 10,
    type: 'unchecked',
    docId: 3,
    docName: 'ЭОМ.pdf',
    title: 'Требуется проверка электрических нагрузок',
    description:
      'Проверка расчетных электрических нагрузок еще не выполнялась.',
    recommendation: 'Запустить проверку раздела ЭОМ.',
    sheet: 'ЭОМ-4',
    norm: 'СП 256.1325800.2016',
    severity: 'minor',
    image: null,
  },
];

// ============================================================
// REPORTS
// ============================================================

// Последний сформированный отчет
var currentReport = null;

// История отчетов
var reportsData = [];

// ============================================================
// SETTINGS
// ============================================================

var settingsData = {
  // Общие настройки
  autoCheck: true,
  autoIndex: true,

  // AI
  aiModel: 'Qwen3.5-9B',
  temperature: 0.2,

  // Проверка
  checkSections: ['ВК', 'ОВ', 'ЭОМ'],
  includeRecommendations: true,

  // Интерфейс
  compactMode: false,
  showTechnicalDetails: false,

  // Экспорт
  reportFormat: 'pdf',
};

// ============================================================
// UI STATE
// ============================================================

// Состояние индексации нормативной базы
var indexingState = {
  active: false,
  total: 0,
  completed: 0,
  currentNormId: null,
};

// Состояние текущей проверки документов
var checkingState = {
  active: false,
  total: 0,
  completed: 0,
  documentIds: [],
};

// ============================================================
// APPLICATION STATISTICS
// ============================================================

var appStats = {
  totalChecks: 247,
  totalViolations: 38,
  totalCompliant: 156,
  totalUnchecked: 53,
  totalCritical: 7,
};

// ============================================================
// HELPERS FOR STATE
// ============================================================

// Получить документ по ID
function getDocumentById(id) {
  return docsData.find(function (doc) {
    return doc.id === id;
  });
}

// Получить нормативный документ по ID
function getNormById(id) {
  return normsData.find(function (norm) {
    return norm.id === id;
  });
}

// Получить результат проверки по ID
function getCheckById(id) {
  return checksData.find(function (check) {
    return check.id === id;
  });
}

// Получить следующий ID результата проверки
function getNextCheckId() {
  if (checksData.length === 0) {
    return 1;
  }

  return (
    Math.max.apply(
      null,
      checksData.map(function (check) {
        return check.id;
      }),
    ) + 1
  );
}

// ============================================================
// INITIALIZATION
// ============================================================

console.log('[VKS Expert AI] state.js загружен');
console.log(
  '[VKS Expert AI] Документов:',
  docsData.length,
  '| Нормативных документов:',
  normsData.length,
  '| Результатов проверок:',
  checksData.length,
);
