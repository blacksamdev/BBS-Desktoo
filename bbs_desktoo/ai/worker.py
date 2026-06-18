# bbs_desktoo/ai/worker.py
# BBS desktOO — fabrique de providers + worker de streaming.
#
# Le worker exécute l'appel IA dans un QThread : l'UI ne gèle jamais pendant
# la génération. Les fragments remontent via le signal `token`, la fin via
# `finished`, les erreurs via `error`.

from PyQt6.QtCore import QThread, pyqtSignal

from bbs_desktoo.ai.base import AIProvider, AIError
from bbs_desktoo.ai.claude import ClaudeProvider
from bbs_desktoo.ai.openai import OpenAIProvider
from bbs_desktoo.ai.ollama import OllamaProvider


def build_provider(settings) -> AIProvider:
    """Instancie le provider actif d'après la configuration utilisateur.

    Lève AIError si la config est incomplète (clé manquante, etc.).
    """
    name = settings.ai_provider()
    model = settings.ai_model()

    if name == "claude":
        return ClaudeProvider(api_key=settings.api_key("claude"), model=model)
    if name == "openai":
        return OpenAIProvider(api_key=settings.api_key("openai"), model=model)
    if name == "ollama":
        return OllamaProvider(model=model, host=settings.ollama_host())
    raise AIError(f"Provider inconnu : {name}")


class StreamWorker(QThread):
    """Exécute provider.stream() hors du thread UI."""

    token = pyqtSignal(str)     # un fragment de texte
    finished = pyqtSignal()     # génération terminée
    error = pyqtSignal(str)     # message d'erreur lisible

    def __init__(self, provider: AIProvider, messages: list[dict],
                 system: str | None = None, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._messages = messages
        self._system = system
        self._stop = False

    def run(self) -> None:
        try:
            for chunk in self._provider.stream(self._messages, self._system):
                if self._stop:
                    break
                self.token.emit(chunk)
            self.finished.emit()
        except AIError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # garde-fou
            self.error.emit(f"Erreur inattendue : {exc}")

    def stop(self) -> None:
        self._stop = True
