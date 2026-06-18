# bbs_desktoo/ai/base.py
# BBS desktOO — contrat commun à tous les providers IA.
#
# Le panneau IA ne connaît que cette interface. Brancher un nouveau modèle =
# ajouter une sous-classe, sans toucher à l'UI. C'est le cœur de la promesse
# BBS : agnostique au modèle, l'utilisateur branche son propre accès.

from abc import ABC, abstractmethod
from collections.abc import Iterator


class AIError(Exception):
    """Erreur normalisée remontée à l'UI (clé absente, réseau, quota…)."""


class AIProvider(ABC):
    """Interface d'un fournisseur de complétion en streaming."""

    @abstractmethod
    def stream(self, messages: list[dict], system: str | None = None) -> Iterator[str]:
        """Envoie la conversation et produit la réponse par fragments (tokens).

        messages : liste de dicts {"role": "user"|"assistant", "content": str}
        system   : instruction système optionnelle
        yield    : fragments de texte au fil de la génération

        Lève AIError en cas de problème (clé manquante, réseau, modèle absent).
        """
        raise NotImplementedError

    @abstractmethod
    def label(self) -> str:
        """Nom court affiché dans le badge du panneau (ex. 'claude-sonnet-4-6')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def key_name(self) -> str:
        """Identifiant interne du provider ('claude', 'openai', 'ollama')."""
        raise NotImplementedError
