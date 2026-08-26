"""
Document Chunk Builder v1

Назначение:

Объединение всех элементов нормативного документа
в единый индекс для RAG.

Текущая версия:

Поддерживает:
    - FormulaIndexer output
    - Formula chunks

Подготовка:
    - FAISS
    - ChromaDB
    - Graph-RAG


Pipeline:

SP PDF
 |
 PyMuPDF
 |
 FormulaCrop
 |
 UniMERNet
 |
 FormulaIndexer
 |
 DocumentChunkBuilder
 |
 document_chunks.json


"""


import json
from pathlib import Path
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


INPUT_DIR = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index\SP_30.13330\pages"
)


OUTPUT_DIR = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index\SP_30.13330"
    r"\document_chunks"
)


DOCUMENT = "СП 30.13330.2020"

VERSION = "base"



# ============================================================
# BUILDER
# ============================================================


class DocumentChunkBuilder:


    def __init__(
        self,
        document,
        version
    ):

        self.document = document
        self.version = version



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



    def build_formula_chunk(
        self,
        page,
        formula
    ):


        chunk_id = (
            f"{self.document}"
            f"-page-{page:03}"
            f"-formula-"
            f"{formula['id'].split('-')[-1]}"
        )


        latex = formula.get(
            "latex"
        )


        context = formula.get(
            "context",
            ""
        )


        embedding_text = (

            f"Документ: {self.document}. "

            f"Версия: {self.version}. "

            f"Страница: {page}. "

            f"Тип: нормативная формула. "

            f"Контекст: {context}. "

        )


        if latex:

            embedding_text += (

                f" "

                f"Формула: "

                f"{latex}"

            )



        chunk = {


            "chunk_id":
                chunk_id,


            "type":
                "formula",



            "document":
                self.document,



            "version":
                self.version,



            "page":
                page,



            "content":
                {


                    "text":
                        context,


                    "latex":
                        latex,


                    "image":
                        formula.get(
                            "image"
                        )

                },



            "location":
                {


                    "pdf":
                        formula
                        .get(
                            "location",
                            {}
                        )
                        .get(
                            "pdf"
                        ),



                    "page":
                        page,



                    "bbox":
                        formula.get(
                            "bbox"
                        )

                },



            "embedding_text":
                embedding_text,



            "metadata":
                {


                    "source":
                        "SP_30.13330",



                    "created":
                        datetime.now()
                        .isoformat()



                }

        }


        return chunk




    def process_page(
        self,
        data
    ):


        page_number = data["page"]


        chunks = []


        for formula in data.get(
            "formulas",
            []
        ):


            chunk = self.build_formula_chunk(

                page_number,

                formula

            )


            chunks.append(
                chunk
            )


        return chunks




    def process_all_pages(
        self,
        input_dir
    ):


        all_chunks = []


        files = sorted(
            Path(input_dir)
            .glob(
                "page_*.json"
            )
        )


        print(
            "Pages found:",
            len(files)
        )


        for file in files:


            print(
                "Processing:",
                file.name
            )


            page_data = self.load_page(
                file
            )


            chunks = self.process_page(
                page_data
            )


            all_chunks.extend(
                chunks
            )


        return all_chunks




    def save(
        self,
        chunks,
        output_dir
    ):


        output = Path(
            output_dir
        )


        output.mkdir(
            parents=True,
            exist_ok=True
        )



        file = (
            output /
            "all_chunks.json"
        )


        with open(
            file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(

                chunks,

                f,

                ensure_ascii=False,

                indent=2

            )


        print()

        print(
            "Saved:",
            file
        )

        print(
            "Total chunks:",
            len(chunks)
        )



# ============================================================
# MAIN
# ============================================================


def main():


    print(
        "Starting Document Chunk Builder..."
    )


    builder = DocumentChunkBuilder(

        DOCUMENT,

        VERSION

    )


    chunks = builder.process_all_pages(

        INPUT_DIR

    )


    builder.save(

        chunks,

        OUTPUT_DIR

    )


    print(
        "DONE"
    )



if __name__ == "__main__":

    main()
    