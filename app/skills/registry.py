"""Registry of selectable engineering checking skills.

A skill describes the expert workflow: scope, checklist, extraction hints and
normative documents. The registry deliberately keeps normative files separate;
the skill only declares which active normative documents are applicable.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


_VK_WASTEWATER_CHECKS = [
    {"id": "wastewater_flow", "name": "Расчётные расходы сточных вод", "parameters": ["расход канализации", "расчётный расход", "Q"], "segments": ["internal", "external"]},
    {"id": "sewer_diameter", "name": "Диаметры канализационных труб", "parameters": ["диаметр канализационной трубы", "диаметр стояка", "DN"], "segments": ["internal", "external"]},
    {"id": "sewer_slope", "name": "Уклоны канализационных труб", "parameters": ["уклон канализационной трубы", "уклон", "i"], "segments": ["internal", "external"]},
    {"id": "sewer_ventilation", "name": "Вентиляция канализационных стояков", "parameters": ["вентиляция канализации", "вытяжная часть", "вентиляционный стояк"], "segments": ["internal"]},
    {"id": "sewer_outlets", "name": "Выпуски канализации", "parameters": ["выпуск канализации", "выпуск"], "segments": ["internal", "external"]},
    {"id": "sewer_cleanouts", "name": "Ревизии и прочистки", "parameters": ["ревизия", "прочистка"], "segments": ["internal"]},
    {"id": "sewer_material", "name": "Материал труб", "parameters": ["материал канализационных труб", "материал труб"], "segments": ["internal", "external"]},
    {"id": "storm_separation", "name": "Разделение бытовой и дождевой канализации", "parameters": ["разделение канализации", "бытовая канализация", "дождевая канализация"], "segments": ["internal", "external"]},
    {"id": "noise_insulation", "name": "Шумоизоляция стояков", "parameters": ["шумоизоляция стояка", "шум", "вибрация"], "segments": ["internal"]},
    {"id": "irrigation", "name": "Поливочные краны", "parameters": ["поливочный кран", "полив"], "segments": ["internal"]},
    {"id": "meters", "name": "Приборы учёта", "parameters": ["прибор учёта", "счётчик", "водомерный узел"], "segments": ["internal"]},
    {"id": "emergency_outlets", "name": "Аварийные выпуски", "parameters": ["аварийный выпуск", "аварийные выпуски"], "segments": ["internal"]},
    {"id": "ar_coordination", "name": "Согласование с архитектурой", "parameters": ["санитарный прибор", "помещение", "стояк", "точка подключения"], "segments": ["internal"]},
]

_SKILLS: dict[str, dict[str, Any]] = {
    "vk_wastewater": {
        "id": "vk_wastewater",
        "code": "ВК",
        "name": "Система водоотведения",
        "description": "Полная инженерная проверка систем внутреннего и наружного водоотведения.",
        "normative_documents": ["СП 30.13330.2020", "СП 31.13330.2021", "СП 32.13330.2018"],
        "default_segment": "internal",
        "checks": _VK_WASTEWATER_CHECKS,
        "extraction": {
            "allowed_fact_types": ["flow", "diameter", "slope", "ventilation", "outlet", "cleanout", "material", "separation", "noise_insulation", "irrigation", "meter", "fixture", "connection"],
            "exclude": ["штамп", "рамка", "название листа", "номер листа", "подпись", "декоративный текст", "секционные ворота", "связь металлическая"],
            "require_project_context": True,
        },
        "routing": {
            "internal_wastewater": ["СП 30.13330.2020"],
            "external_wastewater": ["СП 32.13330.2018"],
            "external_water": ["СП 31.13330.2021"],
            "internal_water": ["СП 30.13330.2020"],
            "cross_boundary": ["СП 30.13330.2020", "СП 32.13330.2018"],
        },
    }
}


def list_skills() -> list[dict[str, Any]]:
    """Return UI-safe skill metadata in deterministic order."""
    return [
        {key: deepcopy(value) for key, value in skill.items() if key in {"id", "code", "name", "description", "normative_documents", "checks"}}
        for skill in _SKILLS.values()
    ]


def get_skill(skill_id: str | None) -> dict[str, Any]:
    """Resolve a skill or raise a clear error for an unknown selection."""
    key = str(skill_id or "vk_wastewater").strip()
    skill = _SKILLS.get(key)
    if skill is None:
        raise KeyError(f"Неизвестный профиль проверки: {key}")
    return deepcopy(skill)


def get_check(skill_id: str | None, check_id: str) -> dict[str, Any]:
    skill = get_skill(skill_id)
    for check in skill["checks"]:
        if check["id"] == check_id:
            return check
    raise KeyError(f"Проверка {check_id!r} не входит в профиль {skill['id']}")
