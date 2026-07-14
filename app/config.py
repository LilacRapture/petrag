from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "petrag"

    embedding_model: str = "all-MiniLM-L6-v2"

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    source_project_name: str = "tasktracker"
    source_project_path: str = "/sources/tasktracker"

    class Config:
        env_file = (".env", ".env.local")


settings = Settings()
