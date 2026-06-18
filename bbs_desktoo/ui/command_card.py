# bbs_desktoo/ui/command_card.py
# BBS desktOO — carte de commande proposée par l'IA (Mode 2).
#
# Affiche une commande shell extraite de la réponse de l'IA, avec trois niveaux :
#   - SÛR      : bordure neutre, exécution au premier clic.
#   - ATTENTION (jaune) : sudo / install / push — repère visuel, premier clic.
#   - RISQUÉ   (rouge)  : rm -rf, dd, reset --hard… — double confirmation.
#
# Rien ne s'exécute sans clic sur Exécuter.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from bbs_desktoo.core.theme import COLORS
from bbs_desktoo.ai.commands import analyze_danger, analyze_caution


class CommandCard(QFrame):
    """Carte actionnable pour une commande proposée."""

    execute_requested = pyqtSignal(str)   # émis avec la commande à exécuter

    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.command = command
        self.dangers = analyze_danger(command)
        self.cautions = analyze_caution(command)
        self._armed = False   # double-confirmation des commandes rouges

        # Niveau et couleur de bordure
        if self.dangers:
            level, border, accent = "danger", COLORS["accent"], COLORS["accent"]
        elif self.cautions:
            level, border, accent = "caution", COLORS["yellow"], COLORS["yellow"]
        else:
            level, border, accent = "safe", COLORS["border"], COLORS["text_muted"]
        self._level = level

        self.setStyleSheet(
            f"""CommandCard {{
                background: {COLORS['bg_deep']};
                border: 1px solid {border};
                border-radius: 8px;
            }}"""
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # En-tête : libellé + badge de niveau
        head = QHBoxLayout()
        tag = QLabel("COMMANDE PROPOSÉE")
        tag.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; letter-spacing: 1px;"
        )
        head.addWidget(tag)
        head.addStretch()
        if level == "danger":
            badge = QLabel("⚠ RISQUÉ")
            badge.setStyleSheet(f"color: {COLORS['accent']}; font-size: 9px; font-weight: 700; letter-spacing: 1px;")
            head.addWidget(badge)
        elif level == "caution":
            badge = QLabel("⚠ ATTENTION")
            badge.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 9px; font-weight: 700; letter-spacing: 1px;")
            head.addWidget(badge)
        layout.addLayout(head)

        # La commande
        cmd_label = QLabel(command)
        cmd_label.setWordWrap(True)
        cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mono = QFont("JetBrains Mono", 10)
        mono.setFixedPitch(True)
        cmd_label.setFont(mono)
        cmd_label.setStyleSheet(
            f"""color: {COLORS['text_main']};
                background: {COLORS['bg_panel']};
                border-radius: 5px;
                padding: 7px 9px;"""
        )
        layout.addWidget(cmd_label)

        # Détail du niveau (rouge ou jaune)
        if level in ("danger", "caution"):
            reasons = self.dangers if level == "danger" else self.cautions
            color = COLORS["accent"] if level == "danger" else COLORS["yellow"]
            reason = QLabel("⚠ " + " · ".join(reasons))
            reason.setWordWrap(True)
            reason.setStyleSheet(f"color: {color}; font-size: 10px;")
            layout.addWidget(reason)

        # Boutons
        actions = QHBoxLayout()
        actions.addStretch()
        self.dismiss_btn = QPushButton("Ignorer")
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        self.exec_btn = QPushButton("▶ Exécuter")
        self.exec_btn.setObjectName("accent")
        self.exec_btn.clicked.connect(self._on_execute)
        actions.addWidget(self.dismiss_btn)
        actions.addWidget(self.exec_btn)
        layout.addLayout(actions)

    # ------------------------------------------------------------------ #
    def _on_execute(self) -> None:
        # Seules les commandes ROUGES exigent une double confirmation.
        if self._level == "danger" and not self._armed:
            self._armed = True
            self.exec_btn.setText("▶ Confirmer l'exécution")
            self.exec_btn.setToolTip(
                "Commande potentiellement destructrice. Clique à nouveau pour exécuter."
            )
            return
        self.execute_requested.emit(self.command)
        self._lock("✓ Exécutée")

    def _on_dismiss(self) -> None:
        self._lock("✕ Ignorée")

    def _lock(self, label: str) -> None:
        self.exec_btn.setEnabled(False)
        self.dismiss_btn.setEnabled(False)
        self.exec_btn.setText(label)
        self.setStyleSheet(
            f"""CommandCard {{
                background: {COLORS['bg_deep']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}"""
        )
