"""
VKS Expert AI
Context Builder v1.0

Builds LLM-ready context from retriever results.
"""

from typing import List, Dict


class ContextBuilder:

    def __init__(
        self,
        max_context_chars: int = 12000
    ):
        self.max_context_chars = max_context_chars


    def build(
        self,
        results: List[Dict]
    ) -> str:

        blocks = []

        for r in results:

            source = r.get(
                "source",
                "unknown"
            )

            page = r.get(
                "page",
                "-"
            )

            doc = r.get(
                "document",
                ""
            )

            chunk_type = r.get(
                "type",
                "text"
            )


            if chunk_type == "formula_context":

                blocks.append(
                    self._build_formula_block(r)
                )

            else:

                blocks.append(
                    self._build_text_block(r)
                )


        context = "\n\n".join(blocks)

        return context[:self.max_context_chars]


    def _build_formula_block(
        self,
        item: Dict
    ) -> str:

        content = item.get(
            "content",
            {}
        )


        text = content.get(
            "text",
            ""
        )

        formula = content.get(
            "formula",
            ""
        )

        after = content.get(
            "after",
            ""
        )


        return f"""
Нормативная формула.

Страница:
{item.get('page')}

Контекст:

{text}


Формула:

$$
{formula}
$$


Продолжение:

{after}
"""


    def _build_text_block(
        self,
        item: Dict
    ) -> str:

        return f"""
Документ:
{item.get('document')}

Страница:
{item.get('page')}


Текст:

{item.get('content','')}
"""
    