// Project Expert AI — detailed findings / remarks
function renderChecks(){
  var list=document.getElementById('checksList'); if(!list)return;
  var data=Array.isArray(window.checksData)?window.checksData:[];
  var filtered=data.slice();
  if(window.currentFilter&&window.currentFilter!=='all')filtered=filtered.filter(function(x){return x.type===window.currentFilter;});
  if(window.currentSectionFilter&&window.currentSectionFilter!=='all')filtered=filtered.filter(function(x){return x.section===window.currentSectionFilter||x.sheet===window.currentSectionFilter;});
  if(window.currentSeverityFilter)filtered=filtered.filter(function(x){return x.severity===window.currentSeverityFilter;});
  if(!filtered.length){list.innerHTML='<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет результатов проверки. Запустите проверку проектного PDF.</div>';return;}
  var html='';
  filtered.forEach(function(item){
    var status=item.type==='violation'?'Нарушение':item.type==='compliant'?'Соответствие':'Не подтверждено';
    var sev=item.severity==='critical'?'Критическое':item.severity==='major'?'Значительное':item.severity==='minor'?'Рекомендация':'';
    html+='<div class="violation-card"><div class="violation-header"><div><div class="violation-title">'+escapeHtml(item.title||'Результат проверки')+'</div><div class="violation-meta">'
      +(item.page?'<span>📄 PDF стр. '+escapeHtml(item.page)+'</span>':'')+(item.norm?'<span>📋 '+escapeHtml(item.norm)+'</span>':'')+(item.clause?'<span>п. '+escapeHtml(item.clause)+'</span>':'')
      +'<span class="status-badge '+(item.type==='violation'?'danger':item.type==='compliant'?'success':'warning')+'">'+status+'</span>'+(sev?'<span class="status-badge">'+sev+'</span>':'')+'</div></div></div>'
      +'<div class="violation-description">'+escapeHtml(item.description||'')+'</div>'
      +(item.evidence_text?'<div style="margin-top:8px;padding:10px;border-radius:8px;background:var(--bg-secondary);font-size:13px;"><strong>Факт на листе:</strong> '+escapeHtml(item.evidence_text)+'</div>':'')
      +(item.recommendation?'<div class="violation-recommendation"><strong>Рекомендуемое исправление:</strong> '+escapeHtml(item.recommendation)+'</div>':'')
      +(item.image?'<div class="violation-image-container"><img src="'+escapeHtml(item.image)+'" class="violation-image" alt="Доказательный фрагмент"></div>':'')
      +'</div>';
  });
  list.innerHTML=html;
}
function setCheckFilter(value){window.currentFilter=value||'all';document.querySelectorAll('.filter-tab').forEach(function(x){x.classList.toggle('active',x.dataset.filter===window.currentFilter);});renderChecks();}
document.querySelectorAll('.filter-tab').forEach(function(tab){tab.addEventListener('click',function(){setCheckFilter(tab.dataset.filter||'all');});});
var sf=document.getElementById('sectionFilter');if(sf)sf.addEventListener('change',function(){window.currentSectionFilter=this.value;renderChecks();});
var sevf=document.getElementById('severityFilter');if(sevf)sevf.addEventListener('change',function(){window.currentSeverityFilter=this.value;renderChecks();});
window.renderChecks=renderChecks;window.setCheckFilter=setCheckFilter;
