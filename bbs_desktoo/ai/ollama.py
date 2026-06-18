# bbs_desktoo/ai/ollama.py
# BBS desktOO — provider Ollama (modèle local).
#
# Pas de SDK : appel direct à l'API HTTP d'Ollama via httpx, en streaming
# NDJSON. Aucune clé requise — c'est local, c'est gratuit, c'est dans l'esprit
# BBS. Hôte par défaut : http://localhost:11434.

import json
from collections.abc import Iterator

from bbs_desktoo.ai.base import AIProvider, AIError


class OllamaProvider(AIProvider):

    def __init__(self, model: str = "mistral", host: str = "http://localhost:11434"):
        self._model = model
        self._host = host.rstrip("/")
        try:
            import httpx
        except ImportError as exc:
            raise AIError("Le paquet 'httpx' n'est pas installé : pip install httpx") from exc
        self._httpx = httpx

    # ------------------------------------------------------------------ #
    def stream(self, messages: list[dict], system: str | None = None) -> Iterator[str]:
        full = list(messages)
        if system:
            full = [{"role": "system", "content": system}] + full

        payload = {"model": self._model, "messages": full, "stream": True}
        url = f"{self._host}/api/chat"
        try:
            with self._httpx.stream("POST", url, json=payload, timeout=None) as resp:
                if resp.status_code == 404:
                    raise AIError(
                        f"Modèle '{self._model}' introuvable sur Ollama. "
                        f"Lance : ollama pull {self._model}"
                    )
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except self._httpx.ConnectError as exc:
            raise AIError(
                f"Ollama injoignable sur {self._host}. "
                "Vérifie qu'Ollama tourne (ollama serve)."
            ) from exc
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"Ollama : {exc}") from exc

    def list_models(self) -> list[str]:
        """Liste les modèles installés localement (pour le sélecteur de modèle)."""
        try:
            resp = self._httpx.get(f"{self._host}/api/tags", timeout=5)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    def label(self) -> str:
        return f"ollama:{self._model}"

    @property
    def key_name(self) -> str:
        return "ollama"
