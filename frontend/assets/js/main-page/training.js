// Project Expert AI — Training / Engineering Knowledge UI
const TRAINING_SECTION_ID = 'trainingSection';

function ensureTrainingStyles(){
  if(document.getElementById('trainingStylesheet')) return;
  const link=document.createElement('link');
  link.id='trainingStylesheet';
  link.rel='stylesheet';
  link.href='./assets/css/main-page/training.css?v=20260909-1';
  document.head.appendChild(link);
}

function ensureTrainingUI(){
  if(!document.body) return false;
  ensureTrainingStyles();

  const sidebarNav=document.querySelector('.sidebar-nav');
  if(sidebarNav && !sidebarNav.querySelector('[data-section="training"]')){
    const sections=sidebarNav.querySelectorAll('.nav-section');
    const target=sections.length ? sections[sections.length-1] : sidebarNav;
    const block=document.createElement('div');
    block.className='nav-section';
    block.innerHTML='<div class="nav-section-title">AI ENGINEER</div><div class="nav-item" data-section="training"><span class="training-nav-icon">◈</span><span>Обучение AI</span></div>';
    sidebarNav.insertBefore(block,target);
  }

  const content=document.querySelector('.content');
  if(content && !document.getElementById(TRAINING_SECTION_ID)){
    const section=document.createElement('section');
    section.className='section';
    section.id=TRAINING_SECTION_ID;
    section.innerHTML=`
      <h1 class="section-title">Обучение AI</h1>
      <p class="section-subtitle">Формирование инженерных знаний, эталонных примеров и наборов для оценки AI Engineer</p>
      <div class="training-overview">
        <div class="training-card"><div class="training-card-label">Эксперименты</div><div class="training-card-value">1</div></div>
        <div class="training-card"><div class="training-card-label">Экспертные кейсы</div><div class="training-card-value">0</div></div>
        <div class="training-card"><div class="training-card-label">Факты</div><div class="training-card-value">0</div></div>
        <div class="training-card"><div class="training-card-label">Нормативные требования</div><div class="training-card-value">0</div></div>
      </div>
      <div class="training-tabs" role="tablist">
        <button class="training-tab active" data-training-tab="overview">Обзор</button>
        <button class="training-tab" data-training-tab="cases">Cases</button>
        <button class="training-tab" data-training-tab="facts">Facts</button>
        <button class="training-tab" data-training-tab="requirements">Requirements</button>
        <button class="training-tab" data-training-tab="checklists">Checklist</button>
        <button class="training-tab" data-training-tab="evaluation">Evaluation</button>
      </div>
      <div id="trainingTabContent"></div>`;
    content.insertBefore(section,document.getElementById('settingsSection')||null);
    section.querySelectorAll('[data-training-tab]').forEach(btn=>btn.addEventListener('click',()=>renderTrainingTab(btn.dataset.trainingTab)));
  }
  return true;
}

function renderTrainingTab(tab='overview'){
  if(!ensureTrainingUI()) return;
  const section=document.getElementById(TRAINING_SECTION_ID);
  const content=document.getElementById('trainingTabContent');
  if(!section||!content) return;
  section.querySelectorAll('.training-tab').forEach(x=>x.classList.toggle('active',x.dataset.trainingTab===tab));
  const empty='<div class="training-empty">Пока нет записей. Это Step 1: структура модуля создана, наполнение Golden Dataset будет следующим этапом.</div>';
  if(tab==='overview'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Experiment 001 — СП 30.13330.2020 + проект ВК</div><span class="training-status">Формирование</span></div><div class="training-panel-body"><div class="training-experiment"><div class="training-experiment-main"><div class="training-experiment-title">Первый Golden Dataset</div><div class="training-experiment-meta">Только нормативная база СП 30.13330.2020 и текущий проект ВК. ТЗ и ТУ будут добавлены позже.</div></div></div></div></div><div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Архитектура данных</div></div><div class="training-panel-body"><div class="training-code">engineering_fact → normative_requirement → checklist → audit_case → evaluation</div></div></div>`;
  } else if(tab==='cases'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Engineering Cases</div><span class="training-status">0 cases</span></div><div class="training-panel-body">${empty}</div></div>`;
  } else if(tab==='facts'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Engineering Facts</div><span class="training-status">0 facts</span></div><div class="training-panel-body">${empty}</div></div>`;
  } else if(tab==='requirements'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Normative Requirements</div><span class="training-status">0 requirements</span></div><div class="training-panel-body">${empty}</div></div>`;
  } else if(tab==='checklists'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Engineering Checklists</div><span class="training-status">0 items</span></div><div class="training-panel-body">${empty}</div></div>`;
  } else if(tab==='evaluation'){
    content.innerHTML=`<div class="training-panel"><div class="training-panel-header"><div class="training-panel-title">Evaluation</div><span class="training-status">Not started</span></div><div class="training-panel-body">${empty}</div></div>`;
  }
}

function renderTraining(){
  ensureTrainingUI();
  renderTrainingTab('overview');
}

window.ensureTrainingUI=ensureTrainingUI;
window.renderTraining=renderTraining;

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',ensureTrainingUI,{once:true}); else ensureTrainingUI();
console.log('[Project Expert AI] training.js loaded — Training UI scaffold enabled');
