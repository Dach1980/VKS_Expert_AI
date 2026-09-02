"""Conservative LLM decision layer for engineering norm-control."""
from __future__ import annotations
import json
from typing import Any


def _json_object(client, prompt: str) -> dict[str, Any]:
    raw = client.chat(prompt, temperature=0.1, max_tokens=1200, enable_thinking=False)
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
    prompt = f"""Ты — инженер нормоконтроля проектной документации РФ. Проверь ОДИН визуально подтверждённый факт по приведённым фрагментам действующих нормативных документов.

ФАКТ ИЗ ПРОЕКТА:
{json.dumps(candidate, ensure_ascii=False)}

НОРМАТИВНЫЕ ФРАГМЕНТЫ:
{norm_text}

Главный принцип: сначала зафиксируй значение буквально как в исходнике, отдельно нормализуй его для машинного сравнения, затем сравнивай с нормой. Никогда не заменяй исходную запись нормализованной.

Алгоритм:
1) Найди конкретное обязательное/условное требование, относящееся именно к параметру.
2) Если проект содержит числовое значение, сравнивай число, единицу измерения и тип параметра отдельно.
3) Для таблиц учитывай название строки/параметра и контекст, чтобы не сравнить значение другой строки.
4) violation — ТОЛЬКО при прямом подтверждённом противоречии.
5) compliant — ТОЛЬКО при прямом подтверждённом соответствии.
6) Если нормативный фрагмент не содержит нужного требования или значение неоднозначно — unchecked.
7) Никогда не придумывай пункт, норму, значение, лист или текст.
8) norm, clause и normative_value должны быть взяты только из контекста.
9) project_value должен повторять исходное значение из ФАКТА ИЗ ПРОЕКТА. Не переписывай Ø110 в 110 мм и не меняй 0,02 на 0.02.
10) severity оценивай только для violation.

Верни ТОЛЬКО JSON:
{{
  "type":"violation|compliant|unchecked",
  "title":"конкретное название проверки",
  "description":"доказательное сопоставление без выдуманных данных",
  "recommendation":"конкретное действие или пусто",
  "sheet":"",
  "norm":"точное обозначение СП из контекста",
  "clause":"точный пункт из контекста",
  "parameter":"проверяемый параметр",
  "project_value":"буквальное значение из проекта",
  "project_unit":"единица проекта, если она явно видна",
  "normative_value":"значение/диапазон/условие из нормы, если оно явно есть",
  "normative_unit":"единица нормы",
  "comparison":"кратко: равно|в пределах|выше|ниже|не применимо|не определено",
  "severity":"critical|major|minor",
  "confidence":0.0
}}"""
    return _json_object(client, prompt)
