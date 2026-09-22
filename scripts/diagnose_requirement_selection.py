"""Diagnostic for the audit retrieval -> normative requirement selection chain.

Diagnostic-only script. It reproduces the real baseline candidate and prints:
1. retrieve_audit_context() output;
2. select_normative_requirements() output;
3. the exact production _multi_context() filtering result.

No production code is modified.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.checking.resilient import _indexed_norms, _multi_context, _finalise_decision
from app.checking.audit_decision import decide_audit
from app.checking.table_check import build_table_check_row, deterministic_numeric_comparison
from app.knowledge.storage import KnowledgeStorage
from app.llm.lmstudio_client import LMStudioClient
from app.rag.audit_retrieval import retrieve_audit_context
from app.rag.normative_requirement import select_normative_requirements
from app.rag.normative_router import route_candidate
from app.rag.normative_router import filter_retrievers


CANDIDATE = {
    "parameter": "диаметр выпуска",
    "title": "Диаметры",
    "description": "Указан диаметр выпусков внутренней самотечной бытовой канализации.",
    "source_context": "Вводная часть раздела ВК о системе водоотведения.",
    "evidence_text": (
        "Бытовые стоки от приборов в санузлах и КУИ, от трапов технических и "
        "душевых помещений, а также от опорожнения сетей водоснабжения и отопления "
        "в количестве 3,58 л/с, 4,34 м³/ч, 8,48 м³/сут отводятся системой внутренней "
        "самотечной бытовой канализации по пяти выпускам Ø110мм в внутриплощадочную "
        "сеть бытовой канализации Ø160 мм."
    ),
    "project_value": "Ø110мм",
}


def dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def print_result(i: int, result: dict) -> None:
    print(f"\nRESULT #{i}")
    print(f"  page: {result.get('page')}")
    print(f"  score: {result.get('score')}")
    print(f"  source: {result.get('source')}")
    print(f"  type: {result.get('type')}")
    print(f"  chunk_id: {result.get('chunk_id')}")
    print(f"  norm_number: {result.get('norm_number')}")
    print(f"  version: {result.get('version')}")
    print(f"  metadata: {result.get('metadata')}")
    print("  content:")
    print(str(result.get("content", ""))[:1800])


def main() -> None:
    print("=== Requirement selection diagnostic ===")
    print(f"Repository root: {ROOT}")

    skill_id = "vk_wastewater"
    route = route_candidate(CANDIDATE, skill_id)
    print("\nROUTE:")
    dump(route)

    storage = KnowledgeStorage()
    norms = _indexed_norms(storage)
    print(f"\n_indexed_norms(): {len(norms)}")
    for document, version, _ in norms:
        print(
            f"  - {document.get('number')} ({document.get('id')})"
            f" -> {version.get('id')}"
        )

    scoped = filter_retrievers(norms, route)
    print(f"filter_retrievers(): {len(scoped)}")
    for document, version, _ in scoped:
        print(f"  - {document.get('number')} -> {version.get('id')}")

    print("\nSTEP 1: retrieve_audit_context()")
    results = retrieve_audit_context(
        norms,
        CANDIDATE,
        top_k=6,
        skill_id=skill_id,
    )
    print(f"RETRIEVED CONTEXT COUNT: {len(results)}")
    for i, result in enumerate(results, 1):
        print_result(i, result)

    print("\nSTEP 2: select_normative_requirements()")
    selected = select_normative_requirements(
        results,
        str(CANDIDATE.get("parameter") or ""),
        limit=4,
    )
    print(f"SELECTED REQUIREMENTS COUNT: {len(selected)}")
    for i, item in enumerate(selected, 1):
        print(f"\nREQUIREMENT #{i}")
        print(f"  norm: {item.get('norm')}")
        print(f"  version: {item.get('version')}")
        print(f"  clause: {item.get('clause')!r}")
        print(f"  requirement_relevance: {item.get('requirement_relevance')}")
        print(f"  has_concrete_clause: {item.get('has_concrete_clause')}")
        print(f"  has_numeric_rule: {item.get('has_numeric_rule')}")
        print(f"  operator: {item.get('operator')!r}")
        print(f"  normative_value: {item.get('normative_value')}")
        print(f"  normative_unit: {item.get('normative_unit')!r}")
        print(f"  page: {item.get('page')}")
        print(f"  metadata_text: {item.get('metadata_text')!r}")
        print("  requirement text:")
        print(str(item.get("requirement") or "")[:1800])

    print("\nSTEP 3: exact production _multi_context() filter")
    norm_text, production_requirements = _multi_context(results, CANDIDATE)
    print(f"PRODUCTION REQUIREMENTS COUNT: {len(production_requirements)}")
    for i, item in enumerate(production_requirements, 1):
        print(
            f"  #{i}: norm={item.get('norm')!r}, "
            f"clause={item.get('clause')!r}, "
            f"requirement_nonempty={bool(str(item.get('requirement') or '').strip())}"
        )

    print("\nSTEP 4: decide_audit()")
    print("Initializing chat client...")
    client = LMStudioClient()
    available_models = [
        str(item.get("id"))
        for item in client.get_models().get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    requested_model = str(os.getenv("LM_STUDIO_MODEL") or "").strip()
    model = requested_model if requested_model else client._select_chat_model({"data": [{"id": value} for value in available_models]})
    if model not in available_models:
        raise RuntimeError(f"LM Studio model is unavailable: {model}")
    client.model = model
    print(f"CHAT MODEL: {model}")
    decision = decide_audit(client, CANDIDATE, norm_text)
    print("DECISION FROM decide_audit():")
    dump(decision)



    print("\nSTEP 4A: raw decide_audit() request/response")
    captured = {}

    original_chat = client.chat

    def capture_chat(prompt, *args, **kwargs):
        captured["prompt"] = str(prompt)
        raw = original_chat(prompt, *args, **kwargs)
        captured["raw_response"] = str(raw or "")
        return raw

    client.chat = capture_chat
    decision = decide_audit(client, CANDIDATE, norm_text)
    client.chat = original_chat

    prompt_text = captured.get("prompt", "")
    raw_response = captured.get("raw_response", "")
    print(f"PROMPT LENGTH: {len(prompt_text)} chars")
    print("RAW LLM RESPONSE:")
    print(raw_response if raw_response else "<EMPTY>")
    print("PARSED DECISION:")
    dump(decision)

    print("\nSTEP 5A: isolated applicability matrix")
    applicability_prompt_template = """Ты проверяешь применимость ОДНОГО нормативного требования к ОДНОМУ факту проекта.
