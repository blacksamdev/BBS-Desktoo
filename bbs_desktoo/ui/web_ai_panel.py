# bbs_desktoo/ui/web_ai_panel.py
# BBS desktOO — panneau IA web (zone haute de la colonne droite).
#
# Affiche un service d'IA web (claude.ai par défaut) dans un navigateur
# embarqué QWebEngineView. L'utilisateur écrit DANS la page, se connecte à son
# compte, copie-colle son code — logique « web assumée ».
#
# Le profil est PERSISTANT : cookies et session conservés entre les lancements
# (stockés sous ~/.config/blacksamdev/desktoo-web), donc pas de reconnexion à
# chaque ouverture.
#
# Note philosophie : ce panneau embarque Chromium (QtWebEngine). C'est un choix
# assumé pour l'usage perso — voir README.

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel,
)
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

from bbs_desktoo.core.theme import COLORS


# Services web proposés dans le sélecteur.
# ChatGPT retiré : OpenAI bloque activement les navigateurs embarqués
# (échec SSL/Cloudflare). Utilise le bouton ↗ pour l'ouvrir dans Firefox.
_SERVICES = {
    "Claude":  "https://claude.ai",
    "Gemini":  "https://gemini.google.com",
    "Mistral": "https://chat.mistral.ai",
}


class WebAIPanel(QWidget):
    """Navigateur embarqué vers un service d'IA web, profil persistant."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {COLORS['bg_panel']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Barre d'outils ----
        toolbar = QWidget(self)
        toolbar.setStyleSheet(f"border-bottom: 1px solid {COLORS['border']};")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(8, 5, 8, 5)
        tb.setSpacing(6)

        label = QLabel("IA WEB")
        label.setObjectName("sectionHeader")
        label.setContentsMargins(0, 0, 0, 0)
        tb.addWidget(label)

        self.service_combo = QComboBox()
        self.service_combo.addItems(_SERVICES.keys())
        self.service_combo.currentTextChanged.connect(self._on_service_changed)
        tb.addWidget(self.service_combo)

        tb.addStretch()

        self.reload_btn = self._tool_button("↻", "Recharger")
        self.reload_btn.clicked.connect(lambda: self.view.reload())
        tb.addWidget(self.reload_btn)

        self.home_btn = self._tool_button("⌂", "Accueil du service")
        self.home_btn.clicked.connect(self._go_home)
        tb.addWidget(self.home_btn)

        self.ext_btn = self._tool_button("↗", "Ouvrir dans le navigateur système")
        self.ext_btn.clicked.connect(self._open_external)
        tb.addWidget(self.ext_btn)

        layout.addWidget(toolbar)

        # ---- Profil persistant + vue web ----
        storage = os.path.expanduser("~/.config/blacksamdev/desktoo-web")
        os.makedirs(storage, exist_ok=True)
        self.profile = QWebEngineProfile("bbs-desktoo-web", self)
        self.profile.setPersistentStoragePath(storage)
        self.profile.setCachePath(storage)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        # User-Agent Chrome réaliste : par défaut QtWebEngine s'annonce comme
        # « QtWebEngine », que les services anti-bot (OpenAI/ChatGPT, Cloudflare)
        # détectent et bloquent. Se faire passer pour un Chrome standard
        # débloque l'authentification de ces services.
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )

        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(self.profile, self.view)
        self.view.setPage(self.page)
        layout.addWidget(self.view, stretch=1)

        self._current_service = "Claude"
        self._go_home()

    # ------------------------------------------------------------------ #
    def _tool_button(self, text: str, tip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedWidth(30)
        btn.setStyleSheet(
            f"""QPushButton {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                padding: 2px;
                font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {COLORS['text_dim']}; color: {COLORS['text_main']}; }}"""
        )
        return btn

    def _on_service_changed(self, name: str) -> None:
        self._current_service = name
        self._go_home()

    def _go_home(self) -> None:
        url = _SERVICES.get(self._current_service, "https://claude.ai")
        self.view.setUrl(QUrl(url))

    def _open_external(self) -> None:
        QDesktopServices.openUrl(self.view.url())

    # ------------------------------------------------------------------ #
    def load_url(self, url: str) -> None:
        """Charge une URL arbitraire (utilisé par les pastilles GitHub CI)."""
        self.view.setUrl(QUrl(url))

    def shutdown(self) -> None:
        """Détruit page puis vue avant le profil (ordre requis par QtWebEngine).

        Sans cet ordre, QtWebEngine émet un avertissement et peut crasher à la
        fermeture de la fenêtre.
        """
        try:
            self.view.setPage(None)
            self.page.deleteLater()
            self.view.deleteLater()
        except RuntimeError:
            pass
