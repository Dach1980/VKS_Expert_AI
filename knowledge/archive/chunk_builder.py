"""
VKS Expert AI
Chunk Builder v2

Purpose:
Build semantic chunks from processed PDF pages.

Pipeline:

pages/*.json
      |
      v
text blocks + formulas
      |
      v
semantic chunks
      |
      v
embedding_text
      |
      v
document_chunks/all_chunks.json
"""


from pathlib import Path
import json
from datetime import datetime



DOCUMENT = "SP_30.13330"


BASE_DIR = (
    Path("knowledge/index")
    / DOCUMENT
)


PAGES_DIR = (
    BASE_DIR
    / "pages"
)


OUTPUT_DIR = (
    BASE_DIR
    / "document_chunks"
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "all_chunks.json"
)



MAX_TEXT_LENGTH = 1200



def load_pages():

    print("Loading pages...")


    pages = []


    files = sorted(
        PAGES_DIR.glob(
            "page_*.json"
        )
    )


    for file in files:

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            pages.append(
                json.load(f)
            )


    print(
        f"Pages loaded: {len(pages)}"
    )


    return pages



def normalize_text(text):

    if not text:
        return ""


    return (
        text
        .replace("\n", " ")
        .replace("  ", " ")
        .strip()
    )



def build_embedding_text(
    page,
    content
):

    result = []


    result.append(
        f"Документ: {page.get('document')}"
    )


    result.append(
        f"Версия: {page.get('version')}"
    )


    result.append(
        f"Страница: {page.get('page')}"
    )


    result.append("")


    result.append(
        content
    )


    return "\n".join(
        result
    )



def split_text(text):

    if len(text) <= MAX_TEXT_LENGTH:
        return [
            text
        ]


    chunks = []


    current = ""


    for sentence in text.split("."):

        sentence = sentence.strip()


        if not sentence:
            continue


        if (
            len(current)
            +
            len(sentence)
            <
            MAX_TEXT_LENGTH
        ):

            current += (
                sentence
                +
                ". "
            )

        else:

            chunks.append(
                current.strip()
            )


            current = (
                sentence
                +
                ". "
            )


    if current:

        chunks.append(
            current.strip()
        )


    return chunks



def process_page(
    page
):

    chunks = []


    page_number = page.get(
        "page"
    )


    blocks = page.get(
        "blocks",
        []
    )


    formulas = page.get(
        "formulas",
        []
    )


    #
    # TEXT BLOCKS
    #

    text_parts = []


    for block in blocks:

        text = normalize_text(
            block.get(
                "text",
                ""
            )
        )


        if text:

            text_parts.append(
                text
            )


    full_text = (
        " "
        .join(text_parts)
    )


    for index, part in enumerate(
        split_text(full_text)
    ):


        chunks.append(
            {
                "chunk_id":
                    f"{DOCUMENT}-page-{page_number:03d}-text-{index:03d}",


                "type":
                    "text",


                "document":
                    page.get(
                        "document"
                    ),


                "version":
                    page.get(
                        "version"
                    ),


                "page":
                    page_number,


                "content":
                    part,


                "embedding_text":
                    build_embedding_text(
                        page,
                        part
                    ),


                "metadata":
                    {
                        "source":
                            DOCUMENT,

                        "created":
                            datetime.now()
                            .isoformat()
                    }
            }
        )



    #
    # FORMULAS
    #

    for index, formula in enumerate(
        formulas
    ):

        context = normalize_text(
            formula.get(
                "embedding_text",
                ""
            )
        )


        if not context:

            continue


        chunks.append(
            {

                "chunk_id":
                    f"{DOCUMENT}-page-{page_number:03d}-formula-{index:03d}",


                "type":
                    "formula",


                "document":
                    page.get(
                        "document"
                    ),


                "version":
                    page.get(
                        "version"
                    ),


                "page":
                    page_number,


                "content":
                    context,


                "embedding_text":
                    build_embedding_text(
                        page,
                        context
                    ),


                "metadata":
                    {
                        "source":
                            DOCUMENT,

                        "created":
                            datetime.now()
                            .isoformat()
                    }

            }
        )



    return chunks



def build_chunks(
    pages
):

    print(
        "Building chunks..."
    )


    result = []


    for page in pages:

        page_chunks = process_page(
            page
        )


        result.extend(
            page_chunks
        )


    print(
        f"Chunks created: {len(result)}"
    )


    return result



def save_chunks(
    chunks
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        OUTPUT_FILE,
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
        "Saved:"
    )

    print(
        OUTPUT_FILE
    )



def main():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Chunk Builder v2"
    )

    print("=" * 70)



    pages = load_pages()


    chunks = build_chunks(
        pages
    )


    save_chunks(
        chunks
    )


    print()
    print(
        "DONE"
    )



if __name__ == "__main__":

    main()
    