# bbs_desktoo/ai/claude.py
# BBS desktOO — provider Claude (API Anthropic).
#
# Utilise le SDK officiel `anthropic`. Streaming via messages.stream().
# L'utilisateur fournit sa propre clé (réglages → IA). Rien n'est codé en dur.

from collections.abc import Iterator

from bbs_desktoo.ai.base import AIProvider, AIError


class ClaudeProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        if not api_key:
            raise AIError("Clé API Anthropic manquante. Renseigne-la dans IA → Configurer le modèle.")
        self._model = model
        try:
            import anthropic
        except ImportError as exc:
            raise AIError("Le paquet 'anthropic' n'est pas installé : pip install anthropic") from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------ #
    def stream(self, messages: list[dict], system: str | None = None) -> Iterator[str]:
        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except self._anthropic.APIStatusError as exc:
            raise AIError(f"Claude API ({exc.status_code}) : {exc.message}") from exc
        except self._anthropic.APIError as exc:
            raise AIError(f"Claude API : {exc}") from exc
        except Exception as exc:  # réseau, etc.
            raise AIError(f"Claude : {exc}") from exc

    def label(self) -> str:
        return self._model

    @property
    def key_name(self) -> str:
        return "claude"
