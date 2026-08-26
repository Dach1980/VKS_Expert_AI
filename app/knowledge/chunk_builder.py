"""
Chunk Builder

Назначение:

Берет индекс страниц СП:
    FormulaIndexer output

Создает RAG chunks:

    page formula
        |
        v
    chunk

Подготовка:
    - FAISS
    - ChromaDB
    - Graph-RAG


Input:

knowledge/index/SP_30.13330/pages/page_012.json


Output:

knowledge/index/SP_30.13330/chunks/page_012_chunks.json

"""


import json
from pathlib import Path
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


INPUT_JSON = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index\SP_30.13330"
    r"\pages\page_012.json"
)


OUTPUT_DIR = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index\SP_30.13330"
    r"\chunks"
)



# ============================================================
# CHUNK BUILDER
# ============================================================


class ChunkBuilder:


    def __init__(
        self,
        document,
        version
    ):

        self.document = document
        self.version = version



    def load(
        self,
        path
    ):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    def build_chunks(
        self,
        page_index
    ):


        chunks = []


        page = page_index["page"]


        for formula in page_index.get(
            "formulas",
            []
        ):


            chunk_id = (
                f"{self.document}"
                f"-page-{page:03}"
                f"-formula-{formula['id'].split('-')[-1]}"
            )



            latex = formula.get(
                "latex"
            )



            context = formula.get(
                "context",
                ""
            )



            bbox = formula.get(
                "bbox"
            )



            image = formula.get(
                "image"
            )


            pdf = (
                formula
                .get(
                    "location",
                    {}
                )
                .get(
                    "pdf"
                )
            )



            embedding_text = (

                f"Документ: {self.document}. "

                f"Версия: {self.version}. "

                f"Страница: {page}. "

                f"Нормативная формула. "

                f"Контекст: {context}. "

            )


            if latex:

                embedding_text += (

                    f" "

                    f"Математическое выражение: "

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



                "location":
                    {

                        "pdf":
                            pdf,


                        "page":
                            page,


                        "bbox":
                            bbox

                    },



                "content":
                    {

                        "context":
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


            chunks.append(
                chunk
            )


        return chunks




    def save(
        self,
        chunks,
        output_dir,
        page
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
            f"page_{page:03}_chunks.json"
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



        print(
            "Saved:",
            file
        )




# ============================================================
# MAIN
# ============================================================



def main():


    print(
        "Loading page index..."
    )


    builder = ChunkBuilder(

        "СП 30.13330.2020",

        "base"

    )



    page_index = builder.load(
        INPUT_JSON
    )



    print(
        "Page:",
        page_index["page"]
    )


    chunks = builder.build_chunks(
        page_index
    )


    print(
        "Chunks:",
        len(chunks)
    )



    builder.save(

        chunks,

        OUTPUT_DIR,

        page_index["page"]

    )



    print(
        "DONE"
    )





if __name__ == "__main__":

    main()
    