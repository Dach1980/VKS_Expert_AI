# RAG Benchmark

Цель — измерять не только количество замечаний, а качество прохождения цепочки:

`Skill → visual evidence → RAG → normative requirement → decision → remark`

## Основные метрики

Для контрольного набора вопросов/проверок с известным эталонным пунктом нормы:

- Recall@1, Recall@5, Recall@10;
- MRR;
- NDCG@K;
- exact clause hit;
- table-row hit;
- version correctness;
- false-positive rate;
- доля кандидатов, дошедших до normative requirement;
- доля решений `violation/compliant/unchecked`.

## Правило сравнения

Каждый эксперимент сохраняется отдельным run. Нельзя сравнивать два запуска без фиксации Git commit, модели, версии нормативной базы, Skill и scope страниц.

Для RAG-изменений baseline должен оставаться неизменным, кроме одного проверяемого изменения. Это позволит приписывать прирост конкретному изменению.

## Текущий baseline

Пока baseline создаётся. Первый стабильный запуск после устранения проблемы Vision следует сохранить с label `baseline`.
