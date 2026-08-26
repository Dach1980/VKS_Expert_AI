"""
Formula Indexer v2

Назначение:

Берет результаты распознавания формул UniMERNet:

PDF page
    |
    ↓
Formula Crop
    |
    ↓
UniMERNet
    |
    ↓
page_xxx_formulas.json
    |
    ↓
FormulaIndexer
    |
    ↓
page_xxx.json


Подготовка для:

- FAISS
- ChromaDB
- RAG
- экспертной проверки проектной документации


Сохраняемые данные:

- документ
- версия СП
- страница
- координаты формулы
- изображение формулы
- LaTeX
- текстовый контекст
- источник PDF
- embedding text


"""


import json
from pathlib import Path
from datetime import datetime



# ============================================================
# CONFIG
# ============================================================


INPUT_JSON = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\work\formulas"
    r"\page_012"
    r"\page_012_formulas.json"
)


OUTPUT_DIR = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\index"
    r"\SP_30.13330"
    r"\pages"
)



PDF_SOURCE = (
    "knowledge/regulations/"
    "SP_30.13330/"
    "СП_30.13330_базовая_версия.pdf"
)


DOCUMENT_NAME = (
    "СП 30.13330.2020"
)


DOCUMENT_VERSION = (
    "base"
)



# ============================================================
# INDEXER
# ============================================================


class FormulaIndexer:


    def __init__(
        self,
        document,
        version,
        pdf_source
    ):

        self.document = document
        self.version = version
        self.pdf_source = pdf_source



    # --------------------------------------------------------

    def load_formula_json(
        self,
        path
    ):


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    # --------------------------------------------------------

    def extract_latex(
        self,
        item
    ):

        recognition = item.get(
            "recognition",
            {}
        )


        return (

            recognition.get(
                "latex"
            )

            or

            recognition.get(
                "pred_str"
            )

            or

            recognition.get(
                "raw"
            )

            or

            item.get(
                "latex"
            )

            or

            item.get(
                "text"
            )

        )


    # --------------------------------------------------------

    def extract_image(
        self,
        item
    ):

        return (

            item.get(
                "crop"
            )

            or

            item.get(
                "image"
            )

            or

            item.get(
                "path"
            )

        )


    # --------------------------------------------------------

    def build_page_index(
        self,
        data
    ):


        page_info = data.get(
            "page",
            {}
        )


        if isinstance(
            page_info,
            dict
        ):


            page_number = page_info.get(
                "number",
                0
            )


            geometry = {

                "width":
                    page_info.get(
                        "width"
                    ),


                "height":
                    page_info.get(
                        "height"
                    )

            }


        else:


            page_number = page_info

            geometry = None



        formulas = []



        for position, item in enumerate(
            data.get(
                "formulas",
                []
            ),
            start=1
        ):



            latex = self.extract_latex(
                item
            )


            image = self.extract_image(
                item
            )



            context = item.get(
                "context",
                {}
            )



            nearest_text = None



            if isinstance(
                context,
                dict
            ):


                block = context.get(
                    "nearest_text_block"
                )


                if block:

                    nearest_text = block.get(
                        "text"
                    )



            formula_id = (

                f"{self.document}"
                f"-page-{page_number:03}"
                f"-formula-{position:03}"

            )



            embedding_text = (

                f"{self.document}. "
                f"Страница {page_number}. "
                f"Формула нормативного документа. "

            )


            if nearest_text:


                embedding_text += (

                    "Контекст: "
                    + nearest_text

                )



            if latex:


                embedding_text += (

                    " Формула LaTeX: "
                    + latex

                )




            formula = {


                "chunk_id":

                    formula_id,



                "id":

                    formula_id,



                "type":

                    "formula",



                "document":

                    self.document,



                "version":

                    self.version,



                "page":

                    page_number,



                "location":

                    {


                        "pdf":

                            self.pdf_source,


                        "page":

                            page_number,


                        "bbox":

                            item.get(
                                "bbox"
                            )

                    },



                "bbox":

                    item.get(
                        "bbox"
                    ),



                "image":

                    image,



                "latex":

                    latex,



                "context":

                    nearest_text,



                "text_for_embedding":

                    embedding_text



            }



            formulas.append(
                formula
            )



        result = {



            "document":

                self.document,



            "version":

                self.version,



            "page":

                page_number,



            "geometry":

                geometry,



            "source":

                {


                    "pdf":

                        self.pdf_source,


                    "pipeline":

                        [

                            "PyMuPDF",

                            "FormulaCrop",

                            "UniMERNet",

                            "FormulaIndexer"

                        ]

                },



            "created":

                datetime.now()
                .isoformat(),



            "formulas":

                formulas



        }



        return result




    # --------------------------------------------------------

    def save(
        self,
        index,
        output_dir
    ):


        output_path = Path(
            output_dir
        )


        output_path.mkdir(
            parents=True,
            exist_ok=True
        )



        page = index.get(
            "page",
            0
        )



        filename = (

            f"page_{int(page):03}.json"

        )



        file_path = (

            output_path /
            filename

        )



        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as f:



            json.dump(

                index,

                f,

                ensure_ascii=False,

                indent=2

            )



        print(
            "Saved:",
            file_path
        )




# ============================================================
# MAIN
# ============================================================



def main():


    print(
        "Loading formula data..."
    )



    indexer = FormulaIndexer(

        DOCUMENT_NAME,

        DOCUMENT_VERSION,

        PDF_SOURCE

    )



    data = indexer.load_formula_json(
        INPUT_JSON
    )



    print(
        "Page:",
        data.get(
            "page"
        )
    )



    print(
        "Formulas:",
        len(
            data.get(
                "formulas",
                []
            )
        )
    )



    index = indexer.build_page_index(
        data
    )



    indexer.save(
        index,
        OUTPUT_DIR
    )



    print(
        "DONE"
    )




if __name__ == "__main__":

    main()
