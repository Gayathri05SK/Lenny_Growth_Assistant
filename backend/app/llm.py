"""
Thin abstraction so the rest of the app doesn't care whether it's talking
to Anthropic's cloud API or a local Ollama model. This is the "LLM toggle".
"""
import requests
from .config import settings


class LLMError(Exception):
    pass


class GROQClient:
    def __init__(self):
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set in your .env file.")
        self.api_key = settings.groq_api_key
        self.model = self._resolve_model_name(settings.groq_model)
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    @staticmethod
    def _resolve_model_name(model_name: str) -> str:
        normalized = (model_name or "llama-3.3-70b-versatile").strip().lower()
        normalized = normalized.replace(" ", "-")

        aliases = {
            "llama-3.3-70b": "llama-3.3-70b-versatile",
            "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant": "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile": "llama-3.1-70b-versatile",
        }
        return aliases.get(normalized, normalized)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "stream": False,
                },
                timeout=180,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                raise LLMError(
                    f"Groq model '{self.model}' was not found. Use a supported Groq model slug such as 'llama-3.3-70b-versatile' or 'llama-3.1-8b-instant'."
                )
            raise LLMError(f"Groq API error: {e}")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Groq request error: {e}")
        except Exception as e:
            raise LLMError(f"Groq response error: {e}")


class OllamaClient:
    def __init__(self):
        self.host = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
                timeout=180,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            raise LLMError(
                f"Could not reach Ollama at {self.host}. Start it with `ollama serve`, "
                f"then pull the model with `ollama pull {self.model}`."
            )
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise LLMError(
                    f"Ollama returned 404 at {self.host}/api/chat. "
                    f"Check that `ollama serve` is running and the model `{self.model}` exists."
                )
            raise LLMError(f"Ollama HTTP error: {e}")
        except requests.exceptions.Timeout:
            raise LLMError("Ollama timed out. Try a smaller/faster local model.")
        except Exception as e:
            raise LLMError(f"Ollama error: {e}")


def get_llm_client(provider: str):
    provider = (provider or settings.default_llm_provider or "groq").lower()
    if provider == "ollama":
        return OllamaClient()
    return GROQClient()
