"""
VKS Expert AI

Query Classifier v1

Purpose:

Classification of engineering questions
before RAG retrieval.

Pipeline:

User Question

        |
        v

QueryClassifier

        |
        v

Engineering intent

        |
        v

Retriever


Supported systems:

- water_supply
- hot_water
- sewerage
- storm_water
- fire_water
- unknown


"""


from dataclasses import dataclass
from typing import List



@dataclass
class QueryIntent:
    """
    Classified engineering query.
    """

    system: str

    discipline: str

    topic: str

    keywords: List[str]



class QueryClassifier:
    """
    Rule-based engineering query classifier.
    """



    def classify(
        self,
        question: str
    ) -> QueryIntent:


        text = question.lower()



        #
        # Default
        #

        system = "unknown"

        topic = "general"

        keywords = []



        #
        # Internal water supply
        #

        water_supply_words = [

            "водоснабж",

            "хвс",

            "гвс",

            "водопровод",

            "расход воды",

            "напор",

            "давление",

            "трубопровод",

            "диаметр трубы",

        ]



        if any(
            word in text
            for word in water_supply_words
        ):

            system = (
                "internal_water_supply"
            )

            keywords.extend(

                [

                    word

                    for word in water_supply_words

                    if word in text

                ]

            )



        #
        # Hot water supply
        #

        hot_water_words = [

            "горяч",

            "гвс",

            "водонагрев",

            "циркуляц",

            "теплопотер",

        ]



        if any(

            word in text

            for word in hot_water_words

        ):

            system = (
                "hot_water_supply"
            )

            keywords.extend(

                [

                    word

                    for word in hot_water_words

                    if word in text

                ]

            )



        #
        # Sewerage
        #

        sewer_words = [

            "канализац",

            "сток",

            "водоотвед",

            "гидрозатвор",

            "стояк канализац",

        ]



        if any(

            word in text

            for word in sewer_words

        ):

            system = (
                "sewerage"
            )


            keywords.extend(

                [

                    word

                    for word in sewer_words

                    if word in text

                ]

            )



        #
        # Storm water
        #

        storm_words = [

            "водосток",

            "дождев",

            "ливнев",

            "осадк",

        ]



        if any(

            word in text

            for word in storm_words

        ):

            system = (
                "storm_water"
            )


            keywords.extend(

                [

                    word

                    for word in storm_words

                    if word in text

                ]

            )



        #
        # Fire water
        #

        fire_words = [

            "пожар",

            "внутренний пожарный",

            "краны пожарные",

            "пк",

        ]



        if any(

            word in text

            for word in fire_words

        ):

            system = (
                "fire_water"
            )


            keywords.extend(

                [

                    word

                    for word in fire_words

                    if word in text

                ]

            )



        #
        # Topic detection
        #

        if any(

            word in text

            for word in [

                "расход",

                "секундный",

                "часовой",

            ]

        ):

            topic = (
                "hydraulic_calculation"
            )



        elif any(

            word in text

            for word in [

                "диаметр",

                "трубы",

                "трубопровод",

            ]

        ):

            topic = (
                "pipe_selection"
            )



        elif any(

            word in text

            for word in [

                "напор",

                "давление",

                "потери",

            ]

        ):

            topic = (
                "pressure_calculation"
            )



        elif any(

            word in text

            for word in [

                "требован",

                "норм",

                "пункт",

                "сп",

            ]

        ):

            topic = (
                "normative_requirement"
            )



        else:

            topic = (
                "general"
            )



        return QueryIntent(

            system=system,

            discipline="ВК",

            topic=topic,

            keywords=list(
                set(keywords)
            )

        )



def demo():


    print("=" * 70)

    print(
        "VKS Expert AI"
    )

    print(
        "Query Classifier v1"
    )

    print("=" * 70)



    classifier = QueryClassifier()



    questions = [

        "Как определяется максимальный расчетный расход воды на участке сети?",

        "Как подобрать диаметр трубопровода ХВС?",

        "Требования к внутреннему пожарному водопроводу",

        "Как рассчитывается канализационный стояк?"

    ]



    for q in questions:


        result = classifier.classify(q)


        print("\nQUESTION:")

        print(q)


        print("\nINTENT:")

        print(result)



if __name__ == "__main__":

    demo()
    