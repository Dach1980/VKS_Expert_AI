"""Registry of selectable engineering checking skills.

A Skill is an expert specification, not a list of prompts. It defines what
must be found in the project, which facts are extracted, how the document is
routed to normative sources, and what evidence is required before a finding
can be classified as violation, compliant, or unchecked.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


# The normative base is global, while each individual check declares its
# applicable route. This prevents unrelated SPs from competing in RAG.
_VK_WASTEWATER_CHECKS: list[dict[str, Any]] = [
    {
        "id": "wastewater_flow",
        "name": "Расчётные расходы",
        "description": "Проверка расчётных расходов хозяйственно-бытовых, дождевых и при наличии производственных сточных вод.",
        "what_to_find": ["таблицы расчётных расходов", "Q", "суточный и часовой расход", "максимальный секундный расход", "расход дождевых стоков", "производственные стоки"],
        "fact_types": ["wastewater_flow", "stormwater_flow", "production_wastewater_flow"],
        "parameters": ["расчётный расход сточных вод", "максимальный секундный расход", "суточный объём стоков", "часовой расход", "расход дождевых вод"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["numeric_threshold", "calculation_method", "conditional"],
        "numeric_comparison": True,
        "evidence_required": ["точное значение расхода", "единица измерения", "контекст системы/участка", "лист или таблица-источник"],
        "violation_when": "Подтверждено, что проектное значение или способ определения противоречит конкретному требованию применимого СП.",
        "compliant_when": "Проектное значение/метод напрямую соответствует конкретному требованию СП и единицы сопоставимы.",
        "unchecked_when": "Недостаточно исходных данных, не определён участок системы, отсутствует применимое численное требование или сравнение требует неподтверждённого расчёта.",
    },
    {
        "id": "sewer_diameter",
        "name": "Диаметры",
        "description": "Проверка диаметров канализационных труб, стояков, выпусков и наружных участков по назначению и расчётному расходу.",
        "what_to_find": ["DN/Ø труб", "диаметры стояков", "диаметры выпусков", "таблицы диаметров", "обозначения К1/К2/НК"],
        "fact_types": ["pipe_diameter", "riser_diameter", "outlet_diameter"],
        "parameters": ["диаметр канализационной трубы", "диаметр стояка", "диаметр выпуска", "DN"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["numeric_threshold", "conditional", "table_lookup"],
        "numeric_comparison": True,
        "evidence_required": ["точный диаметр", "система/участок", "расчётный или табличный контекст", "лист и источник значения"],
        "violation_when": "Подтверждено, что диаметр не удовлетворяет конкретному минимальному/максимальному требованию или условию применимого СП.",
        "compliant_when": "Для данного участка подтверждено соответствие диаметра конкретному требованию СП.",
        "unchecked_when": "Диаметр виден, но отсутствует необходимый расход, уклон, участок или конкретное нормативное условие для однозначной проверки.",
    },
    {
        "id": "sewer_slope",
        "name": "Уклоны",
        "description": "Проверка уклонов внутренних и наружных самотечных канализационных труб с учётом диаметра и назначения участка.",
        "what_to_find": ["i=...", "уклон труб", "отметки начала/конца", "продольный профиль", "диаметр участка"],
        "fact_types": ["pipe_slope", "pipe_elevation"],
        "parameters": ["уклон канализационной трубы", "уклон", "i"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["numeric_threshold", "conditional", "table_lookup"],
        "numeric_comparison": True,
        "evidence_required": ["значение уклона или две отметки", "диаметр участка", "система", "лист/фрагмент"],
        "violation_when": "Подтверждено численное или условное несоответствие уклона конкретному требованию СП.",
        "compliant_when": "Уклон и связанные условия напрямую удовлетворяют требованию СП.",
        "unchecked_when": "Есть только формула/символ i без однозначного значения, диаметра или контекста участка.",
    },
    {
        "id": "sewer_ventilation",
        "name": "Вентиляция",
        "description": "Проверка вентиляции канализационных стояков и вытяжных частей внутренней канализации.",
        "what_to_find": ["фановая труба", "вытяжная часть стояка", "вентиляционный стояк", "выход выше кровли", "диаметр вытяжной части"],
        "fact_types": ["sewer_ventilation", "vent_stack", "roof_outlet"],
        "parameters": ["вентиляция канализационного стояка", "вытяжная часть стояка", "фановая труба", "высота выхода над кровлей"],
        "systems": ["wastewater"],
        "segments": ["internal"],
        "normative_documents": {"internal": ["СП 30.13330.2020"]},
        "requirement_type": ["presence", "numeric_threshold", "conditional"],
        "numeric_comparison": True,
        "evidence_required": ["сам факт наличия/отсутствия вентиляции", "связь со стояком", "конкретный размер при численной проверке", "лист/схема"],
        "violation_when": "Подтверждено отсутствие обязательного решения либо конкретное отступление от требования СП.",
        "compliant_when": "Необходимое вентиляционное решение и его параметры подтверждены проектом и соответствуют СП.",
        "unchecked_when": "На листе есть косвенный символ/труба, но нельзя достоверно установить её функцию как вентиляции канализации.",
    },
    {
        "id": "sewer_outlets",
        "name": "Выпуски",
        "description": "Проверка устройства выпусков внутренней канализации и перехода к наружной сети.",
        "what_to_find": ["выпуски К1/К2", "наружный выпуск", "место выхода из здания", "диаметр выпуска", "отметки выпуска"],
        "fact_types": ["sewer_outlet", "outlet_diameter", "outlet_elevation"],
        "parameters": ["выпуск канализации", "диаметр выпуска", "отметка выпуска", "место выпуска"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["presence", "numeric_threshold", "conditional"],
        "numeric_comparison": True,
        "evidence_required": ["обозначение выпуска", "система", "диаметр/отметка при проверке", "лист или схема"],
        "violation_when": "Подтверждено обязательное, но отсутствующее/неверно выполненное решение либо конкретное численное несоответствие.",
        "compliant_when": "Выпуск и проверяемые параметры подтверждены и соответствуют СП.",
        "unchecked_when": "Видно обозначение выпуска, но его функция, участок или обязательность не установлены.",
    },
    {
        "id": "sewer_cleanouts",
        "name": "Ревизии и прочистки",
        "description": "Проверка доступности и размещения ревизий, прочисток и иных средств обслуживания канализации.",
        "what_to_find": ["ревизии", "прочистки", "люки доступа", "обозначения Р/П", "места обслуживания"],
        "fact_types": ["cleanout", "inspection_point", "access_point"],
        "parameters": ["ревизия", "прочистка", "место установки ревизии", "доступность"],
        "systems": ["wastewater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["presence", "spacing", "conditional"],
        "numeric_comparison": True,
        "evidence_required": ["точка ревизии/прочистки", "участок или стояк", "расстояние при проверке шага", "лист/план/схема"],
        "violation_when": "Подтверждено отсутствие обязательной точки либо несоблюдение конкретного условия размещения.",
        "compliant_when": "Требуемая точка и её размещение подтверждены и соответствуют СП.",
        "unchecked_when": "План недостаточен для определения доступности или обязательности точки.",
    },
    {
        "id": "sewer_material",
        "name": "Материалы",
        "description": "Проверка материала труб и фасонных частей по назначению, условиям эксплуатации и требованиям СП.",
        "what_to_find": ["ПВХ", "ПП", "чугун", "сталь", "материал труб", "марка/тип труб"],
        "fact_types": ["pipe_material", "fitting_material"],
        "parameters": ["материал канализационных труб", "материал труб", "материал фасонных частей"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["allowed_material", "conditional", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["точное обозначение материала", "назначение участка", "условия применения при необходимости", "лист/спецификация"],
        "violation_when": "Материал прямо запрещён/не соответствует установленному условию для данного применения.",
        "compliant_when": "Материал прямо допускается СП для данного применения и это подтверждено контекстом.",
        "unchecked_when": "Материал назван, но область применения или условие допуска не установлены.",
    },
    {
        "id": "storm_separation",
        "name": "Разделение систем",
        "description": "Проверка раздельного решения хозяйственно-бытовой и дождевой канализации и правильной идентификации систем.",
        "what_to_find": ["К1", "К2", "К3", "бытовая канализация", "дождевая канализация", "ливневая сеть", "раздельные выпуски"],
        "fact_types": ["sewer_system", "storm_system", "system_connection"],
        "parameters": ["разделение бытовой и дождевой канализации", "система К1", "система К2", "связь сетей"],
        "systems": ["wastewater", "stormwater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["presence", "prohibition", "conditional", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["обозначения обеих систем", "схема их трассировки/подключения", "точка соединения при наличии", "лист/схема"],
        "violation_when": "Подтверждено запрещённое смешение или иное прямое противоречие требованию СП.",
        "compliant_when": "Раздельность и подключения однозначно подтверждены проектом и соответствуют СП.",
        "unchecked_when": "Обозначения систем есть, но схема не позволяет установить их взаимосвязь.",
    },
    {
        "id": "noise_insulation",
        "name": "Шумоизоляция",
        "description": "Проверка мероприятий по снижению шума и вибрации от канализационных стояков и трубопроводов.",
        "what_to_find": ["звукоизоляция", "шумоизоляция", "виброизоляция", "изоляция стояка", "облицовка шахты"],
        "fact_types": ["noise_insulation", "vibration_isolation"],
        "parameters": ["шумоизоляция стояка", "звукоизоляция", "виброизоляция"],
        "systems": ["wastewater"],
        "segments": ["internal"],
        "normative_documents": {"internal": ["СП 30.13330.2020"]},
        "requirement_type": ["presence", "conditional", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["конкретное мероприятие", "место/стояк", "материал или конструкция при наличии", "лист/узел/описание"],
        "violation_when": "СП устанавливает обязательное мероприятие для подтверждённых условий, а проект его не предусматривает.",
        "compliant_when": "Обязательное мероприятие явно предусмотрено и применимо к соответствующему участку.",
        "unchecked_when": "Нельзя установить акустические условия или обязательность мероприятия только по имеющемуся листу.",
    },
    {
        "id": "irrigation",
        "name": "Поливочные устройства",
        "description": "Кросс-системная проверка наличия предусмотренных проектом поливочных устройств; фактически относится к водоснабжению и не должна смешиваться с канализационными требованиями.",
        "what_to_find": ["поливочные краны", "краны для полива", "точки полива", "наружные водоразборные устройства"],
        "fact_types": ["irrigation_point", "water_fixture"],
        "parameters": ["поливочный кран", "точка полива", "водоразборное устройство"],
        "systems": ["water_supply"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 31.13330.2021"]},
        "requirement_type": ["presence", "conditional", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["точка полива", "её назначение", "место/лист", "связь с водоснабжением при межсистемной проверке"],
        "violation_when": "Только при наличии подтверждённого обязательного требования и подтверждённого отсутствия/противоречия в проекте.",
        "compliant_when": "Предусмотренное устройство подтверждено и соответствует применимому требованию.",
        "unchecked_when": "Нельзя определить требуемое количество/место без исходных данных или проверки другого раздела.",
        "cross_system": True,
    },
    {
        "id": "meters",
        "name": "Приборы учёта",
        "description": "Кросс-системная проверка водомерных узлов и приборов учёта как части водоснабжения; не считать произвольные размеры оборудования канализационными расходами.",
        "what_to_find": ["счётчик воды", "водомерный узел", "прибор учёта", "узел ввода", "диаметр водомерного узла"],
        "fact_types": ["water_meter", "metering_unit"],
        "parameters": ["прибор учёта", "счётчик", "водомерный узел"],
        "systems": ["water_supply"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 31.13330.2021"]},
        "requirement_type": ["presence", "numeric_threshold", "conditional", "semantic"],
        "numeric_comparison": True,
        "evidence_required": ["явное обозначение прибора", "узел/система", "диаметр или параметры только если они относятся к счётчику", "лист/схема"],
        "violation_when": "Подтверждено обязательное решение и его отсутствие/несоответствие конкретному требованию.",
        "compliant_when": "Прибор учёта и проверяемые параметры соответствуют применимому требованию.",
        "unchecked_when": "Число/размер относится к другому оборудованию или не подтверждена его связь с учётом воды.",
        "cross_system": True,
    },
    {
        "id": "emergency_outlets",
        "name": "Аварийные решения",
        "description": "Проверка предусмотренных нормативами аварийных выпусков и иных решений для аварийных режимов, если они применимы к объекту.",
        "what_to_find": ["аварийный выпуск", "аварийный сброс", "аварийная схема", "защита от затопления", "меры аварийного режима"],
        "fact_types": ["emergency_outlet", "emergency_measure"],
        "parameters": ["аварийный выпуск", "аварийное решение", "аварийный сброс"],
        "systems": ["wastewater"],
        "segments": ["internal", "external"],
        "normative_documents": {"internal": ["СП 30.13330.2020"], "external": ["СП 32.13330.2018"]},
        "requirement_type": ["presence", "conditional", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["условие применимости", "аварийное решение", "место/система", "лист/схема/описание"],
        "violation_when": "Установлена применимость обязательного аварийного решения и подтверждено его отсутствие или противоречие СП.",
        "compliant_when": "Применимое аварийное решение предусмотрено и соответствует СП.",
        "unchecked_when": "Не установлено, требуется ли аварийное решение именно для данного объекта/участка.",
    },
    {
        "id": "ar_coordination",
        "name": "Координация с АР",
        "description": "Проверка согласованности санитарных приборов, помещений, стояков, выпусков и точек подключения между ВК и архитектурной частью.",
        "what_to_find": ["санитарные приборы", "помещения", "стояки", "точки подключения", "выпуски", "сравнение планов ВК и АР"],
        "fact_types": ["fixture", "room", "riser", "connection_point", "cross_section_match"],
        "parameters": ["санитарный прибор", "помещение", "стояк", "точка подключения", "выпуск"],
        "systems": ["wastewater", "water_supply"],
        "segments": ["internal"],
        "normative_documents": {"internal": ["СП 30.13330.2020"]},
        "requirement_type": ["cross_document_consistency", "presence", "semantic"],
        "numeric_comparison": False,
        "evidence_required": ["факт из ВК", "соответствующий факт из АР", "идентификатор помещения/оси/стояка", "оба листа при выявлении расхождения"],
        "violation_when": "Один и тот же объект/помещение однозначно имеет противоречащие друг другу решения ВК и АР.",
        "compliant_when": "Ключевые проверяемые элементы ВК и АР однозначно совпадают по назначению и расположению.",
        "unchecked_when": "Нельзя однозначно сопоставить элементы двух разделов или отсутствует необходимая часть АР.",
    },
]

_SKILLS: dict[str, dict[str, Any]] = {
    "vk_wastewater": {
        "id": "vk_wastewater",
        "code": "ВК",
        "name": "Система водоотведения",
        "description": "Экспертный профиль проверки внутреннего и наружного водоотведения с кросс-системными проверками только там, где они явно определены.",
        "normative_documents": ["СП 30.13330.2020", "СП 31.13330.2021", "СП 32.13330.2018"],
        "default_segment": "internal",
        "workflow": [
            "identify_system_and_segment",
            "extract_project_facts",
            "route_to_applicable_sp",
            "retrieve_normative_requirement",
            "compare_project_fact_with_requirement",
            "classify_violation_compliant_unchecked",
            "build_evidence_backed_remark",
        ],
        "classification": {
            "violation": "Только подтверждённое прямое несоответствие проектного факта конкретному применимому нормативному требованию.",
            "compliant": "Только подтверждённое прямое соответствие проектного факта конкретному применимому нормативному требованию.",
            "unchecked": "Недостаточно доказательств, нормативное условие не извлечено однозначно, либо сравнение требует предположения.",
        },
        "global_rules": {
            "never_infer_from_isolated_number": True,
            "never_use_unrelated_equipment_as_evidence": True,
            "never_route_all_checks_to_all_norms": True,
            "preserve_project_value_verbatim": True,
            "require_normative_clause_for_final_classification": True,
            "require_evidence_for_violation": True,
            "prefer_code_comparison_for_numeric_requirements": True,
        },
        "checks": _VK_WASTEWATER_CHECKS,
        "routing": {
            "internal_wastewater": ["СП 30.13330.2020"],
            "external_wastewater": ["СП 32.13330.2018"],
            "internal_water": ["СП 30.13330.2020"],
            "external_water": ["СП 31.13330.2021"],
            "cross_boundary_wastewater": ["СП 30.13330.2020", "СП 32.13330.2018"],
        },
        "cross_system_checks": ["irrigation", "meters", "ar_coordination"],
    }
}


def list_skills() -> list[dict[str, Any]]:
    """Return UI-safe complete Skill specifications in deterministic order."""
    return [deepcopy(skill) for skill in _SKILLS.values()]


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