Верни ТОЛЬКО JSON:
{"applicable":"yes|no|unclear","reason":"кратко","missing_evidence":["..."]}

ФАКТ ПРОЕКТА:
{candidate}

НОРМАТИВНОЕ ТРЕБОВАНИЕ:
{requirement}

Правила:
- yes только если текст факта прямо относится к объекту/параметру требования и данных достаточно, чтобы утверждать применимость;
- no если требование явно относится к другому объекту, параметру или условию;
- unclear если связь возможна, но из факта не видно нужного объекта/условия;
- не считай совпадение одного общего слова (например, «диаметр») доказательством применимости.
"""
    applicability_matrix = []
    for i, requirement in enumerate(production_requirements, 1):
        isolated_prompt = applicability_prompt_template.format(
            candidate=json.dumps(CANDIDATE, ensure_ascii=False),
            requirement=json.dumps(
                {
                    "norm": requirement.get("norm"),
                    "clause": requirement.get("clause"),
                    "requirement": requirement.get("requirement"),
                    "operator": requirement.get("operator"),
                    "normative_value": requirement.get("normative_value"),
                    "normative_unit": requirement.get("normative_unit"),
                },
                ensure_ascii=False,
            ),
        )
        raw = original_chat(
            isolated_prompt,
            temperature=0.1,
            max_tokens=500,
            enable_thinking=False,
        )
        raw_text = str(raw or "").strip()
        parsed = {}
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            start, end = raw_text.find("{"), raw_text.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(raw_text[start:end + 1])
                except json.JSONDecodeError:
                    parsed = {}
        row = {
            "index": i,
            "clause": requirement.get("clause"),
            "requirement": requirement.get("requirement"),
            "applicable": parsed.get("applicable") if isinstance(parsed, dict) else None,
            "reason": parsed.get("reason") if isinstance(parsed, dict) else "",
            "missing_evidence": parsed.get("missing_evidence") if isinstance(parsed, dict) else [],
            "raw_response": raw_text,
        }
        applicability_matrix.append(row)
        print(f"\nREQUIREMENT #{i} / clause {requirement.get('clause')}")
        print(f"  applicable: {row['applicable']!r}")
        print(f"  reason: {row['reason']!r}")
        print(f"  missing_evidence: {row['missing_evidence']!r}")
        print(f"  raw_response: {raw_text!r}")

    print("\nAPPLICABILITY MATRIX:")
    dump(applicability_matrix)

    print("\nSTEP 5: deterministic_numeric_comparison()")
    compared = deterministic_numeric_comparison(CANDIDATE, decision, production_requirements)
    print("DECISION AFTER deterministic_numeric_comparison():")
    dump(compared)
    print(f"  type: {compared.get('type')!r}")
    print(f"  norm: {compared.get('norm')!r}")
    print(f"  clause: {compared.get('clause')!r}")
    print(f"  project_value: {compared.get('project_value')!r}")
    print(f"  normative_value: {compared.get('normative_value')!r}")
    print(f"  comparison: {compared.get('comparison')!r}")

    print("\nSTEP 6: _finalise_decision()")
    final_decision = _finalise_decision(compared, CANDIDATE, production_requirements)
    print("FINAL DECISION:")
    dump(final_decision)
    print(f"  type: {final_decision.get('type')!r}")
    print(f"  norm: {final_decision.get('norm')!r}")
    print(f"  clause: {final_decision.get('clause')!r}")
    print(f"  normative_requirement_nonempty: {bool(str(final_decision.get('normative_requirement') or '').strip())}")

    print("\nSTEP 7: build_table_check_row()")
    table_row = build_table_check_row(CANDIDATE, final_decision, 1, results)
    print("TABLE CHECK ROW:")
    dump(table_row.to_dict())

    print("\nPRODUCTION NORM TEXT:")
    print(norm_text[:8000] if norm_text else "<EMPTY>")

    print("\nFINAL DIAGNOSTIC:")
    if not results:
        print("FAILURE_STAGE=retrieve_audit_context")
    elif not selected:
        print("FAILURE_STAGE=select_normative_requirements")
    elif not production_requirements:
        print("FAILURE_STAGE=_multi_context_production_filter")
    elif not isinstance(decision, dict):
        print("FAILURE_STAGE=decide_audit")
    elif not isinstance(compared, dict):
        print("FAILURE_STAGE=deterministic_numeric_comparison")
    elif not isinstance(final_decision, dict):
        print("FAILURE_STAGE=_finalise_decision")
    else:
        print("FAILURE_STAGE=after_table_check_row")
        print("Steps 1-7 returned data without modifying production logic.")

if __name__ == "__main__":
    main()
