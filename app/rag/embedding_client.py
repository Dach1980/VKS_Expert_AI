"""
VKS Expert AI

Embedding Client v1.1

Purpose:
Generate embeddings through LM Studio local API.

Important:
Embedding model is managed by LM Studio.
This client does not download or load models.

Architecture:

Retriever
    |
    v
EmbeddingClient
    |
    v
LM Studio Embedding API
    |
    v
text-embedding-nomic-embed-text-v1.5
"""


from typing import List


from openai import OpenAI



class EmbeddingClient:
    """
    Local embedding client.

    Uses LM Studio OpenAI-compatible endpoint.
    """


    def __init__(
        self,
        model: str = "text-embedding-nomic-embed-text-v1.5",
        base_url: str = "http://localhost:1234/v1",
    ):

        print(
            "Initializing embedding client..."
        )


        self.model = model


        self.client = OpenAI(

            base_url=base_url,

            api_key="lm-studio"

        )


        self.base_url = base_url


        print(
            f"Embedding model: {self.model}"
        )

        print(
            f"Endpoint: {self.base_url}"
        )



    # ==================================================
    # HEALTH CHECK
    # ==================================================


    def health_check(self) -> bool:
        """
        Check LM Studio availability.
        """


        try:

            models = self.client.models.list()


            return (

                models is not None

            )


        except Exception as e:


            print(
                "Embedding service unavailable:"
            )


            print(
                e
            )


            return False



    # ==================================================
    # SINGLE EMBEDDING
    # ==================================================


    def embed(
        self,
        text: str
    ) -> List[float]:
        """
        Generate embedding vector.

        Args:
            text:
                Input string

        Returns:
            Vector
        """


        if not text.strip():

            raise ValueError(

                "Cannot create embedding for empty text"

            )



        try:


            response = (

                self.client.embeddings.create(

                    model=self.model,

                    input=text

                )

            )



            return (

                response
                .data[0]
                .embedding

            )



        except Exception as e:


            raise RuntimeError(

                f"""
Embedding generation failed.

Model:
{self.model}

Endpoint:
{self.base_url}

Error:
{e}
"""

            )



    # ==================================================
    # BATCH EMBEDDING
    # ==================================================


    def embed_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        """


        if not texts:

            return []



        try:


            response = (

                self.client.embeddings.create(

                    model=self.model,

                    input=texts

                )

            )



            return [

                item.embedding

                for item in response.data

            ]



        except Exception as e:


            raise RuntimeError(

                f"""
Batch embedding generation failed.

Error:
{e}
"""

            )



    # ==================================================
    # INFO
    # ==================================================


    def info(self) -> dict:
        """
        Return embedding configuration.
        """


        return {

            "model":
                self.model,

            "endpoint":
                self.base_url,

            "type":
                "lm_studio_embedding"

        }



# ======================================================
# DEMO
# ======================================================


def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Embedding Client v1.1"
    )

    print("=" * 70)



    client = EmbeddingClient()



    print()

    print(
        "INFO:"
    )

    print(
        client.info()
    )



    print()

    print(
        "Checking LM Studio..."
    )


    if not client.health_check():

        print(
            "FAILED"
        )

        return



    print(
        "OK"
    )



    text = """

СП 30.13330.2020.
Расчетный расход воды
на расчетном участке сети.

"""



    vector = client.embed(text)



    print()

    print(
        "Embedding generated"
    )


    print(
        "Dimension:",
        len(vector)
    )


    print(
        "First values:",
        vector[:5]
    )



if __name__ == "__main__":

    demo()
    