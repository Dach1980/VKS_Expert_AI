// Project Expert AI — canonical remarks / expert results workspace
function renderChecks(){
  var list=document.getElementById('checksList'); if(!list)return;
  var data=Array.isArray(window.checksData)?window.checksData:[];
  var filter=window.currentFilter||'violation';
  var filtered=data.slice();
  if(filter!=='all')filtered=filtered.filter(function(x){return x.type===filter;});
  if(window.currentSectionFilter&&window.currentSectionFilter!=='all')filtered=filtered.filter(function(x){return x.section===window.currentSectionFilter||x.sheet===window.currentSectionFilter;});
  if(window.currentSeverityFilter)filtered=filtered.filter(function(x){return x.severity===window.currentSeverityFilter;});
  if(!filtered.length){
    var message=filter==='violation'?'Подтверждённых замечаний пока нет. Результаты «Требует проверки» не являются замечаниями.':'Нет результатов для выбранного фильтра.';
    list.innerHTML='<div style="text-align:center;padding:48px;color:var(--text-secondary);">'+escapeHtml(message)+'</div>';return;
  }
  var html='<div style="margin-bottom:12px;color:var(--text-secondary);font-size:13px;">'+(filter==='violation'?'Показываются только подтверждённые нарушения, вошедшие в реестр замечаний.':'Результаты экспертной проверки по выбранному статусу.')+'</div>';
  html+='<div style="overflow-x:auto;width:100%;"><table style="width:100%;border-collapse:collapse;font-size:13px;min-width:1050px;"><thead><tr>'+
    '<th style="text-align:left;padding:10px;">№</th><th style="text-align:left;padding:10px;">Лист</th><th style="text-align:left;padding:10px;">Параметр</th>'+
    '<th style="text-align:left;padding:10px;">Значение в исходнике</th><th style="text-align:left;padding:10px;">Нормативное требование</th>'+
    '<th style="text-align:left;padding:10px;">СП / пункт</th><th style="text-align:left;padding:10px;">Результат</th><th style="text-align:left;padding:10px;">Рекомендация</th></tr></thead><tbody>';
  filtered.forEach(function(item,index){
    var status=item.type==='violation'?'Нарушение':item.type==='compliant'?'Соответствие':'Требует проверки';
    var cls=item.type==='violation'?'danger':item.type==='compliant'?'success':'warning';
    var projectValue=item.project_value_raw||item.project_value||item.evidence_text||'—';
    if(item.project_unit&&!String(projectValue).includes(String(item.project_unit)))projectValue+=' '+item.project_unit;
    var normValue=item.normative_requirement||item.normative_value_raw||item.normative_value||'—';
    if(item.normative_unit&&!String(normValue).includes(String(item.normative_unit)))normValue+=' '+item.normative_unit;
    var normClause=[item.norm,item.clause?'п. '+item.clause:''].filter(Boolean).join(' / ')||'—';
    html+='<tr style="border-top:1px solid var(--border-color);vertical-align:top;">'+
      '<td style="padding:10px;white-space:nowrap;">'+(index+1)+'</td><td style="padding:10px;white-space:nowrap;">'+escapeHtml(item.page||item.sheet||'—')+'</td>'+ 
      '<td style="padding:10px;min-width:170px;"><strong>'+escapeHtml(item.parameter||item.title||'Проверка')+'</strong>'+(item.source_row?'<div style="margin-top:5px;color:var(--text-secondary);">'+escapeHtml(item.source_row)+'</div>':'')+'</td>'+ 
      '<td style="padding:10px;min-width:170px;"><strong>'+escapeHtml(projectValue)+'</strong>'+(item.comparison&&item.comparison!=='не определено'?'<div style="margin-top:5px;color:var(--text-secondary);">Сравнение: '+escapeHtml(item.comparison)+'</div>':'')+'</td>'+ 
      '<td style="padding:10px;min-width:220px;">'+escapeHtml(normValue)+'</td><td style="padding:10px;white-space:nowrap;">'+escapeHtml(normClause)+'</td>'+ 
      '<td style="padding:10px;white-space:nowrap;"><span class="status-badge '+cls+'">'+status+'</span></td><td style="padding:10px;min-width:180px;">'+escapeHtml(item.recommendation||'—')+(item.image?'<div style="margin-top:8px;"><img src="'+escapeHtml(item.image)+'" alt="Фрагмент" style="max-width:180px;height:auto;border-radius:6px;"></div>':'')+'</td></tr>';
  });
  html+='</tbody></table></div>';list.innerHTML=html;
}
function setCheckFilter(value){window.currentFilter=value||'violation';document.querySelectorAll('.filter-tab').forEach(function(x){x.classList.toggle('active',x.dataset.filter===window.currentFilter);});renderChecks();}
document.querySelectorAll('.filter-tab').forEach(function(tab){tab.addEventListener('click',function(){setCheckFilter(tab.dataset.filter||'violation');});});
var sf=document.getElementById('sectionFilter');if(sf)sf.addEventListener('change',function(){window.currentSectionFilter=this.value;renderChecks();});
var sevf=document.getElementById('severityFilter');if(sevf)sevf.addEventListener('change',function(){window.currentSeverityFilter=this.value;renderChecks();});
window.renderChecks=renderChecks;window.setCheckFilter=setCheckFilter;
