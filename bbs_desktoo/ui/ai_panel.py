# bbs_desktoo/ui/ai_panel.py
# BBS desktOO — panneau IA (v0.3.0 : Chat + Mode injection terminal).
#
# Deux modes, sélectionnables en haut du panneau :
#   - CHAT     : conversation classique sur le code.
#   - COMMANDE : l'IA propose des commandes shell dans des blocs ```bash,
#                que desktOO transforme en cartes actionnables (Exécuter /
#                Ignorer), avec avertissement renforcé pour les commandes
#                dangereuses. Rien ne s'exécute sans clic explicite.
#
# La zone de conversation est un conteneur défilant (QScrollArea) qui accepte
# bulles de texte ET widgets CommandCard.
#
# Philosophie BBS : l'outil est gratuit, l'utilisateur branche son modèle.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFrame, QScrollArea, QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal

from bbs_desktoo.core.theme import COLORS
from bbs_desktoo.ai.base import AIError
from bbs_desktoo.ai.worker import build_provider, StreamWorker
from bbs_desktoo.ai.commands import extract_commands
from bbs_desktoo.ui.command_card import CommandCard


class ChatInput(QPlainTextEdit):
    """Champ de saisie : Entrée envoie, Maj+Entrée insère un saut de ligne."""

    submitted = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)   # saut de ligne
            else:
                self.submitted.emit()           # envoi
                return
        else:
            super().keyPressEvent(event)


SYSTEM_CHAT = (
    "Tu es l'assistant intégré à BBS desktOO, un IDE natif Linux (bash, KDE Neon) "
    "doté d'un terminal intégré. Tu PEUX proposer des commandes shell : desktOO les "
    "exécutera pour l'utilisateur après sa confirmation. "
    "Ne dis JAMAIS que tu n'as pas accès au système de fichiers ou que tu ne peux pas "
    "exécuter de commandes — c'est faux, desktOO s'en charge. "
    "Fais exactement ce qui est demandé : si on demande de LISTER, utilise ls/find sur "
    "l'existant, ne crée rien. Utilise le dossier de travail fourni en contexte. "
    "Quand une demande se résout par une commande, donne-la dans un bloc ```bash. "
    "Sinon, discute du code de façon directe et technique, sans bla-bla."
)

SYSTEM_COMMAND = (
    "Tu es l'assistant terminal de BBS desktOO, un IDE natif Linux (bash, KDE Neon). "
    "L'utilisateur décrit une intention ; tu fournis la ou les commandes shell. "
    "Règles STRICTES :\n"
    "- Donne DIRECTEMENT la commande, sans préambule ni justification. Ne dis JAMAIS "
    "que tu n'as pas accès au système : desktOO exécutera la commande pour l'utilisateur.\n"
    "- Fais EXACTEMENT ce qui est demandé, rien de plus. Si on demande de LISTER, utilise "
    "ls/find sur l'existant — ne crée RIEN. Ne touch/mkdir/écris que si c'est explicitement demandé.\n"
    "- N'invente pas de chemins. Utilise le dossier de travail fourni en contexte ; les chemins "
    "relatifs partent de là.\n"
    "- Mets CHAQUE commande dans un bloc ```bash distinct, au plus une phrase d'explication courte.\n"
    "- Si une commande est destructrice, signale-le en une ligne.\n"
    "- Si l'intention est vraiment ambiguë, pose UNE question précise au lieu de deviner."
)


