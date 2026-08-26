"""
SP Index Builder v1

Главный pipeline построения индекса нормативного документа.

Назначение:

Полный цикл обработки СП:

PDF
 |
 PyMuPDF
 |
 Page extraction
 |
 Formula recognition
 |
 Formula indexing
 |
 Document chunks
 |
 RAG preparation


Версия v1:

Поддерживает:
- PDF страницы
- существующие page json
- формулы
- сбор chunks


Подготовка:
- FAISS
- ChromaDB
- Graph-RAG


"""


from pathlib import Path
import json
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


PROJECT_ROOT = Path(
    r"D:\Projects\VKS_Expert_AI"
)


DOCUMENT_NAME = (
    "СП 30.13330.2020"
)


VERSION = "base"



PDF_PATH = (

    PROJECT_ROOT /
    "knowledge" /
    "regulations" /
    "SP_30.13330" /
    "СП_30.13330_базовая_версия.pdf"

)



PAGES_DIR = (

    PROJECT_ROOT /
    "knowledge" /
    "index" /
    "SP_30.13330" /
    "pages"

)



CHUNKS_DIR = (

    PROJECT_ROOT /
    "knowledge" /
    "index" /
    "SP_30.13330" /
    "document_chunks"

)



# ============================================================
# BUILDER
# ============================================================


class SPIndexBuilder:



    def __init__(
        self,
        pdf,
        pages_dir,
        chunks_dir
    ):

        self.pdf = pdf
        self.pages_dir = pages_dir
        self.chunks_dir = chunks_dir



    def check_pdf(self):

        print(
            "Checking PDF..."
        )


        if not self.pdf.exists():

            raise FileNotFoundError(
                f"PDF not found: {self.pdf}"
            )


        print(
            "PDF:",
            self.pdf.name
        )



    def collect_pages(self):

        print()

        print(
            "Searching page indexes..."
        )


        files = sorted(
            self.pages_dir.glob(
                "page_*.json"
            )
        )


        print(
            "Pages found:",
            len(files)
        )


        return files



    def load_page(
        self,
        file
    ):


        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    def build_summary(
        self,
        pages
    ):


        summary = {


            "document":
                DOCUMENT_NAME,


            "version":
                VERSION,


            "source":
                {

                    "pdf":
                        str(
                            self.pdf
                        )

                },


            "statistics":
                {

                    "pages":
                        len(pages),


                    "formulas":
                        0


                },


            "created":
                datetime.now()
                .isoformat()


        }



        formulas = 0



        for file in pages:

            data = self.load_page(
                file
            )


            formulas += len(
                data.get(
                    "formulas",
                    []
                )
            )



        summary["statistics"]["formulas"] = formulas


        return summary




    def save_summary(
        self,
        summary
    ):


        self.chunks_dir.mkdir(

            parents=True,

            exist_ok=True

        )


        file = (

            self.chunks_dir /
            "index_summary.json"

        )



        with open(
            file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(

                summary,

                f,

                ensure_ascii=False,

                indent=2

            )



        print()

        print(
            "Saved summary:",
            file
        )



# ============================================================
# MAIN
# ============================================================



def main():


    print(
        "=" * 70
    )


    print(
        "VKS Expert AI"
    )


    print(
        "SP Index Builder v1"
    )


    print(
        "=" * 70
    )



    builder = SPIndexBuilder(

        PDF_PATH,

        PAGES_DIR,

        CHUNKS_DIR

    )



    builder.check_pdf()



    pages = builder.collect_pages()



    if not pages:

        print()

        print(
            "No page indexes found."
        )

        print(
            "Run page extraction pipeline first."
        )

        return



    summary = builder.build_summary(
        pages
    )



    print()

    print(
        "INDEX SUMMARY"
    )


    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2
        )
    )



    builder.save_summary(
        summary
    )



    print()

    print(
        "DONE"
    )





if __name__ == "__main__":

    main()
    