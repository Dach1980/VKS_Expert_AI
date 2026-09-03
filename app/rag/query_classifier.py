"""Project Expert AI — rule-based engineering query classifier."""

from dataclasses import dataclass
from typing import List


@dataclass
class QueryIntent:
    system: str
    discipline: str
    topic: str
    keywords: List[str]


class QueryClassifier:
    """Classify engineering questions before RAG retrieval."""

    def classify(self, question: str) -> QueryIntent:
        text = str(question or "").lower()
        system = "unknown"
        topic = "general"
        keywords: list[str] = []

        water_supply_words = [
            "водоснабж", "хвс", "гвс", "водопровод", "расход воды",
            "напор", "давление", "трубопровод", "трубы", "диаметр",
            "условный проход", "ду", "dn",
        ]
        if any(word in text for word in water_supply_words):
            system = "internal_water_supply"
            keywords.extend(word for word in water_supply_words if word in text)

        hot_water_words = ["горяч", "гвс", "водонагрев", "циркуляц", "теплопотер"]
        if any(word in text for word in hot_water_words):
            system = "hot_water_supply"
            keywords.extend(word for word in hot_water_words if word in text)

        sewer_words = ["канализац", "сток", "водоотвед", "гидрозатвор", "стояк канализац"]
        if any(word in text for word in sewer_words):
            system = "sewerage"
            keywords.extend(word for word in sewer_words if word in text)

        storm_words = ["водосток", "дождев", "ливнев", "осадк"]
        if any(word in text for word in storm_words):
            system = "storm_water"
            keywords.extend(word for word in storm_words if word in text)

        fire_words = ["пожар", "внутренний пожарный", "краны пожарные", "пк"]
        if any(word in text for word in fire_words):
            system = "fire_water"
            keywords.extend(word for word in fire_words if word in text)

        if any(word in text for word in ["расход", "секундный", "часовой"]):
            topic = "hydraulic_calculation"
        elif any(word in text for word in [
            "диаметр", "диаметру", "диаметры", "трубы", "трубопровод",
            "условный проход", "ду", "dn",
        ]):
            topic = "pipe_selection"
        elif any(word in text for word in ["напор", "давление", "потери"]):
            topic = "pressure_calculation"
        elif any(word in text for word in ["требован", "норм", "пункт", "сп"]):
            topic = "normative_requirement"

        return QueryIntent(
            system=system,
            discipline="ВК",
            topic=topic,
            keywords=list(dict.fromkeys(keywords)),
        )


def demo():
    classifier = QueryClassifier()
    for question in [
        "Как определяется максимальный расчетный расход воды на расчетном участке сети?",
        "Как подобрать диаметр трубопровода ХВС?",
        "Требования к внутреннему пожарному водопроводу",
        "Как рассчитывается канализационный стояк?",
    ]:
        print("\nQUESTION:\n", question)
        print("\nINTENT:\n", classifier.classify(question))


if __name__ == "__main__":
    demo()
