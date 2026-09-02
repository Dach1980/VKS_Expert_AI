// Project Expert AI — expert checking profile selector
const SKILLS_API_BASE='http://127.0.0.1:8000/api/skills';
const CHECKS_API_BASE_SKILLS='http://127.0.0.1:8000/api/checks';
let selectedSkillId=localStorage.getItem('projectExpertAI.skillId')||'vk_wastewater';
let skillsData=[];
function skillsEscape(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;')}
function selectedSkill(){return skillsData.find(x=>x.id===selectedSkillId)||skillsData[0]||null}
function renderSkillSelector(){
  const section=document.getElementById('docsSection');if(!section)return;
  let box=document.getElementById('expertSkillSelector');
  if(!box){box=document.createElement('div');box.id='expertSkillSelector';box.style.cssText='margin:0 0 20px;padding:18px;border:1px solid var(--border-color);border-radius:14px;background:var(--card-bg)';const subtitle=section.querySelector('.section-subtitle');(subtitle||section.firstChild).after(box)}
  const skill=selectedSkill();
  if(!skill){box.innerHTML='<strong>Профиль проверки</strong><div style="margin-top:8px;color:var(--text-secondary)">Профили не загружены.</div>';return}
  box.innerHTML='<div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap"><div><div style="font-weight:700;font-size:16px">Вид нормоконтроля</div><div style="margin-top:5px;color:var(--text-secondary);font-size:13px">Выберите экспертный профиль. Он определяет чек-лист и применимые нормативные документы.</div></div><select id="expertSkillSelect" class="select-input" style="min-width:300px">'+skillsData.map(function(x){return '<option value="'+skillsEscape(x.id)+'" '+(x.id===selectedSkillId?'selected':'')+'>'+skillsEscape(x.name)+' ('+skillsEscape(x.code||'')+')</option>'}).join('')+'</select></div><div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">'+(skill.normative_documents||[]).map(function(x){return '<span class="status-badge success">'+skillsEscape(x)+'</span>'}).join('')+'</div><div style="margin-top:12px;color:var(--text-secondary);font-size:13px">Чек-лист: '+(skill.checks||[]).length+' групп проверки</div>';
  const select=document.getElementById('expertSkillSelect');if(select)select.onchange=function(){selectedSkillId=this.value;localStorage.setItem('projectExpertAI.skillId',selectedSkillId);renderSkillSelector()};
}
async function loadSkills(){try{const r=await fetch(SKILLS_API_BASE);const data=await r.json();if(!r.ok)throw Error(data.detail||('HTTP '+r.status));skillsData=data.skills||[];if(!skillsData.some(x=>x.id===selectedSkillId)&&skillsData.length)selectedSkillId=skillsData[0].id;localStorage.setItem('projectExpertAI.skillId',selectedSkillId);renderSkillSelector()}catch(e){console.warn('[Project Expert AI][Skills] Load error:',e);renderSkillSelector()}}
function getSelectedSkillId(){return selectedSkillId}
async function runSkillCheck(id){
  if(!id)return null;
  if(typeof window.ensureCheckProgressUI==='function')window.ensureCheckProgressUI();
  if(typeof window.documentsToast==='function')window.documentsToast('Проверка запущена по профилю «'+((selectedSkill()||{}).name||selectedSkillId)+'».','info');
  try{
    const r=await fetch(CHECKS_API_BASE_SKILLS+'/'+encodeURIComponent(id)+'?skill_id='+encodeURIComponent(selectedSkillId),{method:'POST'});const data=await r.json();
    if(!r.ok){const err=Error(data.detail||('HTTP '+r.status));err.status=r.status;throw err}
    if(typeof window.updateCheckProgress==='function')window.updateCheckProgress(data);
    if(typeof window.pollCheckJob==='function'&&data.job_id)window.pollCheckJob(data.job_id);return data;
  }catch(e){if(typeof window.closeCheckProgress==='function')window.closeCheckProgress();if(typeof window.documentsToast==='function')window.documentsToast('Ошибка проверки: '+e.message,'error');else console.error(e);return null}
}
function installSkillCheckOverrides(){window.checkDocument=runSkillCheck;window.checkSelectedDocs=function(){const docs=Array.isArray(window.docsData)?window.docsData.filter(x=>x.checked):[];if(!docs.length){if(typeof window.documentsToast==='function')window.documentsToast('Выберите хотя бы один документ.','error');return}return docs.reduce((promise,d)=>promise.then(()=>runSkillCheck(d.id)),Promise.resolve())};renderSkillSelector()}
window.loadSkills=loadSkills;window.getSelectedSkillId=getSelectedSkillId;window.renderSkillSelector=renderSkillSelector;window.runSkillCheck=runSkillCheck;window.installSkillCheckOverrides=installSkillCheckOverrides;
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(function(){installSkillCheckOverrides();loadSkills()},150),{once:true});else setTimeout(function(){installSkillCheckOverrides();loadSkills()},150);
