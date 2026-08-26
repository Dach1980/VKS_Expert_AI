"""
VKS Expert AI
Page Enricher v2

Input:
knowledge/index/SP_30.13330/pages/page_xxx.json

Optional:
knowledge/work/formulas/page_xxx/page_xxx_formulas.json

Output:
knowledge/index/SP_30.13330/enriched/page_xxx_enriched.json
"""

import json
from pathlib import Path
from datetime import datetime


class PageEnricher:

    def __init__(
        self,
        pages_dir,
        formulas_dir,
        output_dir
    ):

        self.pages_dir = Path(pages_dir)
        self.formulas_dir = Path(formulas_dir)
        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )


    def load_json(self, path):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)


    def save_json(
        self,
        path,
        data
    ):

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )


    def load_formulas(
        self,
        page_number
    ):

        formula_file = (
            self.formulas_dir
            /
            f"page_{page_number:03d}"
            /
            f"page_{page_number:03d}_formulas.json"
        )


        if not formula_file.exists():

            return []


        data = self.load_json(
            formula_file
        )


        formulas = data.get(
            "formulas",
            []
        )


        return formulas



    def normalize_blocks(
        self,
        blocks
    ):

        result = []


        for block in blocks:

            text = block.get(
                "text",
                ""
            )


            if not text:
                continue


            text = text.strip()


            if not text:
                continue


            result.append(
                {
                    "id":
                        block.get(
                            "index"
                        ),

                    "bbox":
                        block.get(
                            "bbox"
                        ),

                    "text":
                        text
                }
            )


        return result



    def enrich_page(
        self,
        page_file
    ):


        page = self.load_json(
            page_file
        )


        page_number = page.get(
            "page"
        )


        print(
            f"Processing page_{page_number:03d}"
        )


        blocks = self.normalize_blocks(
            page.get(
                "blocks",
                []
            )
        )


        formulas = self.load_formulas(
            page_number
        )


        embedding_parts = []


        #
        # document metadata
        #

        embedding_parts.append(
            f"Документ: {page.get('document','')}"
        )


        embedding_parts.append(
            f"Страница: {page_number}"
        )


        #
        # text
        #

        for block in blocks:

            embedding_parts.append(
                block["text"]
            )


        #
        # formulas
        #

        for formula in formulas:

            latex = formula.get(
                "latex"
            )


            context = formula.get(
                "context",
                {}
            )


            if latex:

                embedding_parts.append(
                    f"Формула: {latex}"
                )


            nearest = (
                context
                .get(
                    "nearest_text_block"
                )
            )


            if nearest:

                txt = nearest.get(
                    "text",
                    ""
                )


                if txt:

                    embedding_parts.append(
                        f"Контекст формулы: {txt}"
                    )



        embedding_text = "\n\n".join(
            embedding_parts
        )


        enriched = {

            "document":
                page.get(
                    "document"
                ),

            "version":
                page.get(
                    "version"
                ),

            "page":
                page_number,


            "geometry":
                page.get(
                    "geometry"
                ),


            "source":
                {
                    "pipeline":
                        [
                            "PDFPageProcessor",
                            "FormulaExtractor",
                            "PageEnricher"
                        ]
                },


            "created":
                datetime.now()
                .isoformat(),


            "text_blocks":
                blocks,


            "formulas":
                formulas,


            "embedding_text":
                embedding_text
        }


        output = (
            self.output_dir
            /
            f"page_{page_number:03d}_enriched.json"
        )


        self.save_json(
            output,
            enriched
        )


        print(
            f"Saved: {output}"
        )


        return enriched



def main():


    print("="*70)
    print(
        "VKS Expert AI"
    )
    print(
        "Page Enricher v2"
    )
    print("="*70)


    base = Path(
        "knowledge/index/SP_30.13330"
    )


    enricher = PageEnricher(

        pages_dir =
            base / "pages",

        formulas_dir =
            Path(
                "knowledge/work/formulas"
            ),

        output_dir =
            base / "enriched"
    )


    pages = sorted(
        enricher.pages_dir.glob(
            "page_*.json"
        )
    )


    print(
        f"Pages found: {len(pages)}"
    )


    for page in pages:

        enricher.enrich_page(
            page
        )


    print()
    print("="*70)
    print(
        "DONE"
    )
    print("="*70)



if __name__ == "__main__":

    main()
    