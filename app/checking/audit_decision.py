"""Conservative LLM decision layer for engineering norm-control."""
from __future__ import annotations
import json
from typing import Any


def _json_object(client, prompt: str) -> dict[str, Any]:
    raw = client.chat(prompt, temperature=0.1, max_tokens=1400, enable_thinking=False)
    text = str(raw or "").strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start:end + 1])
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def decide_audit(client, candidate: dict[str, Any], norm_text: str) -> dict[str, Any]:
    prompt = f"""Ты — эксперт по нормоконтролю проектной документации РФ. Проверь ОДИН отобранный факт ВК по приведённым фрагментам действующих нормативных документов.

ФАКТ ИЗ ПРОЕКТА:
{json.dumps(candidate, ensure_ascii=False)}

НОРМАТИВНЫЕ ФРАГМЕНТЫ:
{norm_text}

Сначала реши, является ли кандидат действительно предметом инженерной проверки ВК. Если это название проекта, штамп, ворота, металлоконструкция, пожаротушение, футляр без связи с канализационной трубой, случайный размер, случайная надпись или другой нерелевантный объект — верни type=unchecked.

ЦЕЛЬ: получать замечания в экспертной форме, а не каталог найденных чисел.

ПОРЯДОК:
1. Определи систему и участок: внутренняя канализация, наружная канализация, внутренний водосток, наружная дождевая сеть и т.п.
2. Выбери только применимый СП из нормативного маршрута. Не используй СП другого сегмента только потому, что его текст оказался похожим.
3. Найди конкретное обязательное или условное требование. Для подтверждённого результата обязательно нужен точный пункт нормы.
4. Для численного требования сравни число, единицу, тип параметра и условие применения. Если требование табличное/условное и входных данных недостаточно — unchecked.
5. Для проверки отсутствия решения требуй доказательство того, что решение обязательно и что проектная часть, где оно должно быть, действительно просмотрена.
6. Старую ссылку на СП проверяй отдельно и только если она явно используется как нормативная база проекта.
7. Не смешивай дождевые расходы с хозяйственно-бытовой канализацией.
8. Не смешивай диаметры, уклоны, материалы и вентиляцию.
9. violation — только прямое подтверждённое несоответствие.
10. compliant — только прямое подтверждённое соответствие.
11. unchecked — всё, что нельзя доказать без предположения.

ФОРМАТ ПОДТВЕРЖДЁННОГО ЗАМЕЧАНИЯ:
- title: краткое предметное нарушение.
- description: факт проекта → точное требование СП → логическое сравнение.
- recommendation: конкретное действие проектировщика.
- project_value: буквальная запись из проекта.
- normative_value: значение/условие из нормы.
- norm + clause: только из retrieved context.

Верни ТОЛЬКО JSON:
{{"type":"violation|compliant|unchecked","title":"","description":"","recommendation":"","sheet":"","norm":"","clause":"","parameter":"","project_value":"","project_unit":"","normative_value":"","normative_unit":"","comparison":"равно|в пределах|выше|ниже|не применимо|не определено","severity":"critical|major|minor","confidence":0.0}}"""
    return _json_object(client, prompt)
