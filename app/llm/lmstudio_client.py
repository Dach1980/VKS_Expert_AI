import json
import urllib.request
import urllib.error
from pathlib import Path


class LMStudioClient:
    """Клиент для работы с локальным сервером LM Studio."""

    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        lm_config = self.config["lm_studio"]

        self.base_url = lm_config["base_url"].rstrip("/")
        self.model = lm_config["model"]
        self.temperature = lm_config.get("temperature", 0.2)
        self.max_tokens = lm_config.get("max_tokens", 2048)

    def _load_config(self) -> dict:
        """Загружает конфигурацию проекта."""

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Файл конфигурации не найден: {self.config_path}"
            )

        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_models(self) -> list[dict]:
        """Возвращает модели, доступные через LM Studio API."""

        url = f"{self.base_url}/models"

        request = urllib.request.Request(
            url,
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            return result.get("data", [])

        except urllib.error.URLError as error:
            raise ConnectionError(
                f"Не удалось подключиться к LM Studio: {error}"
            ) from error

    def is_model_available(self) -> bool:
        """Проверяет наличие выбранной модели."""

        models = self.get_models()

        available_models = {
            model.get("id")
            for model in models
        }

        return self.model in available_models

    def chat(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Отправляет сообщение модели и возвращает ответ."""

        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=300,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"LM Studio API вернул ошибку "
                f"{error.code}: {details}"
            ) from error

        except urllib.error.URLError as error:
            raise ConnectionError(
                f"Не удалось подключиться к LM Studio: {error}"
            ) from error

        try:
            return result["choices"][0]["message"]["content"]

        except (KeyError, IndexError) as error:
            raise RuntimeError(
                f"Неожиданный ответ LM Studio: {result}"
            ) from error


if __name__ == "__main__":

    client = LMStudioClient()

    print("=" * 60)
    print("VKS Expert AI — LM Studio diagnostic")
    print("=" * 60)

    print("\nДоступные модели:")

    models = client.get_models()

    for model in models:
        print(f"  • {model.get('id')}")

    print("\nВыбранная модель:")
    print(f"  {client.model}")

    print("\nМодель доступна:")

    if client.is_model_available():
        print("  ✓ Да")
    else:
        print("  ✗ Нет")

    print("\nОтправляем тестовый запрос...")

    answer = client.chat(
        "Объясни одним коротким абзацем, "
        "что такое система внутреннего хозяйственно-питьевого "
        "водопровода.",
        system_prompt=(
            "Ты являешься техническим AI-ассистентом "
            "инженера по разделу ВК. "
            "Отвечай технически точно и не выдумывай "
            "нормативные требования."
        ),
    )

    print("\nОтвет модели:")
    print("-" * 60)
    print(answer)
    print("-" * 60)
    