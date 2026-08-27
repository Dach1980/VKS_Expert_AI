"""
VKS Expert AI

Document Chunk Builder v7

Formula Context Merge

Purpose:

Convert enriched PDF pages into RAG chunks.

Pipeline:

SP PDF
 |
PyMuPDF
 |
Enriched pages
 |
Text blocks
 |
Formula recognition
 |
Formula Context Merge
 |
all_chunks.json


Supports:

- text chunks
- formula_context chunks


Formula context:

TEXT BEFORE
+
FORMULA
+
TEXT AFTER

"""



import json

from pathlib import Path

from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


INPUT_DIR = (
    r"knowledge\index\SP_30.13330\enriched"
)


OUTPUT_DIR = (
    r"knowledge\index\SP_30.13330\document_chunks"
)



DOCUMENT = (
    "СП 30.13330.2020"
)



VERSION = (
    "base"
)




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




    # ---------------------------------------------------------


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




    # ---------------------------------------------------------


    def build_text_chunk(
        self,
        page,
        block,
        index
    ):


        text = (

            block.get(
                "text",
                ""
            )
            .strip()

        )


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




    # ---------------------------------------------------------
    # FORMULA CONTEXT
    # ---------------------------------------------------------


    def find_nearest_text(
        self,
        formula,
        blocks
    ):


        context_before = ""

        context_after = ""



        if not blocks:

            return (
                "",
                ""
            )



        formula_y = (

            formula
            .get(
                "bbox",
                [
                    0,
                    0,
                    0,
                    0
                ]
            )[1]

        )



        before = []

        after = []



        for block in blocks:


            bbox = block.get(
                "bbox",
                [
                    0,
                    0,
                    0,
                    0
                ]
            )


            text = block.get(
                "text",
                ""
            ).strip()



            if not text:

                continue



            y = bbox[3]



            if y <= formula_y:

                before.append(
                    (
                        y,
                        text
                    )
                )


            else:

                after.append(
                    (
                        y,
                        text
                    )
                )



        before.sort(
            key=lambda x:x[0],
            reverse=True
        )


        after.sort(
            key=lambda x:x[0]
        )



        if before:

            context_before = " ".join(
                x[1]
                for x in before[:3]
            )



        if after:

            context_after = " ".join(
                x[1]
                for x in after[:2]
            )



        return (

            context_before,

            context_after

        )




    # ---------------------------------------------------------


    def build_formula_context_chunk(
        self,
        page,
        formula,
        blocks,
        index
    ):



        recognition = (

            formula
            .get(
                "recognition",
                {}
            )

        )



        latex = (

            recognition
            .get(
                "latex",
                ""
            )

        )



        before, after = self.find_nearest_text(

            formula,

            blocks

        )



        if not latex:

            return None




        chunk_id = (

            f"{self.document}"
            f"-page-{page:03}"
            f"-formula-context-{index:03}"

        )



        embedding_text = (

            f"Документ: {self.document}. "

            f"Версия: {self.version}. "

            f"Страница: {page}. "

            f"Тип: нормативная формула. "

            f"Область: ВК. "

            f"Система: внутренний водопровод. "

            f"Тема: гидравлический расчет. "

            f"Нормативное описание: "

            f"{before}. "

            f"Формула: "

            f"{latex}. "

            f"Дополнительный текст: "

            f"{after}"

        )



        return {



            "chunk_id":

                chunk_id,



            "type":

                "formula_context",




            "document":

                self.document,



            "version":

                self.version,



            "page":

                page,



            "content":
            {

                "text":
                    (
                        before
                        +
                        "\n\nФормула: "
                        +
                        latex
                        +
                        "\n\n"
                        +
                        after
                    ),

                "formula":
                    latex,

                "before":
                    before,

                "after":
                    after,


                "engineering_context":
                {

                    "discipline":
                        "ВК",

                    "system":
                        "Внутренний водопровод",

                    "purpose":
                        before,

                    "calculation_type":
                        "Гидравлический расчет"

                }

            },




            "embedding_text":

                embedding_text,




        "metadata":

        {

            "source":

                "SP_30.13330",


            "formula":

                True,


            "discipline":

                "ВК",


            "system":

                "internal_water_supply",


            "topic":

                "hydraulic_calculation",


            "created":

                datetime.now()
                .isoformat()

        }


        }




    # ---------------------------------------------------------


    def process_page(
        self,
        data
    ):


        page = data["page"]



        chunks = []



        blocks = data.get(
            "text_blocks",
            []
        )



        # TEXT


        for i, block in enumerate(

            blocks,

            start=1

        ):



            chunk = self.build_text_chunk(

                page,

                block,

                i

            )



            if chunk:

                chunks.append(
                    chunk
                )




        # FORMULA CONTEXT


        formulas = data.get(
            "formulas",
            []
        )



        for i, formula in enumerate(

            formulas,

            start=1

        ):



            chunk = self.build_formula_context_chunk(

                page,

                formula,

                blocks,

                i

            )



            if chunk:

                chunks.append(
                    chunk
                )



        return chunks





    # ---------------------------------------------------------


    def process_all_pages(
        self,
        input_dir
    ):


        result = []



        files = sorted(

            Path(input_dir)
            .glob(
                "page_*_enriched.json"
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



            data = self.load_page(
                file
            )



            result.extend(

                self.process_page(
                    data
                )

            )



        return result




    # ---------------------------------------------------------


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

            output
            /
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
        "Starting Document Chunk Builder v7..."
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



    from collections import Counter



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


    print()

    print(
        "DONE"
    )




if __name__ == "__main__":

    main()
