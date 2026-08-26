"""
Document Enricher v1

Объединение всех страниц нормативного документа.

Pipeline:

PDF
 |
PyMuPDF
 |
pages/page_xxx.json
 |
FormulaIndexer
 |
formulas/page_xxx_formulas.json
 |
PageEnricher
 |
enriched/page_xxx_enriched.json
 |
DocumentEnricher
 |
document.json


Назначение:

- собрать полный документ;
- объединить страницы;
- собрать формулы;
- подготовить metadata;
- подготовить основу для FAISS / Chroma.
"""


import json
from pathlib import Path
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


DOCUMENT = "СП 30.13330.2020"

VERSION = "base"


ENRICHED_DIR = (
    r"knowledge/index/SP_30.13330/enriched"
)


OUTPUT_DIR = (
    r"knowledge/index/SP_30.13330/document"
)


PDF_PATH = (
    r"knowledge/regulations/SP_30.13330/"
    r"СП_30.13330_базовая_версия.pdf"
)



# ============================================================
# CLASS
# ============================================================


class DocumentEnricher:


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



    def collect_pages(
        self,
        directory
    ):


        pages = []


        files = sorted(
            Path(directory)
            .glob(
                "page_*_enriched.json"
            )
        )


        for file in files:


            print(
                "Loading:",
                file.name
            )


            pages.append(
                self.load_json(
                    file
                )
            )


        return pages




    def build_document(
        self,
        pages
    ):


        formulas = []

        text_blocks = 0



        for page in pages:


            blocks = page.get(
                "text_blocks",
                []
            )


            text_blocks += len(
                blocks
            )


            for formula in page.get(
                "formulas",
                []
            ):


                formula_item = {


                    "id":
                        formula.get(
                            "id"
                        ),


                    "type":
                        "formula",


                    "page":
                        page.get(
                            "page"
                        ),


                    "latex":
                        formula.get(
                            "latex"
                        ),


                    "image":
                        formula.get(
                            "image"
                        ),


                    "bbox":
                        formula.get(
                            "bbox"
                        ),


                    "context":
                        formula.get(
                            "context"
                        ),


                    "embedding_text":
                        formula.get(
                            "embedding_text"
                        )

                }


                formulas.append(
                    formula_item
                )



        document = {


            "document":

                DOCUMENT,


            "version":

                VERSION,


            "source":

                {

                    "pdf":

                        PDF_PATH,


                    "pipeline":

                        [

                            "PyMuPDF",

                            "FormulaCrop",

                            "UniMERNet",

                            "FormulaIndexer",

                            "PageEnricher",

                            "DocumentEnricher"

                        ]

                },


            "created":

                datetime.now()
                .isoformat(),



            "statistics":

                {

                    "pages":

                        len(
                            pages
                        ),


                    "text_blocks":

                        text_blocks,


                    "formulas":

                        len(
                            formulas
                        )

                },



            "pages":

                pages,



            "formulas":

                formulas

        }


        return document



# ============================================================
# MAIN
# ============================================================


def main():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Document Enricher v1"
    )

    print("=" * 70)



    enricher = DocumentEnricher()



    pages = enricher.collect_pages(
        ENRICHED_DIR
    )


    print()

    print(
        "Pages loaded:",
        len(pages)
    )



    document = enricher.build_document(
        pages
    )



    print()

    print(
        "DOCUMENT SUMMARY"
    )


    print(
        json.dumps(
            document["statistics"],
            ensure_ascii=False,
            indent=2
        )
    )



    output = Path(
        OUTPUT_DIR
    ) / "document.json"



    enricher.save_json(
        document,
        output
    )



    print()

    print(
        "Saved:",
        output
    )


    print(
        "DONE"
    )



if __name__ == "__main__":

    main()
    