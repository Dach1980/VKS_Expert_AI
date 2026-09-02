"""API for selectable expert checking profiles."""
from __future__ import annotations
from fastapi import APIRouter,HTTPException
from app.skills.registry import get_skill,list_skills
router=APIRouter(prefix="/api/skills",tags=["skills"])
@router.get("")
def skills():
    return {"skills":list_skills()}
@router.get("/{skill_id}")
def skill(skill_id:str):
    try:return get_skill(skill_id)
    except KeyError as error:raise HTTPException(status_code=404,detail=str(error)) from error