class AIPanel(QWidget):
    """Panneau IA : modes Chat et Commande (injection terminal)."""

    configure_requested = pyqtSignal()
    command_execute = pyqtSignal(str)   # commande validée -> terminal

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setStyleSheet(f"background: {COLORS['bg_panel']};")

        self._history: list[dict] = []
        self._context_path: str | None = None
        self._context_text: str | None = None
        self._workdir: str | None = None
        self._worker: StreamWorker | None = None
        self._streaming_buffer = ""
        self._current_bubble: QLabel | None = None
        self._mode = "chat"   # "chat" | "command"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_mode_bar())
        layout.addWidget(self._build_chat_area(), stretch=1)
        layout.addWidget(self._build_context_bar())
        layout.addWidget(self._build_input_area())

        self._add_welcome()
        self.refresh_model_badge()

    # ------------------------------------------------------------------ #
    #  Construction de l'UI
    # ------------------------------------------------------------------ #
    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setStyleSheet(f"border-bottom: 1px solid {COLORS['border']};")
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 6, 10, 6)

        title = QLabel("IA")
        title.setObjectName("sectionHeader")
        title.setContentsMargins(0, 0, 0, 0)
        h.addWidget(title)
        h.addStretch()

        self.model_badge = QPushButton()
        self.model_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_badge.setStyleSheet(
            f"""QPushButton {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ border-color: {COLORS['text_dim']}; }}"""
        )
        self.model_badge.clicked.connect(self.configure_requested.emit)
        h.addWidget(self.model_badge)
        return header

    def _build_mode_bar(self) -> QWidget:
        bar = QWidget(self)
        bar.setStyleSheet(f"border-bottom: 1px solid {COLORS['border']};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(6)

        self.mode_group = QButtonGroup(self)
        self.btn_chat = self._mode_button("Chat", "chat", checked=True)
        self.btn_command = self._mode_button("Commande", "command")
        self.mode_group.addButton(self.btn_chat)
        self.mode_group.addButton(self.btn_command)
        lay.addWidget(self.btn_chat)
        lay.addWidget(self.btn_command)
        lay.addStretch()

        self._mode_hint = QLabel("Conversation libre sur le code")
        self._mode_hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        lay.addWidget(self._mode_hint)
        return bar

    def _mode_button(self, label: str, mode: str, checked: bool = False) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._set_mode(mode))
        btn.setStyleSheet(
            f"""QPushButton {{
                background: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 3px 12px;
                font-size: 11px;
            }}
            QPushButton:checked {{
                background: {COLORS['accent']};
                color: #FFFFFF;
                border-color: {COLORS['accent']};
                font-weight: 700;
            }}"""
        )
        return btn

    def _build_chat_area(self) -> QScrollArea:
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"background: {COLORS['bg_panel']}; border: none;")

        self.messages = QWidget()
        self.messages.setStyleSheet(f"background: {COLORS['bg_panel']};")
        self.msg_layout = QVBoxLayout(self.messages)
        self.msg_layout.setContentsMargins(10, 10, 10, 10)
        self.msg_layout.setSpacing(8)
        self.msg_layout.addStretch()   # pousse les messages vers le haut

        self.scroll.setWidget(self.messages)
        return self.scroll

    def _build_context_bar(self) -> QFrame:
        ctx = QFrame(self)
        ctx.setStyleSheet(
            f"background: {COLORS['bg_deep']}; "
            f"border-top: 1px solid {COLORS['border']}; "
            f"border-bottom: 1px solid {COLORS['border']};"
        )
        c = QHBoxLayout(ctx)
        c.setContentsMargins(12, 5, 12, 5)
        ctx_label = QLabel("Contexte")
        ctx_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self.context_chip = QLabel("aucun fichier")
        self.context_chip.setStyleSheet(
            f"""color: {COLORS['text_muted']};
                background: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 9px;
                padding: 2px 9px;
                font-size: 10px;"""
        )
        c.addWidget(ctx_label)
        c.addStretch()
        c.addWidget(self.context_chip)
        return ctx

    def _build_input_area(self) -> QWidget:
        input_wrap = QWidget(self)
        iw = QVBoxLayout(input_wrap)
        iw.setContentsMargins(10, 8, 10, 10)
        iw.setSpacing(6)

        self.input = ChatInput(input_wrap)
        self.input.setPlaceholderText("Pose une question sur ton code…")
        self.input.setFixedHeight(72)
        self.input.setStyleSheet(
            f"""background: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 8px;
                color: {COLORS['text_main']};
                font-size: 12px;"""
        )
        self.input.submitted.connect(self._on_send)
        iw.addWidget(self.input)

        actions = QHBoxLayout()
        hint = QLabel("⏎ envoyer · ⇧⏎ saut de ligne")
        hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self.send_btn = QPushButton("Envoyer")
        self.send_btn.setObjectName("accent")
        self.send_btn.clicked.connect(self._on_send)
        actions.addWidget(hint)
        actions.addStretch()
        actions.addWidget(self.send_btn)
        iw.addLayout(actions)
        return input_wrap

    # ------------------------------------------------------------------ #
    #  Mode
    # ------------------------------------------------------------------ #
    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "command":
            self._mode_hint.setText("L'IA propose des commandes à exécuter")
            self.input.setPlaceholderText("Décris ce que tu veux faire (ex. annule mon dernier commit)…")
        else:
            self._mode_hint.setText("Conversation libre sur le code")
            self.input.setPlaceholderText("Pose une question sur ton code…")
        # Le changement de mode repart sur une conversation neuve
        self._history.clear()

    # ------------------------------------------------------------------ #
    #  État affiché
    # ------------------------------------------------------------------ #
    def refresh_model_badge(self) -> None:
        provider = self.settings.ai_provider()
        model = self.settings.ai_model()
        self.model_badge.setText(f"● {model or provider}  ▾")

    def set_context_file(self, path: str | None, text: str | None = None) -> None:
        self._context_path = path
        self._context_text = text
        if path:
            import os
            self.context_chip.setText(os.path.basename(path))
        else:
            self.context_chip.setText("aucun fichier")

    def set_workdir(self, path: str | None) -> None:
        self._workdir = path

    # ------------------------------------------------------------------ #
    #  Insertion de contenu dans le flux de messages
    # ------------------------------------------------------------------ #
    def _insert_widget(self, w: QWidget) -> None:
        # Insère avant le stretch final
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, w)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        # Différé : laisse Qt recalculer la hauteur du contenu avant de scroller,
        # sinon maximum() est encore l'ancienne valeur et les cartes/bulles
        # fraîchement insérées restent sous le pli.
        from PyQt6.QtCore import QTimer
        def _do():
            sb = self.scroll.verticalScrollBar()
            sb.setValue(sb.maximum())
        QTimer.singleShot(0, _do)

    def _add_welcome(self) -> None:
        lbl = QLabel(
            "BBS desktOO — IA locale (Ollama).\n\n"
            "Dès que l'IA propose une commande dans un bloc bash, "
            "un bouton ▶ Exécuter apparaît pour l'envoyer au terminal "
            "(avec confirmation, et double confirmation si risqué).\n\n"
            "Mode Chat : discussion libre.\n"
            "Mode Commande : l'IA va droit au but sur les commandes shell."
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; padding: 4px;")
        self._insert_widget(lbl)

    def _add_bubble(self, role: str, text: str) -> QLabel:
        color = COLORS["accent"] if role == "user" else "#5B9BD5"
        role_txt = "TOI" if role == "user" else "ASSISTANT"
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tag = QLabel(role_txt)
        tag.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 700; letter-spacing: 1px;"
        )
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bg = (f"rgba(225,29,46,0.1)" if role == "user" else COLORS["bg_input"])
        body.setStyleSheet(
            f"""color: {COLORS['text_main'] if role == 'user' else COLORS['text_muted']};
                background: {bg};
                border-radius: 6px;
                padding: 7px 9px;
                font-size: 12px;"""
        )
        v.addWidget(tag)
        v.addWidget(body)
        self._insert_widget(wrap)
        return body

    def _add_error(self, message: str) -> None:
        lbl = QLabel("⚠ " + message)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"""color: {COLORS['accent']};
                background: {COLORS['bg_deep']};
                border: 1px solid {COLORS['accent']};
                border-radius: 6px;
                padding: 7px 9px;
                font-size: 11px;"""
        )
        self._insert_widget(lbl)

    # ------------------------------------------------------------------ #
    #  Envoi / streaming
    # ------------------------------------------------------------------ #
    def _on_send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text or self._worker is not None:
            return

        try:
            provider = build_provider(self.settings)
        except AIError as exc:
            self._add_bubble("user", text)
            self.input.clear()
            self._add_error(str(exc))
            return

        self._add_bubble("user", text)
        self.input.clear()

        # Construit le message enrichi du contexte
        content = self._compose_message(text)
        self._history.append({"role": "user", "content": content})

        system = SYSTEM_COMMAND if self._mode == "command" else SYSTEM_CHAT

        self._streaming_buffer = ""
        self._current_bubble = self._add_bubble("assistant", "▍")

        self._worker = StreamWorker(provider, list(self._history), system=system, parent=self)
        self._worker.token.connect(self._on_token)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("…")
        self._worker.start()

    def _compose_message(self, text: str) -> str:
        parts = []
        if self._workdir:
            parts.append(f"Dossier de travail : {self._workdir}")
        if self._context_text:
            import os
            name = os.path.basename(self._context_path or "fichier")
            parts.append(f"Fichier courant ({name}) :\n```\n{self._context_text}\n```")
        parts.append(text)
        return "\n\n".join(parts)

    def _on_token(self, chunk: str) -> None:
        self._streaming_buffer += chunk
        if self._current_bubble is not None:
            self._current_bubble.setText(self._streaming_buffer)
        self._scroll_to_bottom()

    def _on_finished(self) -> None:
        if self._streaming_buffer:
            self._history.append({"role": "assistant", "content": self._streaming_buffer})
            # Tout bloc ```bash devient actionnable, quel que soit le mode.
            # Le mode ne change que le ton du prompt système, pas la possibilité
            # d'exécuter une commande proposée.
            self._spawn_command_cards(self._streaming_buffer)
        self._teardown_worker()

    def _spawn_command_cards(self, text: str) -> None:
        for cmd in extract_commands(text):
            card = CommandCard(cmd)
            card.execute_requested.connect(self.command_execute.emit)
            self._insert_widget(card)

    def _on_error(self, message: str) -> None:
        self._add_error(message)
        if self._history and self._history[-1]["role"] == "user":
            self._history.pop()
        self._teardown_worker()

    def _teardown_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._current_bubble = None
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Envoyer")
