# PetRAG

RAG-поиск по pet-проектам (TaskTracker, DnD Backend, Fairytale) через
Qdrant + локальные embeddings (sentence-transformers) + локальную LLM (Ollama).

## Архитектура

Два независимых процесса:

- `ingestion/` — batch-пайплайн: читает исходники, режет на чанки,
  считает embeddings, пишет в Qdrant. Запускается руками при обновлении данных.
- `app/` — FastAPI-сервис: принимает вопрос, ищет в Qdrant, генерирует
  ответ через Ollama. Работает постоянно.

## Стек

- Python 3.12, FastAPI
- Qdrant (векторная БД)
- sentence-transformers (`all-MiniLM-L6-v2`) — embeddings, полностью локально
- Ollama (`qwen2.5-coder`) — генерация ответа, полностью локально
- Docker + OrbStack (Qdrant в контейнере; Ollama — нативно на хосте, см. `docs/decisions.md` ADR-002)

## Запуск (полный стек)

1. Установить Ollama-модель: `ollama pull qwen2.5-coder:7b`
2. `cp .env.example .env`
3. Положить чекаут TaskTracker в `sources/tasktracker/` (symlink, не копия):
   `ln -s /полный/путь/до/tasktracker sources/tasktracker`
4. `docker compose up --build`
5. Проверить: `http :8001/health`

## Разработка (локально, без пересборки образа)

Для итеративной работы над ingestion/`app/` быстрее гонять код напрямую из venv, не дожидаясь `docker compose build` на каждое изменение:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Создать `.env.local` (гитигнорится, не коммитится) с host-специфичными значениями — они переопределяют `.env` для локальных запусков:

```bash
# .env.local
QDRANT_HOST=localhost
SOURCE_PROJECT_PATH=sources/tasktracker
OLLAMA_BASE_URL=http://localhost:11434
```

Дальше:

```bash
docker compose up -d qdrant          # Qdrant поднят в докере в любом случае
python -m ingestion.ingest --source readme       # или docstrings / git_log
uvicorn app.main:app --reload --port 8000
http POST :8000/query question="..." project=tasktracker top_k:=5
```

Линтер: `ruff check .` (конфиг в `pyproject.toml`).

## Документация

| Файл | Назначение |
|------|-----------|
| [AGENTS.md](AGENTS.md) | Конвенции проекта, статус по фазам |
| [docs/decisions.md](docs/decisions.md) | ADR (архитектурные решения) |

## Статус

**Фазы 1-4 завершены** — end-to-end пайплайн работает: README/docs + docstrings + git log индексируются в Qdrant, `/query` отвечает через retrieval + локальную LLM.

**Фаза 5 (следующая):** второй/третий проект (DnD Backend, Fairytale) — та же схема extractors, единая Qdrant-коллекция с фильтром по `project` в payload (решение уже принято, см. историю обсуждения при старте проекта).

Подробный статус по каждой фазе — в [AGENTS.md](AGENTS.md).