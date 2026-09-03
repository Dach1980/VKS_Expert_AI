// Project Expert AI — main entry point and live counters
import './state.js?v=20260902-3';
import './utils.js?v=20260902-3';
import './dashboard.js?v=20260902-3';
import './norms.js?v=20260903-2';
import './norms-metadata-fix.js?v=20260903-6';
import './norms-registry-fix.js?v=20260903-4';
import './norms-amendment-label-fix.js?v=20260903-1';
import './documents.js?v=20260902-3';
import './checks.js?v=20260902-3';
import './reports.js?v=20260902-3';
import './settings.js?v=20260902-3';
import './skills.js?v=20260902-1';
const SECTION_LABELS={dashboard:'Dashboard',norms:'Нормы',docs:'Документация',checks:'Замечания',reports:'Отчёты',settings:'Настройки'};
function updateNavCounters(){var norms=Array.isArray(window.normsData)?window.normsData.length:0,docs=Array.isArray(window.docsData)?window.docsData.length:0,checks=Array.isArray(window.checksData)?window.checksData.filter(function(x){return x&&x.type==='violation';}).length:0,reports=Array.isArray(window.reportsData)?window.reportsData.length:0;var n=document.getElementById('normsBadge'),d=document.getElementById('docsBadge'),c=document.getElementById('checksBadge'),r=document.getElementById('reportsBadge');if(n)n.textContent=norms;if(d)d.textContent=docs;if(c)c.textContent=checks;if(r)r.textContent=reports;var nav=document.querySelector('.nav-item[data-section="checks"]');if(nav){var spans=nav.querySelectorAll('span');if(spans.length>1)spans[1].textContent='Замечания';}}
function switchSection(name){name=String(name||'dashboard');var target=document.getElementById(name+'Section');if(!target)return false;document.querySelectorAll('.section').forEach(function(x){x.classList.toggle('active',x===target);});document.querySelectorAll('.sidebar .nav-item[data-section]').forEach(function(x){x.classList.toggle('active',x.dataset.section===name);});var b=document.getElementById('breadcrumbCurrent');if(b)b.textContent=SECTION_LABELS[name]||name;window.currentSection=name;updateNavCounters();if(name==='dashboard'&&window.renderDashboard)window.renderDashboard();if(name==='norms'&&window.renderNorms)window.renderNorms();if(name==='docs'&&window.renderDocs)window.renderDocs();if(name==='docs'&&window.renderSkillSelector)window.renderSkillSelector();if(name==='checks'&&window.renderChecks)window.renderChecks();if(name==='reports'&&window.renderReports)window.renderReports();if(name==='settings'&&window.renderSettings)window.renderSettings();return true;}
function navigateTo(name){return switchSection(name)}
window.updateNavCounters=updateNavCounters;window.switchSection=switchSection;window.navigateTo=navigateTo;
function init(){document.querySelectorAll('.sidebar .nav-item[data-section]').forEach(function(item){item.addEventListener('click',function(e){e.preventDefault();switchSection(item.dataset.section);});});switchSection('dashboard');setTimeout(function(){if(window.loadDocs)window.loadDocs();if(window.loadNorms)window.loadNorms();if(window.loadReports)window.loadReports();if(window.loadSkills)window.loadSkills();if(window.installSkillCheckOverrides)window.installSkillCheckOverrides();updateNavCounters();},100);setInterval(function(){updateNavCounters();if(window.loadReports)window.loadReports();},5000)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
console.log('[Project Expert AI] main.js loaded — skill-driven checking enabled');