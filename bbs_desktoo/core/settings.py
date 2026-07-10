# bbs_desktoo/core/settings.py
# BBS desktOO — accès centralisé à la configuration persistante.
#
# Préférences (géométrie, dossiers, police…) : QSettings
# (~/.config/blacksamdev/desktoo.conf).
#
# SECRETS (clés API, token GitHub) : trousseau système (KWallet/GNOME Keyring)
# via la lib `keyring`, quand elle est disponible — les secrets ne touchent
# alors plus le disque en clair. Les clés déjà présentes en clair dans
# QSettings sont migrées automatiquement au premier accès, puis effacées.
# Si aucun trousseau n'est disponible, repli transparent sur QSettings
# (comportement historique) : rien ne casse.

from PyQt6.QtCore import QSettings

try:
    import keyring as _keyring
except ImportError:          # lib absente : repli QSettings
    _keyring = None

_KR_SERVICE = "bbs-desktoo"
_kr_ok: bool | None = None   # cache : trousseau réellement utilisable ?


def _kr_available() -> bool:
    """Sonde une fois si un vrai trousseau répond (pas le backend 'fail')."""
    global _kr_ok
    if _kr_ok is None:
        if _keyring is None:
            _kr_ok = False
        else:
            try:
                _keyring.get_password(_KR_SERVICE, "__probe__")
                _kr_ok = True
            except Exception:
                _kr_ok = False
    return _kr_ok


def _kr_get(name: str) -> str | None:
    if not _kr_available():
        return None
    try:
        return _keyring.get_password(_KR_SERVICE, name)
    except Exception:
        return None


def _kr_set(name: str, value: str) -> bool:
    """Écrit (ou efface si vide) dans le trousseau. True si pris en charge."""
    if not _kr_available():
        return False
    try:
        if value:
            _keyring.set_password(_KR_SERVICE, name, value)
        else:
            try:
                _keyring.delete_password(_KR_SERVICE, name)
            except Exception:
                pass
        return True
    except Exception:
        return False


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

    # ---- Taille de police de l'éditeur ----
    def editor_font_size(self) -> int:
        return self._q.value("editor/font_size", 11, type=int)

    def set_editor_font_size(self, size: int) -> None:
        self._q.setValue("editor/font_size", size)

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
        # 1) Trousseau système
        v = _kr_get(f"api_{provider}")
        if v:
            return v
        # 2) Héritage QSettings (clair) : migrer vers le trousseau si possible
        legacy = self._q.value(f"ai/key_{provider}", "", type=str)
        if legacy and _kr_set(f"api_{provider}", legacy):
            self._q.remove(f"ai/key_{provider}")
        return legacy

    def set_api_key(self, provider: str, key: str) -> None:
        if _kr_set(f"api_{provider}", key):
            # Le trousseau a pris le relais : on purge toute trace en clair.
            self._q.remove(f"ai/key_{provider}")
        else:
            # Pas de trousseau : comportement historique (QSettings).
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
        v = _kr_get("github_token")
        if v:
            return v
        legacy = self._q.value("github/token", "", type=str)
        if legacy and _kr_set("github_token", legacy):
            self._q.remove("github/token")
        return legacy

    def set_github_token(self, token: str) -> None:
        if _kr_set("github_token", token):
            self._q.remove("github/token")
        else:
            self._q.setValue("github/token", token)

    # ---- Introspection ----
    @staticmethod
    def secrets_backend() -> str:
        """'trousseau' si les secrets vont dans KWallet/Keyring, sinon 'clair'."""
        return "trousseau" if _kr_available() else "clair"
