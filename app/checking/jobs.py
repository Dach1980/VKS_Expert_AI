"""In-process background jobs and progress estimation for document checks."""
from __future__ import annotations
import threading,time,uuid
from datetime import datetime
from typing import Any
from app.checking.resilient import run_resilient_check
_jobs:dict[str,dict[str,Any]]={};_lock=threading.Lock()
_STAGE_LABELS={"queued":"Ожидание запуска","preparing":"Подготовка документа","visual":"Визуальный анализ страниц","normative":"Нормативная проверка через RAG","retry":"Повторная попытка страницы","completed":"Формирование отчёта","error":"Ошибка проверки"}
def _update(job_id:str,**fields:Any)->None:
    with _lock:
        job=_jobs.get(job_id)
        if job is None:return
        job.update(fields);stage=str(job.get("stage","queued"));job["stage_label"]=_STAGE_LABELS.get(stage,stage);started=job.get("started_monotonic");total_pages=int(job.get("total_pages",0) or 0);completed_pages=int(job.get("pages_completed",0) or 0)
        if started:
            elapsed=max(0.0,time.monotonic()-started);job["elapsed_seconds"]=round(elapsed)
            if total_pages>0 and completed_pages>0 and completed_pages<total_pages:
                spp=elapsed/completed_pages;job["average_seconds_per_page"]=round(spp,1);job["estimated_remaining_seconds"]=round(spp*(total_pages-completed_pages))
            elif total_pages>0 and completed_pages>=total_pages:
                job["average_seconds_per_page"]=round(elapsed/total_pages,1);job["estimated_remaining_seconds"]=0
            else:job["estimated_remaining_seconds"]=None
def _progress(job_id:str,data:dict[str,Any])->None:
    fields=dict(data)
    if data.get("page_completed"):
        current=int(data.get("current_page",0) or 0)
        with _lock:
            job=_jobs.get(job_id);previous=int(job.get("pages_completed",0) or 0) if job else 0
        fields["pages_completed"]=max(previous,current)
    _update(job_id,**fields)
def _worker(job_id:str,document_id:str,skill_id:str)->None:
    _update(job_id,status="running",started_at=datetime.now().isoformat(timespec="seconds"),started_monotonic=time.monotonic())
    try:
        report=run_resilient_check(document_id,progress_callback=lambda data:_progress(job_id,data),skill_id=skill_id);scope=report.get("check_scope") or {};pages_checked=int(scope.get("pages_checked",report.get("summary",{}).get("pages",0)) or 0);pages_available=int(scope.get("pages_available",pages_checked) or pages_checked)
        _update(job_id,status="completed",percent=100,stage="completed",message="Проверка завершена. Отчёт готов.",result=report,current_page=pages_available,total_pages=pages_available,pages_completed=pages_checked,pages_checked=pages_checked,pages_available=pages_available,failed_pages=scope.get("failed_pages",[]),report_url=f"/api/reports/{document_id}",report_pdf_url="/api/reports/pdf",report_docx_url="/api/reports/docx",finished_at=datetime.now().isoformat(timespec="seconds"),estimated_remaining_seconds=0)
    except Exception as error:
        _update(job_id,status="error",stage="error",percent=100,message=f"Ошибка проверки: {error}",error=str(error),finished_at=datetime.now().isoformat(timespec="seconds"),estimated_remaining_seconds=0)
def start_check_job(document_id:str,skill_id:str="vk_wastewater")->dict[str,Any]:
    job_id=uuid.uuid4().hex
    with _lock:
        _jobs[job_id]={"job_id":job_id,"document_id":document_id,"skill_id":skill_id,"status":"queued","stage":"queued","stage_label":_STAGE_LABELS["queued"],"percent":0,"current_page":0,"total_pages":0,"pages_completed":0,"pages_checked":0,"pages_available":None,"message":"Проверка поставлена в очередь…","estimated_remaining_seconds":None,"average_seconds_per_page":None,"elapsed_seconds":0,"created_at":datetime.now().isoformat(timespec="seconds")}
    thread=threading.Thread(target=_worker,args=(job_id,document_id,skill_id),daemon=True,name=f"check-{job_id[:8]}");thread.start();return get_check_job(job_id) or {}
def get_check_job(job_id:str)->dict[str,Any]|None:
    with _lock:
        job=_jobs.get(job_id)
        if not job:return None
        return {k:v for k,v in job.items() if k!="started_monotonic"}
