// Project Expert AI — runtime state
var currentSection = 'dashboard';
var currentFilter = 'all';
var currentSeverityFilter = '';
var currentSectionFilter = 'all';
var docsData = [];
var normsData = [];
var checksData = [];
var reportsData = [];
var currentReport = null;
var CHECKS_STORAGE_VERSION = 'v3-server-reports';
try {
  if (localStorage.getItem('projectExpertAI.checks.version') === CHECKS_STORAGE_VERSION) {
    var savedChecks = JSON.parse(localStorage.getItem('projectExpertAI.checks') || '[]');
    if (Array.isArray(savedChecks)) checksData = savedChecks;
  } else {
    localStorage.removeItem('projectExpertAI.checks');
    localStorage.setItem('projectExpertAI.checks.version', CHECKS_STORAGE_VERSION);
  }
  var savedReports = JSON.parse(localStorage.getItem('projectExpertAI.reports') || '[]');
  if (Array.isArray(savedReports)) reportsData = savedReports;
} catch (error) { console.warn('[Project Expert AI] Не удалось загрузить локальное состояние:', error); }
var nextDocId = 1;
var nextNormId = 1;
var settingsData = { autoCheck: true, autoIndex: true, aiModel: 'qwen3-vl-4b-instruct', temperature: 0.1, checkSections: ['ВК'], includeRecommendations: true, compactMode: false, showTechnicalDetails: false, reportFormat: 'pdf' };
var indexingState = { active: false, total: 0, completed: 0, currentNormId: null };
var checkingState = { active: false, total: 0, completed: 0, documentIds: [] };
var appStats = { totalChecks: checksData.length, totalViolations: 0, totalCompliant: 0, totalUnchecked: 0, totalCritical: 0 };
window.docsData = docsData;
window.normsData = normsData;
window.checksData = checksData;
window.reportsData = reportsData;
window.currentReport = currentReport;
window.appStats = appStats;
window.settingsData = settingsData;
window.indexingState = indexingState;
window.checkingState = checkingState;
function getDocumentById(id) { return window.docsData.find(function(x){return String(x.id)===String(id);}); }
function getNormById(id) { return window.normsData.find(function(x){return String(x.id)===String(id);}); }
function getCheckById(id) { return window.checksData.find(function(x){return String(x.id)===String(id);}); }
function getNextCheckId() { return window.checksData.length ? Math.max.apply(null, window.checksData.map(function(x){return Number(x.id)||0;}))+1 : 1; }
console.log('[Project Expert AI] state.js загружен — серверные результаты проверок');
