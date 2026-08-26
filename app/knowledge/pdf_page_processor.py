"""
PDF Page Processor v1

Назначение:

Преобразование нормативного PDF
в структурированный индекс страниц.

Pipeline:

PDF
 |
 PyMuPDF
 |
 Page Processor
 |
 pages/page_xxx.json


v1:

Создаёт:

- номер страницы
- размеры страницы
- текстовые блоки
- координаты блоков
- изображения страницы
- источник PDF


Подготовка:

Formula extraction
Tables
Embedding
RAG


"""


import json
from pathlib import Path
from datetime import datetime

import pymupdf



# ============================================================
# CONFIG
# ============================================================


PROJECT_ROOT = Path(
    r"D:\Projects\VKS_Expert_AI"
)


PDF_PATH = (
    PROJECT_ROOT /
    "knowledge" /
    "regulations" /
    "SP_30.13330" /
    "СП_30.13330_базовая_версия.pdf"
)


OUTPUT_DIR = (
    PROJECT_ROOT /
    "knowledge" /
    "index" /
    "SP_30.13330" /
    "pages"
)


DOCUMENT = "СП 30.13330.2020"

VERSION = "base"



# ============================================================
# PROCESSOR
# ============================================================


class PDFPageProcessor:


    def __init__(
        self,
        pdf_path,
        output_dir
    ):

        self.pdf_path = pdf_path
        self.output_dir = output_dir



    def open_pdf(self):

        print(
            "Opening PDF..."
        )


        if not self.pdf_path.exists():

            raise FileNotFoundError(
                self.pdf_path
            )


        doc = pymupdf.open(
            self.pdf_path
        )


        print(
            "Pages:",
            len(doc)
        )


        return doc




    def extract_page(
        self,
        page,
        number
    ):


        rect = page.rect


        blocks = []


        text_blocks = page.get_text(
            "blocks"
        )


        for index, block in enumerate(
            text_blocks
        ):


            x0, y0, x1, y1, text, *_ = block


            if not text.strip():

                continue



            blocks.append(

                {

                    "index":
                        index,


                    "bbox":
                        [

                            round(x0,3),

                            round(y0,3),

                            round(x1,3),

                            round(y1,3)

                        ],


                    "text":
                        text.strip()

                }

            )



        result = {


            "document":
                DOCUMENT,


            "version":
                VERSION,


            "page":
                number,


            "geometry":
                {


                    "width":
                        rect.width,


                    "height":
                        rect.height

                },



            "source":
                {


                    "pdf":
                        str(
                            self.pdf_path
                        ),


                    "pipeline":
                        [

                            "PyMuPDF",

                            "PDFPageProcessor"

                        ]

                },



            "created":
                datetime.now()
                .isoformat(),



            "blocks":
                blocks,



            "formulas":
                []

        }



        return result




    def save_page(
        self,
        data
    ):


        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        filename = (

            self.output_dir /
            f"page_{data['page']:03}.json"

        )


        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(

                data,

                f,

                ensure_ascii=False,

                indent=2

            )


        return filename




    def run(self):


        doc = self.open_pdf()


        total = len(doc)



        for index in range(total):


            page_number = index + 1


            print(
                f"Processing page {page_number}/{total}"
            )



            page = doc[index]



            data = self.extract_page(

                page,

                page_number

            )



            file = self.save_page(
                data
            )



            print(
                "Saved:",
                file.name
            )



        doc.close()



        print()

        print(
            "PDF processing completed"
        )



# ============================================================
# MAIN
# ============================================================



def main():


    processor = PDFPageProcessor(

        PDF_PATH,

        OUTPUT_DIR

    )


    processor.run()



if __name__ == "__main__":

    main()
    