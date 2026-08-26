"""
Batch Page Enricher v1

Массовое обогащение страниц нормативного документа.

Pipeline:

pages/
 |
 | page_001.json
 | page_002.json
 |
 v

formulas/
 |
 | page_001_formulas.json
 | page_002_formulas.json
 |
 v

PageEnricher

 |
 v

enriched/

 page_001_enriched.json
 page_002_enriched.json


"""


import json
from pathlib import Path
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


PAGES_DIR = Path(
    r"knowledge/index/SP_30.13330/pages"
)


FORMULAS_DIR = Path(
    r"knowledge/work/formulas"
)


OUTPUT_DIR = Path(
    r"knowledge/index/SP_30.13330/enriched"
)



# ============================================================
# PAGE ENRICHER
# ============================================================


class BatchPageEnricher:


    def load_json(
        self,
        path
    ):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    def save_json(
        self,
        data,
        path
    ):

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )


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



    def find_formula_file(
        self,
        page_number
    ):


        folder = (
            FORMULAS_DIR /
            f"page_{page_number:03}"
        )


        file = (
            folder /
            f"page_{page_number:03}_formulas.json"
        )


        if file.exists():

            return file


        return None



    def build_embedding_text(
        self,
        page,
        formulas
    ):


        texts = []


        for block in page.get(
            "text_blocks",
            []
        ):


            text = block.get(
                "text",
                ""
            )


            if text:

                texts.append(
                    text
                )



        for formula in formulas:


            latex = formula.get(
                "latex"
            )


            if latex:

                texts.append(
                    "Formula: " + latex
                )



        return "\n".join(
            texts
        )



    def enrich_page(
        self,
        page,
        formulas_data
    ):


        formulas = []


        for item in formulas_data.get(
            "formulas",
            []
        ):


            formulas.append(

                {

                    "id":
                        item.get(
                            "id"
                        ),


                    "type":
                        "formula",


                    "page":
                        page.get(
                            "page"
                        ),


                    "bbox":
                        item.get(
                            "bbox"
                        ),


                    "latex":
                        item.get(
                            "latex"
                        ),


                    "image":
                        item.get(
                            "image"
                        ),


                    "context":
                        item.get(
                            "context"
                        )

                }

            )



        result = {


            "document":

                page.get(
                    "document"
                ),


            "page":

                page.get(
                    "page"
                ),



            "geometry":

                page.get(
                    "geometry"
                ),



            "source":

                {

                    "pipeline":

                        [

                            "PyMuPDF",

                            "FormulaCrop",

                            "UniMERNet",

                            "PageEnricher"

                        ]

                },


            "created":

                datetime.now()
                .isoformat(),



            "text_blocks":

                page.get(
                    "text_blocks",
                    []
                ),



            "formulas":

                formulas,



            "embedding_text":

                self.build_embedding_text(
                    page,
                    formulas
                )

        }


        return result



# ============================================================
# MAIN
# ============================================================


def main():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Batch Page Enricher v1"
    )

    print("=" * 70)



    enricher = BatchPageEnricher()



    pages = sorted(
        PAGES_DIR.glob(
            "page_*.json"
        )
    )



    print()

    print(
        "Pages found:",
        len(pages)
    )



    processed = 0

    formulas_count = 0



    for page_file in pages:


        page_number = int(
            page_file.stem.split("_")[1]
        )


        print()

        print(
            "Processing:",
            page_file.name
        )



        page = enricher.load_json(
            page_file
        )



        formula_file = (
            enricher.find_formula_file(
                page_number
            )
        )



        if formula_file:


            formulas_data = (
                enricher.load_json(
                    formula_file
                )
            )


            formulas_count += len(
                formulas_data.get(
                    "formulas",
                    []
                )
            )


        else:


            formulas_data = {

                "formulas": []

            }



        result = enricher.enrich_page(
            page,
            formulas_data
        )



        output = (

            OUTPUT_DIR /

            f"page_{page_number:03}_enriched.json"

        )



        enricher.save_json(
            result,
            output
        )


        print(
            "Saved:",
            output.name
        )


        processed += 1



    print()

    print("=" * 70)

    print(
        "SUMMARY"
    )

    print("=" * 70)



    print(
        "Pages processed:",
        processed
    )


    print(
        "Formulas:",
        formulas_count
    )


    print()

    print(
        "DONE"
    )



if __name__ == "__main__":

    main()
    