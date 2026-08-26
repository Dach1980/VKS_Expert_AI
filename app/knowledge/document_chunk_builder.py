"""
VKS Expert AI

Document Chunk Builder v6

Назначение:

Создание RAG chunks из enriched нормативного документа.

Поддерживает:

- text_blocks
- formulas
- UniMERNet LaTeX recognition
- formula context
- formula images

Pipeline:

PDF
 |
PyMuPDF
 |
pages
 |
FormulaCrop
 |
UniMERNet
 |
enriched
 |
DocumentChunkBuilder
 |
document_chunks/all_chunks.json
 |
Embeddings
 |
FAISS
"""


import json
from pathlib import Path
from datetime import datetime
from collections import Counter



# ============================================================
# CONFIG
# ============================================================


BASE_DIR = Path(
    "knowledge/index/SP_30.13330"
)


INPUT_DIR = (
    BASE_DIR
    /
    "enriched"
)


OUTPUT_DIR = (
    BASE_DIR
    /
    "document_chunks"
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



    def load_json(
        self,
        file
    ):

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    # ========================================================
    # TEXT CHUNK
    # ========================================================


    def build_text_chunk(
        self,
        page,
        block,
        index
    ):


        text = block.get(
            "text",
            ""
        ).strip()


        if not text:

            return None



        chunk_id = (

            f"{self.document}"

            f"-page-{page:03}"

            f"-text-{index:03}"

        )



        embedding_text = (

            f"Документ: {self.document}. "

            f"Версия: {self.version}. "

            f"Страница: {page}. "

            f"Тип: нормативный текст. "

            f"Текст: {text}"

        )



        return {


            "chunk_id":
                chunk_id,


            "type":
                "text",



            "document":
                self.document,



            "version":
                self.version,



            "page":
                page,



            "content":
                {

                    "text":
                        text

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



    # ========================================================
    # FORMULA CHUNK
    # ========================================================


    def build_formula_chunk(
        self,
        page,
        formula,
        index
    ):


        latex = (

            formula
            .get(
                "recognition",
                {}
            )
            .get(
                "latex",
                ""
            )

        )



        context = (

            formula
            .get(
                "context",
                {}
            )
            .get(
                "nearest_text_block",
                {}
            )
            .get(
                "text",
                ""
            )

        )



        image = (

            formula
            .get(
                "crop",
                {}
            )
            .get(
                "path"
            )

        )



        if not latex and not context:

            return None



        chunk_id = (

            f"{self.document}"

            f"-page-{page:03}"

            f"-formula-{index:03}"

        )



        embedding_text = (

            f"Документ: {self.document}. "

            f"Версия: {self.version}. "

            f"Страница: {page}. "

            f"Тип: нормативная формула. "

            f"Контекст: {context}. "

            f"Формула: {latex}"

        )



        return {


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
                        image

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



    # ========================================================
    # PAGE PROCESS
    # ========================================================


    def process_page(
        self,
        data
    ):


        page = data["page"]


        chunks = []



        text_count = 0

        formula_count = 0



        # ----------------------------
        # TEXT
        # ----------------------------


        for index, block in enumerate(

            data.get(
                "text_blocks",
                []
            ),

            start=1

        ):


            chunk = self.build_text_chunk(

                page,

                block,

                index

            )


            if chunk:

                chunks.append(
                    chunk
                )

                text_count += 1




        # ----------------------------
        # FORMULAS
        # ----------------------------


        for index, formula in enumerate(

            data.get(
                "formulas",
                []
            ),

            start=1

        ):


            chunk = self.build_formula_chunk(

                page,

                formula,

                index

            )


            if chunk:

                chunks.append(
                    chunk
                )

                formula_count += 1



        if formula_count:


            print(

                f"page={page}: "

                f"text={text_count}, "

                f"formula={formula_count}"

            )


        return chunks




    # ========================================================
    # ALL PAGES
    # ========================================================


    def build(
        self
    ):


        files = sorted(

            INPUT_DIR.glob(

                "page_*_enriched.json"

            )

        )


        print(
            "Pages found:",
            len(files)
        )



        all_chunks = []



        for file in files:


            print(
                "Processing:",
                file.name
            )


            data = self.load_json(
                file
            )


            chunks = self.process_page(
                data
            )


            all_chunks.extend(
                chunks
            )



        return all_chunks




    # ========================================================
    # SAVE
    # ========================================================


    def save(
        self,
        chunks
    ):


        OUTPUT_DIR.mkdir(

            parents=True,

            exist_ok=True

        )


        output_file = (

            OUTPUT_DIR

            /

            "all_chunks.json"

        )



        with open(

            output_file,

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
            output_file
        )


        print(
            "Total chunks:",
            len(chunks)
        )


        print()

        print(
            "Chunk statistics:"
        )


        print(

            Counter(

                x["type"]

                for x in chunks

            )

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
        "Document Chunk Builder v6"
    )

    print(
        "=" * 70
    )



    builder = DocumentChunkBuilder(

        DOCUMENT,

        VERSION

    )



    chunks = builder.build()



    builder.save(
        chunks
    )



    print(
        "DONE"
    )




if __name__ == "__main__":

    main()
    