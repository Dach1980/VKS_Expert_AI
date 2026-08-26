"""
VKS Expert AI

Document Chunk Builder v6

Назначение:

Создание RAG chunks из нормативного документа.

Поддерживает:

- текстовые блоки
- формулы UniMERNet
- контекст формул

Pipeline:

PDF
 |
 PyMuPDF
 |
 pages/*.json
 |
 enriched pages
 |
 DocumentChunkBuilder
 |
 document_chunks/all_chunks.json
 |
 Embeddings
 |
 FAISS


Version:

v6
"""


import json
from pathlib import Path
from datetime import datetime
from collections import Counter



# ============================================================
# CONFIG
# ============================================================


INPUT_DIR = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index\SP_30.13330\enriched"
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



    # --------------------------------------------------------
    # LOAD PAGE
    # --------------------------------------------------------

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



    # --------------------------------------------------------
    # TEXT CHUNK
    # --------------------------------------------------------

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



        return {

            "chunk_id":
                f"{DOCUMENT}-page-{page:03}-text-{index:03}",


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
                    "text": text
                },


            "embedding_text":

                (
                    f"Документ: {self.document}. "
                    f"Версия: {self.version}. "
                    f"Страница: {page}. "
                    f"Тип: нормативный текст. "
                    f"Текст: {text}"
                ),


            "metadata":
                {
                    "source": "SP_30.13330",
                    "created":
                        datetime.now()
                        .isoformat()
                }

        }



    # --------------------------------------------------------
    # FIND FORMULA CONTEXT
    # --------------------------------------------------------

    def find_formula_context(
        self,
        blocks,
        formula
    ):


        formula_bbox = formula.get(
            "bbox"
        )


        if not formula_bbox:

            return "", ""



        formula_y = formula_bbox[1]


        before = ""

        after = ""


        candidates = []


        for block in blocks:


            text = (
                block.get(
                    "text",
                    ""
                )
                .strip()
            )


            if not text:

                continue



            bbox = block.get(
                "bbox"
            )


            if not bbox:

                continue



            y = bbox[1]


            distance = abs(
                y - formula_y
            )


            candidates.append(
                (
                    distance,
                    y,
                    text
                )
            )



        candidates.sort(
            key=lambda x: x[0]
        )



        for _, y, text in candidates:


            if y < formula_y:

                before = text

                break



        for _, y, text in candidates:


            if y > formula_y:

                after = text

                break



        return before, after



    # --------------------------------------------------------
    # FORMULA CHUNK
    # --------------------------------------------------------

    def build_formula_chunk(
        self,
        page,
        formula,
        blocks,
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
        )


        if isinstance(
            context,
            dict
        ):

            context_text = (
                context
                .get(
                    "nearest_text_block",
                    {}
                )
                .get(
                    "text",
                    ""
                )
            )

        else:

            context_text = context



        before, after = (
            self.find_formula_context(
                blocks,
                formula
            )
        )



        embedding_text = (

            f"Документ: {self.document}. "

            f"Версия: {self.version}. "

            f"Страница: {page}. "

            f"Раздел: определение расчетных расходов воды. "

            f"Тип: нормативная формула. "

            f"Контекст перед формулой: {before}. "

            f"Описание формулы: {context_text}. "

            f"Контекст после формулы: {after}. "

            f"Формула: {latex}"

        )



        return {

            "chunk_id":
                f"{DOCUMENT}-page-{page:03}-formula-{index:03}",


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

                    "context_before":
                        before,

                    "context":
                        context_text,

                    "context_after":
                        after,

                    "latex":
                        latex

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



    # --------------------------------------------------------
    # PAGE PROCESSING
    # --------------------------------------------------------

    def process_page(
        self,
        data
    ):


        page = data["page"]

        chunks = []



        blocks = (
            data.get(
                "text_blocks",
                []
            )
        )


        if not blocks:

            blocks = (
                data.get(
                    "blocks",
                    []
                )
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



        # FORMULAS

        formulas = (
            data.get(
                "formulas",
                []
            )
        )


        for i, formula in enumerate(
            formulas,
            start=1
        ):


            chunks.append(

                self.build_formula_chunk(

                    page,

                    formula,

                    blocks,

                    i

                )

            )



        return chunks



    # --------------------------------------------------------
    # ALL PAGES
    # --------------------------------------------------------

    def process_all_pages(
        self,
        input_dir
    ):


        all_chunks = []


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


            page = self.load_page(
                file
            )


            chunks = self.process_page(
                page
            )


            all_chunks.extend(
                chunks
            )



        return all_chunks



    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    def save(
        self,
        chunks
    ):


        output = Path(
            OUTPUT_DIR
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
        "Starting Document Chunk Builder v6..."
    )


    builder = DocumentChunkBuilder(

        DOCUMENT,

        VERSION

    )


    chunks = builder.process_all_pages(

        INPUT_DIR

    )


    builder.save(
        chunks
    )


    print(
        "DONE"
    )



if __name__ == "__main__":

    main()
    