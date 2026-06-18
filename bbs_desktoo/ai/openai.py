# bbs_desktoo/ai/openai.py
# BBS desktOO — provider OpenAI.
#
# SDK officiel `openai`, streaming via chat.completions(stream=True).
# Le message système est passé comme premier message de rôle "system".

from collections.abc import Iterator

from bbs_desktoo.ai.base import AIProvider, AIError


class OpenAIProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        if not api_key:
            raise AIError("Clé API OpenAI manquante. Renseigne-la dans IA → Configurer le modèle.")
        self._model = model
        try:
            import openai
        except ImportError as exc:
            raise AIError("Le paquet 'openai' n'est pas installé : pip install openai") from exc
        self._openai = openai
        self._client = openai.OpenAI(api_key=api_key)

    # ------------------------------------------------------------------ #
    def stream(self, messages: list[dict], system: str | None = None) -> Iterator[str]:
        full = list(messages)
        if system:
            full = [{"role": "system", "content": system}] + full
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=full,
                stream=True,
                max_tokens=4096,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except self._openai.APIError as exc:
            raise AIError(f"OpenAI : {exc}") from exc
        except Exception as exc:
            raise AIError(f"OpenAI : {exc}") from exc

    def label(self) -> str:
        return self._model

    @property
    def key_name(self) -> str:
        return "openai"
