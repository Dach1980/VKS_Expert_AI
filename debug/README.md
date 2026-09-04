# Debug artifacts

Эта папка хранит воспроизводимую историю диагностических запусков Project Expert AI.

## Структура

```text
debug/
├── README.md
├── rag-benchmark.md
└── runs/
    └── <timestamp>_<document_id>/
        ├── report.json
        └── run_meta.json
```

`report.json` — полный результат проверки, включая `diagnostics`, `diagnostics_log`, findings, нормативные источники и решения.

`run_meta.json` — метаданные эксперимента: commit проекта, модель Vision, документ, Skill, число проверенных страниц и краткие метрики цепочки Skill → Vision → RAG → normative requirements → decision.

## Как сохранять результат

После завершения проверки запустите из корня проекта:

```powershell
python scripts/save_debug_run.py <document_id> --model qwen3-vl-4b-instruct --label baseline
```

Скрипт копирует текущий `knowledge/project_documents/<document_id>/checking/first_pass/report.json` в `debug/runs/...` и создаёт компактные метаданные для сравнения запусков.

Получившиеся файлы являются частью экспериментальной истории и должны коммититься в Git. Исходный PDF, изображения страниц и checkpoint в `knowledge/project_documents` в debug-историю не копируются.

## Правило экспериментов

Перед каждым сравнительным запуском фиксируйте:

- Git commit;
- Vision model и quantization;
- Skill;
- нормативные версии;
- документ и scope страниц;
- параметры retrieval;
- изменения prompt/pipeline.

Не удаляйте старые runs: они являются baseline для оценки регрессий и улучшений.
