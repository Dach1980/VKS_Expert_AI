"""Conservative LLM decision layer for engineering norm-control."""
from __future__ import annotations
import json
from typing import Any

def _json_object(client, prompt: str) -> dict[str, Any]:
    raw=client.chat(prompt,temperature=0.1,max_tokens=1000,enable_thinking=False)
    text=str(raw or "").strip()
    try:
        value=json.loads(text)
        return value if isinstance(value,dict) else {}
    except json.JSONDecodeError:
        start=text.find("{"); end=text.rfind("}")
        if start>=0 and end>start:
            try:
                value=json.loads(text[start:end+1]); return value if isinstance(value,dict) else {}
            except json.JSONDecodeError:return {}
        return {}

def decide_audit(client, candidate:dict[str,Any], norm_text:str)->dict[str,Any]:
    prompt=f"""Ты — инженер нормоконтроля проектной документации РФ. Проверь ОДИН визуально подтверждённый факт по приведённым фрагментам действующих нормативных документов.

ФАКТ ИЗ ПРОЕКТА:
{json.dumps(candidate,ensure_ascii=False)}

НОРМАТИВНЫЕ ФРАГМЕНТЫ:
{norm_text}

Алгоритм:
1) Найди в нормативных фрагментах конкретное обязательное/условное требование, относящееся именно к факту.
2) Сопоставь фактическое значение, наличие/отсутствие элемента или проектное решение с этим требованием.
3) violation ставь ТОЛЬКО при прямом подтверждении противоречия. Если нужный пункт не найден, ставь unchecked.
4) compliant ставь только при прямом подтверждении соответствия. Иначе unchecked.
5) Никогда не придумывай номер пункта, норматив, значение, лист или отсутствующий в контексте текст.
6) Для violation обязательно сформулируй цепочку: «в проекте ...; норма требует ...; следовательно ...».
7) norm и clause должны быть взяты из предоставленного контекста, а не из памяти модели.
8) severity: critical — существенное влияние на безопасность/работоспособность; major — значимое нормативное несоответствие; minor — локальное/малозначимое.
9) Если проектный факт недостаточно однозначен или нормативный фрагмент нерелевантен — unchecked.

Верни ТОЛЬКО JSON:
{{"type":"violation|compliant|unchecked","title":"конкретное название замечания","description":"доказательное сопоставление факта и нормы","recommendation":"конкретное действие","sheet":"","norm":"точное обозначение СП из контекста","clause":"точный пункт из контекста","severity":"critical|major|minor","confidence":0.0}}
"""
    return _json_object(client,prompt)
