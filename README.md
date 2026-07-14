# PetRAG

RAG-поиск по pet-проектам (TaskTracker, DnD Backend, Fairytale) через
Qdrant + локальные embeddings (sentence-transformers) + локальную LLM (Ollama).

## Архитектура

Два независимых процесса:

- `ingestion/` — batch-пайплайн: читает исходники, режет на чанки,
  считает embeddings, пишет в Qdrant. Запускается руками при обновлении данных.
- `app/` — FastAPI-сервис: принимает вопрос, ищет в Qdrant, генерирует
  ответ через Ollama. Работает постоянно.

## Запуск

1. Установить Ollama-модель: `ollama pull qwen2.5-coder:7b`
2. `cp .env.example .env`
3. Положить чекаут TaskTracker в `sources/tasktracker/` (или примонтировать свой путь в docker-compose.yml)
4. `docker compose up --build`
5. Проверить: `curl http://localhost:8001/health`

## Статус

Скаффолд. Логика ingestion и retrieval — заглушки (`TODO`), заполняем итеративно по фазам:

1. extract_readme.py + chunking + ingest.py → первый end-to-end прогон
2. app/vector_store.py + app/llm.py + app/main.py → первый рабочий /query
3. extract_docstrings.py
4. extract_git_log.py
