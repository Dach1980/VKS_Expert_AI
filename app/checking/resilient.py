"""Resilient page-level checking with targeted ВК audit and multi-norm RAG."""
from __future__ import annotations
import json,time
from datetime import datetime
from pathlib import Path
from typing import Any,Callable
from PIL import Image
from app.checking.first_pass import CHECK_DPI,DEFAULT_NORM_NUMBER,MAX_NORM_RESULTS,REPORT_API_BASE,_json_array,_strict_candidates,_vision_request
from app.checking.audit_decision import decide_audit
from app.checking.page_pipeline import annotate_evidence,normalize_bbox,render_pdf_pages
from app.checking.vk_audit import build_vk_audit_prompt
from app.knowledge.storage import KnowledgeStorage
from app.llm.lmstudio_client import LMStudioClient
from app.rag.retriever import Retriever
from app.rag.audit_retrieval import retrieve_audit_context
ProgressCallback=Callable[[dict[str,Any]],None]
MAX_PAGE_RETRIES=3
RETRY_DELAY_SECONDS=3.0
MAX_PAGE_CANDIDATES=8
def _checkpoint_path(directory:Path)->Path:return directory/"checkpoint.json"
def _write_json(path:Path,value:dict[str,Any])->None:
    tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(path)
def _load_checkpoint(path:Path,document_id:str,pdf_name:str)->dict[str,Any]:
    empty={"status":"running","document_id":document_id,"document_name":pdf_name,"pages_completed":0,"completed_pages":[],"findings":[],"last_error":None}
    if not path.exists():return empty
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value,dict) or value.get("document_id")!=document_id:return empty
        value.setdefault("completed_pages",[]);value.setdefault("findings",[]);value.setdefault("pages_completed",len(value["completed_pages"]));return value
    except (OSError,ValueError,json.JSONDecodeError):return empty
def _indexed_norms(storage:KnowledgeStorage)->list[tuple[dict[str,Any],dict[str,Any],Retriever]]:
    result=[]
    for document in storage.registry.get_all_documents():
        try:
            version=storage.get_current_version(document["id"]);paths=storage.paths(document["id"],version["id"])
            if (paths.embeddings/"index.faiss").exists() and (paths.embeddings/"metadata.json").exists():result.append((document,version,Retriever(document["id"],version["id"],storage)))
        except Exception:continue
    return result
def _multi_context(results:list[dict[str,Any]])->str:
    parts=[]
    for item in results:
        content=item.get("content",{});text=content.get("text","") if isinstance(content,dict) else str(content)
        if text:parts.append(f"{item.get('norm_number','СП')}, версия {item.get('version','—')}, стр. {item.get('page','—')}: {text}")
    value="\n\n".join(parts);return value[:12000]+("\n[нормативный контекст сокращён]" if len(value)>12000 else "")
def _bbox_has_real_evidence(image_path:Path,bbox:list[float])->bool:
    try:
        with Image.open(image_path).convert("L") as image:
            width,height=image.size;x1,y1,x2,y2=bbox;area=max(1.0,(x2-x1)*(y2-y1))
            if area/float(width*height)>0.82:return False
            crop=image.crop((int(x1),int(y1),int(x2),int(y2)));pixels=list(crop.getdata());return bool(pixels) and sum(1 for value in pixels if value<245)/len(pixels)>=0.001
    except Exception:return False
def _build_report(document_id:str,pdf_name:str,norms,total_pages:int,findings:list[dict[str,Any]],failed_pages:list[int])->dict[str,Any]:
    violations=[x for x in findings if x.get("type")=="violation"];basis=[{"number":d.get("number"),"version":v.get("id"),"title":d.get("title")} for d,v,_ in norms]
    return {"template":"reference_normcontrol_report_ios_3.1","document_id":document_id,"document_name":pdf_name,"checked_at":datetime.now().isoformat(timespec="seconds"),"status":"completed","normative_document":", ".join(str(x.get("number")) for x in basis if x.get("number")) or DEFAULT_NORM_NUMBER,"normative_version":", ".join(str(x.get("version")) for x in basis if x.get("version")),"normative_basis":basis,"results":findings,"check_scope":{"pages_checked":total_pages-len(failed_pages),"pages_available":total_pages,"limited":False,"max_pages":None,"failed_pages":failed_pages},"summary":{"pages":total_pages,"total":len(findings),"violations":len(violations),"critical":sum(x.get("severity")=="critical" for x in violations),"major":sum(x.get("severity")=="major" for x in violations),"minor":sum(x.get("severity")=="minor" for x in violations),"compliant":sum(x.get("type")=="compliant" for x in findings),"unchecked":sum(x.get("type")=="unchecked" for x in findings)}}
