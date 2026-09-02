"""Expert report contract for the VK wastewater checking Skill.

This is deliberately a data contract rather than a presentation-only prompt.
The checker must produce findings that can be rendered into the same logical
shape as the expert source report and each finding must keep a stable evidence
number shared by the remark and its annotated image.
"""
from __future__ import annotations

VK_REPORT_SPEC = {
    "title": "ОТЧЁТ ПО НОРМОКОНТРОЛЮ ПРОЕКТНОЙ ДОКУМЕНТАЦИИ",
    "profile": "Система водоотведения",
    "sections": [
        "1. Область и нормативная база",
        "2. Заключение",
        "3. Перечень замечаний",
        "4. Доказательства по замечаниям",
        "5. Результаты, требующие экспертной проверки",
        "6. Нормативные источники",
    ],
    "remark_contract": [
        "id",
        "number",
        "title",
        "severity",
        "sheet",
        "page",
        "parameter",
        "project_value",
        "normative_requirement",
        "norm",
        "clause",
        "description",
        "recommendation",
        "evidence_text",
        "evidence_image",
        "bbox",
    ],
    "remark_style": {
        "title": "Кратко и предметно сформулированное несоответствие, без слов 'требует проверки' в подтверждённом замечании.",
        "description": "Сначала факт проекта, затем конкретное требование СП, затем логическое сравнение. Не добавлять сведения, которых нет в проекте или retrieved-норме.",
        "recommendation": "Конкретное действие проектировщика для устранения замечания.",
        "citation": "Обязательно точное обозначение СП и пункт. Если точный пункт не найден в RAG, нарушение не подтверждать.",
    },
    "evidence_contract": {
        "one_to_one": True,
        "rule": "Номер замечания N обязан совпадать с номером изображения N. Одно изображение должно показывать именно тот фрагмент, на котором основано замечание.",
        "bbox": "Красная рамка только вокруг реального доказательного фрагмента: строки таблицы, обозначения, размера, участка схемы или текста.",
        "no_blank_regions": True,
    },
}

# The visual model is not allowed to turn arbitrary OCR into a finding.
# These are high-value VK signals; everything else is rejected unless it is
# explicitly tied to one of them by the page context.
VK_HIGH_VALUE_SIGNALS = {
    "wastewater_flow": ("расчётный расход", "расход сточных вод", "Qк", "л/с", "м3/сут", "м³/сут"),
    "sewer_diameter": ("канализац", "К1", "К2", "К3", "К1-", "К2-", "Ø", "DN"),
    "sewer_slope": ("уклон", "i=", "i =", "продольн"),
    "sewer_ventilation": ("вентиляц", "вытяжн", "фанов", "стояк", "выше кровли"),
    "sewer_outlets": ("выпуск", "К1-", "К2-", "из здания"),
    "sewer_cleanouts": ("ревиз", "прочист", "доступ"),
    "sewer_material": ("материал труб", "полипропилен", "ПП", "ПВХ", "чугун", "сталь", "полиэтилен"),
    "storm_separation": ("дождевая", "ливнев", "бытовая канализац", "раздель", "К1", "К2"),
    "noise_insulation": ("шумоизоляц", "звукоизоляц", "шум", "звукоизол"),
    "irrigation": ("поливоч", "кран", "мойка", "уборка"),
    "meters": ("водомер", "водомерный узел", "счётчик", "счетчик", "прибор учёта", "узел учёта"),
    "emergency_outlets": ("аварийн", "аварийный выпуск", "аварийный сброс"),
    "ar_coordination": ("санитарн", "унитаз", "раковин", "мойка", "АР", "план этажа"),
}

# Text which is commonly OCR'ed from unrelated objects on engineering plans.
VK_ALWAYS_REJECT_AS_STANDALONE = (
    "секционные ворота",
    "ворота",
    "связь металлическая",
    "установка пожаротушения",
    "пожаротушение",
    "футляр ст.",
    "производственный корпус",
    "штамп",
)
