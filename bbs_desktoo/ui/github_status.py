# bbs_desktoo/ui/github_status.py
# BBS desktOO — pastilles de statut CI GitHub.
#
# Affiche, pour chaque dépôt suivi, une pastille colorée :
#   vert  = dernier build OK
#   rouge = dernier build en échec
#   jaune = build en cours
#   gris  = aucun run / erreur / dépôt privé sans token
#
# Clic sur une pastille -> ouvre la page Actions du dépôt dans le panneau web.
# Bouton + : ajoute un dépôt (URL ou owner/repo) ; il est mémorisé (QSettings).
#
# Le statut est rafraîchi en arrière-plan (QThread) pour ne pas geler l'UI.

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QInputDialog, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QBrush

from bbs_desktoo.core.theme import COLORS
from bbs_desktoo.core import github


_STATE_COLORS = {
    "success":  COLORS["green"],
    "failure":  COLORS["accent"],
    "building": COLORS["yellow"],
    "none":     COLORS["text_dim"],
    "error":    COLORS["text_dim"],
}


def _dot_icon(color: str, size: int = 12) -> QIcon:
    """Dessine un rond plein de la couleur donnée (pastille de statut CI)."""
    from PyQt6.QtGui import QImage
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)   # 0 = transparent total en ARGB32
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(color)))
    m = 1
    p.drawEllipse(m, m, size - 2 * m, size - 2 * m)
    p.end()
    return QIcon(QPixmap.fromImage(img))


class _PollWorker(QThread):
    """Récupère le statut d'un dépôt hors du thread UI."""
    done = pyqtSignal(str, dict)   # "owner/repo", résultat

    def __init__(self, owner, repo, token, parent=None):
        super().__init__(parent)
        self._owner, self._repo, self._token = owner, repo, token

    def run(self):
        result = github.fetch_status(self._owner, self._repo, self._token)
        self.done.emit(f"{self._owner}/{self._repo}", result)


class GitHubStatus(QWidget):
    """Barre de pastilles CI, à placer dans le coin de la barre de menus."""

    open_url = pyqtSignal(str)   # demande d'ouverture d'une URL dans le panneau web

    REFRESH_MS = 90_000          # rafraîchissement auto toutes les 90 s

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._buttons: dict[str, QPushButton] = {}   # "owner/repo" -> pastille
        self._workers: list[_PollWorker] = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 0, 8, 0)
        self._layout.setSpacing(4)

        # Bouton d'ajout
        self.add_btn = QPushButton("＋ CI")
        self.add_btn.setToolTip("Suivre le statut CI d'un dépôt GitHub")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet(self._add_btn_style())
        self.add_btn.clicked.connect(self._add_repo)
        self._layout.addWidget(self.add_btn)

        # Charge les dépôts mémorisés
        for ref in self.settings.github_repos():
            parsed = github.parse_repo(ref)
            if parsed:
                self._add_pastille(*parsed)

        # Rafraîchissement périodique
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_all)
        self._timer.start(self.REFRESH_MS)
        QTimer.singleShot(500, self.refresh_all)   # premier fetch peu après le démarrage

    # ------------------------------------------------------------------ #
    def _add_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {COLORS['bg_input']}; color: {COLORS['text_muted']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 9px; padding: 1px 8px;"
            f" font-size: 10px; }}"
            f"QPushButton:hover {{ border-color: {COLORS['text_dim']}; color: {COLORS['text_main']}; }}"
        )

    def _pastille_style(self) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {COLORS['text_main']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 9px;"
            f" padding: 1px 9px 1px 6px; font-size: 10px; text-align: left; }}"
            f"QPushButton:hover {{ border-color: {COLORS['text_dim']}; }}"
        )

    # ------------------------------------------------------------------ #
    def _add_repo(self) -> None:
        ref, ok = QInputDialog.getText(
            self, "Suivre un dépôt GitHub",
            "URL ou owner/repo :\n(ex. blacksamdev/BBS-Desktoo)",
        )
        if not ok or not ref.strip():
            return
        parsed = github.parse_repo(ref)
        if not parsed:
            return
        key = f"{parsed[0]}/{parsed[1]}"
        if key in self._buttons:
            return
        self.settings.add_github_repo(key)
        btn = self._add_pastille(*parsed)
        self._poll(*parsed)

    def _add_pastille(self, owner: str, repo: str) -> QPushButton:
        key = f"{owner}/{repo}"
        btn = QPushButton(repo)
        btn.setIcon(_dot_icon(COLORS["text_dim"]))   # gris au départ (pas encore de statut)
        btn.setIconSize(QSize(11, 11))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._pastille_style())
        btn.setToolTip(f"{key} — clic : ouvrir Actions · clic droit : retirer")
        btn.clicked.connect(lambda _=False, o=owner, r=repo: self.open_url.emit(github.actions_url(o, r)))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda _pos, k=key: self._repo_menu(k))
        self._layout.insertWidget(self._layout.count() - 1, btn)
        self._buttons[key] = btn
        return btn

    def _repo_menu(self, key: str) -> None:
        menu = QMenu(self)
        menu.addAction("Rafraîchir", self.refresh_all)
        menu.addAction("Retirer", lambda: self._remove_repo(key))
        menu.exec(self.cursor().pos())

    def _remove_repo(self, key: str) -> None:
        self.settings.remove_github_repo(key)
        btn = self._buttons.pop(key, None)
        if btn is not None:
            btn.setParent(None)
            btn.deleteLater()

    # ------------------------------------------------------------------ #
    def refresh_all(self) -> None:
        token = self.settings.github_token()
        for key in list(self._buttons.keys()):
            owner, repo = key.split("/", 1)
            self._poll(owner, repo)

    def _poll(self, owner: str, repo: str) -> None:
        token = self.settings.github_token()
        worker = _PollWorker(owner, repo, token, self)
        worker.done.connect(self._on_status)
        worker.finished.connect(lambda w=worker: self._workers.remove(w) if w in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _on_status(self, key: str, result: dict) -> None:
        btn = self._buttons.get(key)
        if btn is None:
            return
        state = result.get("state", "error")
        color = _STATE_COLORS.get(state, COLORS["text_dim"])
        repo = key.split("/", 1)[1]
        btn.setText(repo)
        # Rond plein complet à la couleur du dernier build
        btn.setIcon(_dot_icon(color))
        btn.setIconSize(QSize(11, 11))
        btn.setStyleSheet(self._pastille_style())
        btn.setToolTip(f"{key} — {result.get('detail','')}\nClic : ouvrir Actions · clic droit : retirer")
        # Le clic ouvre le run précis (ou la page Actions)
        url = result.get("url") or github.actions_url(*key.split("/", 1))
        try:
            btn.clicked.disconnect()
        except TypeError:
            pass
        btn.clicked.connect(lambda _=False, u=url: self.open_url.emit(u))

    # ------------------------------------------------------------------ #
    def shutdown(self) -> None:
        self._timer.stop()
        for w in self._workers:
            w.quit()
            w.wait(500)
