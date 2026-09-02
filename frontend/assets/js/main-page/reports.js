// Project Expert AI — persisted norm-control reports
var REPORTS_API = 'http://127.0.0.1:8000/api/reports';
function reportDate(value){ var d=new Date(value||''); return isNaN(d.getTime()) ? 'Дата не указана' : d.toLocaleString('ru-RU'); }
function reportTitle(report){ return 'Нормоконтроль — ' + String(report.document_name || 'Документ'); }
function reportNorms(report){ var basis=Array.isArray(report.normative_basis)?report.normative_basis:[]; if(basis.length)return basis.map(function(x){return x.number;}).filter(Boolean).join(', '); return String(report.normative_document||'—'); }
async function loadReports(){
  try{
    var r=await fetch(REPORTS_API); var data=await r.json(); if(!r.ok)throw Error(data.detail||('HTTP '+r.status));
    reportsData=(data.reports||[]).map(function(report){ return Object.assign({},report,{title:reportTitle(report),date:report.checked_at||report.created_at||'',documents:1,violations:(report.summary||{}).violations||0,totalChecks:(report.summary||{}).total||0}); });
    window.reportsData=reportsData; if(typeof window.renderReports==='function')window.renderReports(); if(typeof window.updateNavCounters==='function')window.updateNavCounters();
    return reportsData;
  }catch(e){ console.warn('[Reports] Load error:',e); return []; }
}
function renderReports(){
  var list=document.getElementById('reportsList'); if(!list)return;
  if(!Array.isArray(window.reportsData)||!window.reportsData.length){list.innerHTML='<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет сформированных отчётов. Сначала выполните проверку документа.</div>';return;}
  var html='';
  window.reportsData.forEach(function(report,index){
    var s=report.summary||{}; var title=reportTitle(report); var status=report.status==='completed'?'Проверка завершена':'В обработке';
    html+='<div class="report-item"><div class="report-icon">📄</div><div class="report-info">'
      +'<div class="report-title">'+escapeHtml(title)+'</div>'
      +'<div class="report-meta"><span>'+escapeHtml(reportDate(report.checked_at))+'</span><span>'+escapeHtml(reportNorms(report))+'</span><span>'+escapeHtml(String(s.pages||0))+' стр.</span><span>'+escapeHtml(String(s.violations||0))+' нарушений</span><span>'+escapeHtml(status)+'</span></div>'
      +'<div style="margin-top:6px;font-size:12px;color:var(--text-secondary);">'+escapeHtml(String(s.total||0))+' результатов · '+escapeHtml(String(s.critical||0))+' критических · '+escapeHtml(String(s.major||0))+' значительных · '+escapeHtml(String(s.unchecked||0))+' не подтверждено</div>'
      +'</div><div class="report-actions"><button class="btn btn-secondary btn-sm" onclick="viewReport('+index+')">Проверка</button><button class="btn btn-secondary btn-sm" onclick="downloadReport('+index+',\'pdf\')">PDF</button><button class="btn btn-secondary btn-sm" onclick="downloadReport('+index+',\'docx\')">Word</button></div></div>';
  });
  list.innerHTML=html;
}
async function createReport(){ return loadReports(); }
function generateReport(){ loadReports(); }
function viewReport(index){ var report=window.reportsData[index]; if(!report)return; window.currentReport=report; window.checksData=Array.isArray(report.results)?report.results:[]; try{localStorage.setItem('projectExpertAI.checks',JSON.stringify(window.checksData));}catch(e){} if(typeof window.renderChecks==='function')window.renderChecks(); if(typeof window.navigateTo==='function')window.navigateTo('checks'); }
function downloadReport(index,format){
  var report=window.reportsData[index]; if(!report)return;
  var endpoint=REPORTS_API+(format==='docx'?'/docx':'/pdf');
  fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report)}).then(function(r){if(!r.ok)return r.text().then(function(t){var d=t;try{d=JSON.parse(t).detail||t;}catch(_){}throw Error(d);});return r.blob();}).then(function(blob){var url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='project-expert-ai-normcontrol-'+(report.document_id||'report')+(format==='docx'?'.docx':'.pdf');document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);if(typeof window.showToast==='function')window.showToast('Отчёт сформирован: '+(format==='docx'?'Word':'PDF'),'success');}).catch(function(e){if(typeof window.showToast==='function')window.showToast('Не удалось сформировать отчёт: '+e.message,'error');});
}
window.loadReports=loadReports;window.renderReports=renderReports;window.createReport=createReport;window.generateReport=generateReport;window.viewReport=viewReport;window.downloadReport=downloadReport;
