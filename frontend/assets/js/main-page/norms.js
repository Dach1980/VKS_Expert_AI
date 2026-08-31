// ============================================================
// Project Expert AI — NORMS
// Реальная интеграция Registry / Storage / processing pipeline.
// ============================================================

const NORMS_API_BASE = 'http://127.0.0.1:8000/api/norms';
var normsPollTimers = {};
if (!Array.isArray(window.normsData)) window.normsData = [];
function getNormsData() { return window.normsData; }
function setNormsData(value) { window.normsData = Array.isArray(value) ? value : []; }
function normProgress(norm) { var p=norm&&norm.processing?norm.processing:{}; if(p.vector_index&&p.vector_metadata)return 100; if(p.chunks)return 75; if(p.structured)return 60; if(p.parsed)return 40; if(p.uploaded)return 20; return 0; }
function escapeHtmlSafe(value) { return String(value==null?'':value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#039;'); }
function showNormToast(message,type) { if(typeof window.showToast==='function'){window.showToast(message,type||'info');return;} console.log('[Project Expert AI][Norms]',message); }
function getNormByIdLocal(id) { return getNormsData().find(function(norm){return String(norm.id)===String(id);}); }

function normVersionLabel(version) {
  var type=String(version.version_type||'edition');
  if(type==='base') return 'Без изменений (базовая версия)';
  if(type==='change' || type==='amendment') return 'С изменениями';
  return 'Редакция';
}
function toggleNormVersions(id) {
  var panel=document.getElementById('normVersions-'+id);
  if(!panel)return;
  panel.style.display=panel.style.display==='none'?'block':'none';
}
function renderNormVersions(norm) {
  var versions=Array.isArray(norm.versions)?norm.versions:[];
  if(!versions.length)return '';
  var html='<div id="normVersions-'+escapeHtmlSafe(norm.id)+'" style="display:none;margin-top:12px;padding:12px 14px;border-top:1px solid var(--border-color);">';
  html+='<div style="font-size:13px;font-weight:600;margin-bottom:8px;">Загруженные версии</div>';
  versions.slice().sort(function(a,b){return String(b.effective_from||'').localeCompare(String(a.effective_from||''));}).forEach(function(v){
    var current=v.status==='current';
    html+='<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--border-color);font-size:12px;">';
    html+='<div><strong>'+escapeHtmlSafe(normVersionLabel(v))+'</strong><div style="color:var(--text-secondary);margin-top:3px;">';
    html+=escapeHtmlSafe(v.effective_from||'Дата не указана')+' · '+escapeHtmlSafe(v.filename||v.version_id||'')+(current?' · действующая':'');
    html+='</div></div>';
    html+='<button class="btn btn-secondary btn-sm" onclick="showNormVersionInfo('+JSON.stringify(norm.id)+','+JSON.stringify(v.version_id)+')">Информация</button></div>';
  });
  return html+'</div>';
}
function renderNorms() {
  var grid=document.getElementById('normsGrid'); if(!grid)return; var norms=getNormsData();
  if(!norms.length){grid.innerHTML='<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет нормативных документов. Перетащите PDF или нажмите на зону загрузки.</div>';return;}
  var html=''; norms.forEach(function(norm){
    var status=norm.status||'pending', progress=norm.progress==null?normProgress(norm):norm.progress, p=norm.processing||{};
    var id=escapeHtmlSafe(JSON.stringify(norm.id));
    var number=norm.number||norm.id;
    var title=norm.title||number;
    var subtitle=norm.subtitle||'';
    html+='<div class="norm-card" style="cursor:pointer;" onclick="toggleNormVersions('+id+')">';
    html+='<div class="norm-card-header"><div style="flex:1;"><div class="norm-card-title">'+escapeHtmlSafe(number)+'</div>';
    html+='<div class="norm-card-subtitle">'+escapeHtmlSafe(title)+(subtitle&&subtitle!==title?' · '+escapeHtmlSafe(subtitle):'')+'</div></div></div>';
    html+='<div class="norm-card-meta"><span>📅 '+escapeHtmlSafe(norm.date||norm.effective_from||'')+'</span><span>📄 '+(p.pages_count||0)+' стр.</span><span>📦 '+((norm.versions||[]).length||1)+' верс.</span></div>';
    if(status==='indexing')html+='<div class="progress-bar"><div class="progress-fill" style="width:'+progress+'%"></div></div><div style="margin-top:8px;font-size:12px;color:var(--accent);">Индексация: '+progress+'%</div>';
    else if(status==='indexed')html+='<div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div><div style="margin-top:8px;font-size:12px;color:var(--text-secondary);">Индексировано: 100%</div>';
    else if(status==='error')html+='<div style="margin-top:12px;"><span class="status-badge error">Ошибка индексации</span></div>';
    else html+='<div style="margin-top:12px;"><span class="status-badge info">Ожидает индексации</span></div>';
    html+='<div class="norm-card-actions" onclick="event.stopPropagation()">';
    if(status!=='indexing'&&status!=='indexed')html+='<button class="btn btn-primary btn-sm" onclick="indexNorm('+id+')">Индексировать</button>';
    html+='<button class="btn btn-secondary btn-sm" onclick="showNormInfo('+id+')">Информация</button><button class="btn btn-secondary btn-sm" onclick="deleteNorm('+id+')">Удалить</button></div>';
    html+=renderNormVersions(norm)+'</div>';
  });
  grid.innerHTML=html;
}

async function loadNorms(){try{var response=await fetch(NORMS_API_BASE);if(!response.ok)throw new Error('HTTP '+response.status);var data=await response.json();setNormsData((data.documents||[]).map(function(item){var p=item.processing||{};return{id:item.document_id,number:item.number,title:item.number||item.document_id,subtitle:item.title||'',date:item.effective_from||'',effective_from:item.effective_from||'',status:p.error?'error':(p.vector_index&&p.vector_metadata?'indexed':'pending'),progress:normProgress(item),sections:[],fileName:item.paths&&item.paths.pdf?item.paths.pdf.split(/[\\/]/).pop():'',version_id:item.version_id,versions:item.versions||[],processing:p,raw:item};}));renderNorms();if(typeof window.updateBadges==='function')window.updateBadges();return getNormsData();}catch(error){console.error('[Project Expert AI] Не удалось загрузить нормы:',error);showNormToast('Не удалось получить нормативную базу: '+error.message,'error');return[];}}
function handleNormDropzoneClick(){var input=document.createElement('input');input.type='file';input.multiple=true;input.accept='.pdf,application/pdf';input.addEventListener('change',function(event){if(event.target.files&&event.target.files.length)handleNormFiles(event.target.files);});input.click();}
function handleNormDragOver(event){event.preventDefault();event.stopPropagation();if(event.currentTarget)event.currentTarget.classList.add('dragover');}
function handleNormDragLeave(event){event.preventDefault();event.stopPropagation();if(event.currentTarget)event.currentTarget.classList.remove('dragover');}
function handleNormDrop(event){event.preventDefault();event.stopPropagation();if(event.currentTarget)event.currentTarget.classList.remove('dragover');if(event.dataTransfer&&event.dataTransfer.files&&event.dataTransfer.files.length)handleNormFiles(event.dataTransfer.files);}
function handleNormFiles(files){var uploads=[];for(var i=0;i<files.length;i+=1)uploads.push(uploadNormFile(files[i]));Promise.all(uploads).then(loadNorms).catch(function(){});}
function uploadNormFile(file){if(!file||!file.name||!file.name.toLowerCase().endsWith('.pdf')){showNormToast('Для нормативной базы допускается только PDF','error');return Promise.reject(new Error('Not a PDF'));}if(file.size>50*1024*1024){showNormToast('Размер PDF не должен превышать 50 МБ','error');return Promise.reject(new Error('File too large'));}var form=new FormData();form.append('file',file,file.name);return fetch(NORMS_API_BASE+'/upload',{method:'POST',body:form}).then(function(response){return response.json().then(function(data){if(!response.ok){var error=new Error(data.detail||('HTTP '+response.status));error.status=response.status;throw error;}return data;});}).then(function(data){showNormToast('Норма загружена: '+(data.number||file.name),'success');return data;}).catch(function(error){console.error('[Project Expert AI] Upload error:',error);if(error.status===409)showNormToast(error.message,'warning');else showNormToast('Ошибка загрузки: '+error.message,'error');throw error;});}
function indexNorm(id){var norm=getNormByIdLocal(id);if(!norm||!norm.version_id){showNormToast('Версия нормативного документа не найдена','error');return;}norm.status='indexing';norm.progress=Math.max(20,norm.progress||0);renderNorms();fetch(NORMS_API_BASE+'/'+encodeURIComponent(norm.id)+'/'+encodeURIComponent(norm.version_id)+'/index',{method:'POST'}).then(function(response){return response.json().then(function(data){if(!response.ok)throw new Error(data.detail||('HTTP '+response.status));return data;});}).then(function(){showNormToast('Полная индексация запущена','info');pollNormStatus(norm.id,norm.version_id);}).catch(function(error){norm.status='pending';renderNorms();showNormToast('Ошибка запуска индексации: '+error.message,'error');});}
function pollNormStatus(documentId,versionId){var key=documentId+':'+versionId;if(normsPollTimers[key])clearInterval(normsPollTimers[key]);normsPollTimers[key]=setInterval(function(){fetch(NORMS_API_BASE+'/'+encodeURIComponent(documentId)+'?version_id='+encodeURIComponent(versionId)).then(function(response){if(!response.ok)throw new Error('HTTP '+response.status);return response.json();}).then(function(data){var norm=getNormByIdLocal(documentId);if(!norm)return;norm.raw=data;norm.processing=data.processing||{};norm.progress=normProgress(data);norm.versions=data.versions||norm.versions||[];if(norm.processing.error){norm.status='error';clearInterval(normsPollTimers[key]);delete normsPollTimers[key];showNormToast('Индексация завершилась с ошибкой','error');}else if(norm.processing.vector_index&&norm.processing.vector_metadata){norm.status='indexed';norm.progress=100;clearInterval(normsPollTimers[key]);delete normsPollTimers[key];showNormToast('Индексация завершена: '+norm.number,'success');}else norm.status='indexing';renderNorms();}).catch(function(error){console.warn('[Project Expert AI] Status polling error:',error);});},3000);}
function indexAllNorms(){var pending=getNormsData().filter(function(norm){return norm.status!=='indexed'&&norm.status!=='indexing';});if(!pending.length){showNormToast('Все документы уже индексированы','info');return;}pending.forEach(function(norm){indexNorm(norm.id);});}
function showNormInfo(id){var norm=getNormByIdLocal(id);if(!norm)return;var p=norm.processing||{};alert('Документ: '+(norm.number||'')+'\nНазвание: '+(norm.subtitle||norm.title||'')+'\nВерсия: '+(norm.version_id||'')+'\nСтраниц: '+(p.pages_count||0)+'\nСтатус: '+(norm.status||'pending'));}
function showNormVersionInfo(documentId,versionId){var norm=getNormByIdLocal(documentId);if(!norm)return;var version=(norm.versions||[]).find(function(v){return String(v.version_id)===String(versionId);});if(!version)return;alert('Документ: '+(norm.number||'')+'\nВерсия: '+normVersionLabel(version)+'\nДата: '+(version.effective_from||'не указана')+'\nФайл: '+(version.filename||version.version_id||'' )+'\nСтатус: '+(version.status||''));}
async function deleteNorm(id){var norm=getNormByIdLocal(id);if(!norm||!norm.version_id){showNormToast('Версия нормативного документа не найдена','error');return;}var label=norm.number||norm.title||id;if(!window.confirm('Удалить нормативный документ/текущую версию «'+label+'»?\n\nБудут удалены PDF, обработанные файлы и индекс.'))return;var key=id+':'+norm.version_id;if(normsPollTimers[key]){clearInterval(normsPollTimers[key]);delete normsPollTimers[key];}try{var response=await fetch(NORMS_API_BASE+'/'+encodeURIComponent(id)+'?version_id='+encodeURIComponent(norm.version_id),{method:'DELETE'});var data=await response.json();if(!response.ok)throw new Error(data.detail||('HTTP '+response.status));showNormToast('Нормативный документ удалён','success');await loadNorms();}catch(error){console.error('[Project Expert AI] Delete error:',error);showNormToast('Ошибка удаления: '+error.message,'error');}}
window.renderNorms=renderNorms;window.loadNorms=loadNorms;window.handleNormDropzoneClick=handleNormDropzoneClick;window.handleNormDragOver=handleNormDragOver;window.handleNormDragLeave=handleNormDragLeave;window.handleNormDrop=handleNormDrop;window.handleNormFiles=handleNormFiles;window.uploadNormFile=uploadNormFile;window.indexNorm=indexNorm;window.pollNormStatus=pollNormStatus;window.indexAllNorms=indexAllNorms;window.showNormInfo=showNormInfo;window.showNormVersionInfo=showNormVersionInfo;window.toggleNormVersions=toggleNormVersions;window.deleteNorm=deleteNorm;
window.handleDropzoneClick=function(type){if(type==='norms')return handleNormDropzoneClick();if(type==='docs'&&typeof window.handleDocsDropzoneClick==='function')return window.handleDocsDropzoneClick();showNormToast('Модуль «Документация» ещё не инициализирован.','error');};
window.handleDragOver=function(event){var id=event&&event.currentTarget&&event.currentTarget.id;if(id==='normsDropzone')return handleNormDragOver(event);if(id==='docsDropzone'&&typeof window.handleDocDragOver==='function')return window.handleDocDragOver(event);};
window.handleDragLeave=function(event){var id=event&&event.currentTarget&&event.currentTarget.id;if(id==='normsDropzone')return handleNormDragLeave(event);if(id==='docsDropzone'&&typeof window.handleDocDragLeave==='function')return window.handleDocDragLeave(event);};
window.handleDrop=function(event,type){if(type==='norms')return handleNormDrop(event);if(type==='docs'&&typeof window.handleDocDrop==='function')return window.handleDocDrop(event);};
window.handleFiles=function(files,type){if(type==='norms')return handleNormFiles(files);if(type==='docs'&&typeof window.handleDocFiles==='function')return window.handleDocFiles(files);};
console.log('[Project Expert AI] norms.js loaded');
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){loadNorms();},{once:true});else loadNorms();