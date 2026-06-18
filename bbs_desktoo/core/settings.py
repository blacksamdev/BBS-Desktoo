# bbs_desktoo/core/settings.py
# BBS desktOO — accès centralisé à la configuration persistante.
#
# Tout passe par QSettings (stockage natif Qt sous ~/.config/blacksamdev/desktoo.conf).
# Aucune clé API n'est écrite en clair dans le dépôt.

from PyQt6.QtCore import QSettings


ORG = "blacksamdev"
APP = "desktoo"


class Settings:
    """Façade fine au-dessus de QSettings, avec des clés nommées et des défauts."""

    def __init__(self) -> None:
        self._q = QSettings(ORG, APP)

    # ---- Géométrie / état de la fenêtre ----
    def window_geometry(self):
        return self._q.value("window/geometry")

    def set_window_geometry(self, data) -> None:
        self._q.setValue("window/geometry", data)

    def splitter_state(self, name: str):
        return self._q.value(f"splitter/{name}")

    def set_splitter_state(self, name: str, data) -> None:
        self._q.setValue(f"splitter/{name}", data)

    # ---- Dernier dossier ouvert ----
    def last_folder(self) -> str:
        return self._q.value("workspace/last_folder", "", type=str)

    def set_last_folder(self, path: str) -> None:
        self._q.setValue("workspace/last_folder", path)

    # ---- Provider IA ----
    def ai_provider(self) -> str:
        return self._q.value("ai/provider", "claude", type=str)

    def set_ai_provider(self, name: str) -> None:
        self._q.setValue("ai/provider", name)

    def ai_model(self) -> str:
        return self._q.value("ai/model", "claude-sonnet-4-6", type=str)

    def set_ai_model(self, model: str) -> None:
        self._q.setValue("ai/model", model)

    def api_key(self, provider: str) -> str:
        return self._q.value(f"ai/key_{provider}", "", type=str)

    def set_api_key(self, provider: str, key: str) -> None:
        self._q.setValue(f"ai/key_{provider}", key)

    def ollama_host(self) -> str:
        return self._q.value("ai/ollama_host", "http://localhost:11434", type=str)

    def set_ollama_host(self, host: str) -> None:
        self._q.setValue("ai/ollama_host", host)

    # ---- Dépôts GitHub suivis (statut CI) ----
    def github_repos(self) -> list[str]:
        val = self._q.value("github/repos", [], type=list)
        return val if val else []

    def add_github_repo(self, repo: str) -> None:
        repos = self.github_repos()
        if repo and repo not in repos:
            repos.append(repo)
            self._q.setValue("github/repos", repos)

    def remove_github_repo(self, repo: str) -> None:
        repos = self.github_repos()
        if repo in repos:
            repos.remove(repo)
            self._q.setValue("github/repos", repos)

    def github_token(self) -> str:
        return self._q.value("github/token", "", type=str)

    def set_github_token(self, token: str) -> None:
        self._q.setValue("github/token", token)
