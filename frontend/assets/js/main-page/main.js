// ============================================================
// VKS Expert AI
// main.js v8
// ============================================================
// Главная точка входа приложения.
// ES-модули не публикуют свои функции в window автоматически, поэтому
// навигация реализуется здесь через DOM-события, а совместимость с
// существующими inline onclick сохраняется через window.navigateTo/switchSection.

import './state.js?v=20260901-8';
import './utils.js?v=20260901-8';
import './dashboard.js?v=20260901-8';
import './norms.js?v=20260901-8';
import './documents.js?v=20260901-8';
import './checks.js?v=20260901-8';
import './reports.js?v=20260901-8';
import './settings.js?v=20260901-8';

const SECTION_LABELS = {
  dashboard: 'Dashboard', norms: 'Нормы', docs: 'Документация', checks: 'Проверки', reports: 'Отчёты', settings: 'Настройки',
};

function switchSection(sectionName) {
  const name = String(sectionName || 'dashboard');
  const target = document.getElementById(name + 'Section');
  if (!target) { console.warn('[VKS Expert AI] Раздел не найден:', name); return false; }
  document.querySelectorAll('.section').forEach((section) => section.classList.toggle('active', section === target));
  document.querySelectorAll('.sidebar .nav-item[data-section]').forEach((item) => item.classList.toggle('active', item.dataset.section === name));
  const breadcrumb = document.getElementById('breadcrumbCurrent');
  if (breadcrumb) breadcrumb.textContent = SECTION_LABELS[name] || name;
  window.currentSection = name;
  if (name === 'dashboard' && typeof window.renderDashboard === 'function') window.renderDashboard();
  if (name === 'norms' && typeof window.renderNorms === 'function') window.renderNorms();
  if (name === 'docs' && typeof window.renderDocs === 'function') window.renderDocs();
  if (name === 'checks' && typeof window.renderChecks === 'function') window.renderChecks();
  if (name === 'reports' && typeof window.renderReports === 'function') window.renderReports();
  if (name === 'settings' && typeof window.renderSettings === 'function') window.renderSettings();
  console.log('[VKS Expert AI] Переход в раздел:', name);
  return true;
}
function navigateTo(sectionName) { return switchSection(sectionName); }
function initNavigation() {
  document.querySelectorAll('.sidebar .nav-item[data-section]').forEach((item) => {
    item.addEventListener('click', (event) => { event.preventDefault(); switchSection(item.dataset.section); });
  });
  window.switchSection = switchSection; window.navigateTo = navigateTo; switchSection('dashboard');
}
function installFavicon() {
  const existing = document.querySelector('link[rel="icon"]');
  if (existing) { existing.href = './favicon.svg?v=20260901-3'; return; }
  const link = document.createElement('link'); link.rel = 'icon'; link.type = 'image/svg+xml'; link.href = './favicon.svg?v=20260901-3'; document.head.appendChild(link);
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { initNavigation(); installFavicon(); }, { once: true });
else { initNavigation(); installFavicon(); }
console.log('[VKS Expert AI] Main page modules loaded — main.js v8');