def run_resilient_check(document_id:str,normative_number:str=DEFAULT_NORM_NUMBER,progress_callback:ProgressCallback|None=None)->dict[str,Any]:
    def progress(**data):
        if progress_callback:progress_callback(data)
    root=Path(__file__).resolve().parents[2]/"knowledge"/"project_documents"/document_id;pdf_path=root/"source.pdf"
    if not pdf_path.exists():raise RuntimeError("Исходный PDF не найден")
    evidence_dir=root/"checking"/"first_pass";evidence_dir.mkdir(parents=True,exist_ok=True);checkpoint_file=_checkpoint_path(evidence_dir);storage=KnowledgeStorage();norms=_indexed_norms(storage)
    if not norms:raise RuntimeError("Нет индексированных действующих нормативных документов. Индексируйте действующие СП в разделе «Нормы».")
    progress(stage="preparing",percent=1,current_page=0,total_pages=0,message="Подготовка проверки и нормативной базы…");pages=render_pdf_pages(pdf_path,evidence_dir,dpi=CHECK_DPI);total_pages=len(pages);checkpoint=_load_checkpoint(checkpoint_file,document_id,pdf_path.name);completed_pages={int(x) for x in checkpoint.get("completed_pages",[])};findings=[x for x in checkpoint.get("findings",[]) if isinstance(x,dict)];next_finding_id=max((int(x.get("id",0) or 0) for x in findings),default=0)+1;norm_names=", ".join(str(d.get("number")) for d,_,_ in norms)
    progress(stage="visual",percent=2,current_page=max(completed_pages,default=0),total_pages=total_pages,message=(f"Возобновляю проверку: завершено {len(completed_pages)} из {total_pages}. Нормативы: {norm_names}." if completed_pages else f"Подготовлено страниц: {total_pages}. Нормативы: {norm_names}. Начинаю инженерный аудит…"));failed_pages=[]
    for page_index,page in enumerate(pages,start=1):
        if page_index in completed_pages:continue
        page_start=2+int((page_index-1)/max(total_pages,1)*96);page_success=False;last_error=None
        for attempt in range(1,MAX_PAGE_RETRIES+1):
            client=LMStudioClient(model=None)
            try:
                progress(stage="visual",percent=page_start,current_page=page_index,total_pages=total_pages,retry=attempt if attempt>1 else 0,message=(f"Повторная обработка страницы {page_index} из {total_pages} (попытка {attempt}/{MAX_PAGE_RETRIES})…" if attempt>1 else f"Инженерный аудит страницы {page_index} из {total_pages}…"));candidates=_strict_candidates(_json_array(_vision_request(client,build_vk_audit_prompt(page.page),Path(page.image_path),1400)))[:MAX_PAGE_CANDIDATES];progress(stage="normative",percent=min(98,page_start+1),current_page=page_index,total_pages=total_pages,message=f"Страница {page_index}: найдено инженерных фактов {len(candidates)}. Сверяю с {len(norms)} нормативными документами…");page_findings=[]
                for candidate in candidates:
                    bbox=normalize_bbox(candidate.get("bbox"),page.width,page.height)
                    if not bbox or not _bbox_has_real_evidence(Path(page.image_path),bbox):continue
                    norm_results=retrieve_audit_context(norms,candidate,top_k=MAX_NORM_RESULTS);norm_text=_multi_context(norm_results)
                    if not norm_text:continue
                    decision=decide_audit(client,candidate,norm_text)
                    if decision.get("type") not in {"violation","compliant","unchecked"}:decision["type"]="unchecked"
                    if decision.get("type")=="violation" and float(decision.get("confidence") or 0)<0.55:decision["type"]="unchecked"
                    finding_id=next_finding_id+len(page_findings);evidence_path=evidence_dir/"annotated"/f"page_{page.page:04d}_finding_{finding_id:03d}.png";evidence_image=annotate_evidence(page.image_path,bbox,evidence_path)
                    page_findings.append({"id":finding_id,"type":decision.get("type","unchecked"),"docId":document_id,"docName":pdf_path.name,"title":str(decision.get("title") or candidate.get("title") or "Результат проверки"),"description":str(decision.get("description") or candidate.get("description") or ""),"recommendation":str(decision.get("recommendation") or ""),"sheet":str(decision.get("sheet") or ""),"norm":str(decision.get("norm") or (norm_results[0].get("norm_number") if norm_results else normative_number)),"clause":str(decision.get("clause") or ""),"severity":str(decision.get("severity") or "minor"),"page":page.page,"bbox":bbox,"evidence_image":evidence_image,"image":f"{REPORT_API_BASE}/api/reports/evidence/{document_id}/{evidence_path.name}","evidence_text":str(candidate.get("evidence_text") or ""),"confidence":decision.get("confidence",candidate.get("confidence")),"normative_sources":norm_results})
                findings.extend(page_findings);next_finding_id+=len(page_findings);completed_pages.add(page_index);checkpoint.update({"status":"running","pages_completed":len(completed_pages),"completed_pages":sorted(completed_pages),"findings":findings,"last_error":None});_write_json(checkpoint_file,checkpoint);page_success=True;progress(stage="visual",percent=min(98,2+int(page_index/max(total_pages,1)*96)),current_page=page_index,total_pages=total_pages,page_completed=True,message=f"Страница {page_index} из {total_pages} завершена. Значимых результатов: {len(page_findings)}.");break
            except Exception as error:
                last_error=error;checkpoint["last_error"]={"page":page_index,"attempt":attempt,"error":str(error),"at":datetime.now().isoformat(timespec="seconds")};_write_json(checkpoint_file,checkpoint)
                if attempt<MAX_PAGE_RETRIES:progress(stage="retry",percent=page_start,current_page=page_index,total_pages=total_pages,retry=attempt,message=f"Ошибка страницы {page_index}: {error}. Повторяю через {int(RETRY_DELAY_SECONDS)} с…");time.sleep(RETRY_DELAY_SECONDS)
                else:failed_pages.append(page_index);progress(stage="error",percent=page_start,current_page=page_index,total_pages=total_pages,message=f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {error}")
        if not page_success:raise RuntimeError(f"Страница {page_index} не обработана после {MAX_PAGE_RETRIES} попыток: {last_error}")
    report=_build_report(document_id,pdf_path.name,norms,total_pages,findings,failed_pages);_write_json(evidence_dir/"report.json",report);checkpoint.update({"status":"completed","pages_completed":total_pages,"completed_pages":list(range(1,total_pages+1)),"findings":findings,"last_error":None});_write_json(checkpoint_file,checkpoint);progress(stage="completed",percent=100,current_page=total_pages,total_pages=total_pages,page_completed=True,message="Проверка завершена. Отчёт готов.");return report
