# bbs_desktoo/ui/main_window.py
# BBS desktOO — fenêtre principale.
#
# Assemble les quatre zones façon Cursor :
#
#   ┌──────────┬───────────────────────────┬──────────────────────┐
#   │ Explorer │  Éditeur (onglets)        │  Panneau IA          │
#   │          ├───────────────────────────┤  (≈ double largeur)  │
#   │          │  Terminal                 │                      │
#   └──────────┴───────────────────────────┴──────────────────────┘
#
# Deux QSplitter imbriqués :
#   - racine horizontal : Explorer | (centre) | IA
#   - centre vertical    : Éditeur | Terminal
#
# Tailles et géométrie persistées via QSettings entre sessions.

import os

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QFileDialog, QWidget, QVBoxLayout,
)
from PyQt6.QtCore import Qt

from bbs_desktoo.core.settings import Settings
from bbs_desktoo.ui.file_explorer import FileExplorer
from bbs_desktoo.ui.editor import BBSEditor
from bbs_desktoo.ui.terminal import BBSTerminal
from bbs_desktoo.ui.ai_panel import AIPanel
from bbs_desktoo.ui.web_ai_panel import WebAIPanel


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.setWindowTitle("BBS desktOO")
        self.resize(1400, 900)

        self._open_editors: dict[str, BBSEditor] = {}  # path -> éditeur

        self._build_menu()
        self._build_layout()
        self._restore_state()

    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        root = QSplitter(Qt.Orientation.Horizontal)

        # --- Gauche : explorateur ---
        self.explorer = FileExplorer()
        self.explorer.file_opened.connect(self.open_file)
        root.addWidget(self.explorer)

        # --- Centre : éditeur (onglets) + terminal, empilés ---
        center = QSplitter(Qt.Orientation.Vertical)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        center.addWidget(self.tabs)

        self.terminal = BBSTerminal()
        center.addWidget(self.terminal)
        center.setSizes([650, 200])
        self.center_splitter = center
        root.addWidget(center)

        # --- Droite : colonne IA, split vertical ---
        #     Haut : IA web (claude.ai embarqué) — logique copier-coller
        #     Bas  : IA locale (Ollama) — logique chat + injection terminal
        ai_column = QSplitter(Qt.Orientation.Vertical)

        self.web_ai = WebAIPanel()
        ai_column.addWidget(self.web_ai)

        self.ai_panel = AIPanel(self.settings)
        self.ai_panel.configure_requested.connect(self._configure_ai)
        self.ai_panel.command_execute.connect(self._on_ai_command)
        ai_column.addWidget(self.ai_panel)

        ai_column.setSizes([450, 450])
        self.ai_column = ai_column
        root.addWidget(ai_column)

        # Largeurs initiales : explorer / centre / IA
        # IA ≈ double d'un panneau latéral classique.
        root.setSizes([220, 780, 400])
        root.setStretchFactor(0, 0)
        root.setStretchFactor(1, 1)
        root.setStretchFactor(2, 0)

        self.root_splitter = root
        self.setCentralWidget(root)

    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        bar = self.menuBar()

        m_file = bar.addMenu("Fichier")
        m_file.addAction("Ouvrir un dossier…", self.open_folder)
        m_file.addAction("Enregistrer", self.save_current).setShortcut("Ctrl+S")
        m_file.addSeparator()
        m_file.addAction("Quitter", self.close).setShortcut("Ctrl+Q")

        m_view = bar.addMenu("Vue")
        m_view.addAction("Afficher/masquer le terminal", self._toggle_terminal)

        m_ai = bar.addMenu("IA")
        m_ai.addAction("Configurer le modèle…", self._configure_ai)

        bar.addMenu("Aide").addAction("À propos de BBS desktOO", self._about)

    # ------------------------------------------------------------------ #
    def open_folder(self) -> None:
        start = self.settings.last_folder() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Ouvrir un dossier", start)
        if path:
            self.set_workspace(path)

    def set_workspace(self, path: str) -> None:
        self.explorer.set_root(path)
        self.terminal.set_cwd(path)
        self.ai_panel.set_workdir(path)
        self.settings.set_last_folder(path)
        self.setWindowTitle(f"BBS desktOO — {os.path.basename(path)}")

    # ------------------------------------------------------------------ #
    def open_file(self, path: str) -> None:
        # Onglet déjà ouvert -> on y bascule
        if path in self._open_editors:
            editor = self._open_editors[path]
            self.tabs.setCurrentWidget(editor)
            return

        editor = BBSEditor()
        try:
            editor.load_file(path)
        except (OSError, UnicodeError) as exc:
            self.terminal._append(f"[desktOO] impossible d'ouvrir {path} : {exc}\n")
            return

        idx = self.tabs.addTab(editor, os.path.basename(path))
        self.tabs.setTabToolTip(idx, path)
        self.tabs.setCurrentIndex(idx)
        self._open_editors[path] = editor

    def save_current(self) -> None:
        editor = self.tabs.currentWidget()
        if isinstance(editor, BBSEditor) and editor.file_path:
            editor.save_file()
            self.terminal._append(f"[desktOO] enregistré : {editor.file_path}\n")

    # ------------------------------------------------------------------ #
    def _close_tab(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if isinstance(editor, BBSEditor) and editor.file_path in self._open_editors:
            del self._open_editors[editor.file_path]
        self.tabs.removeTab(index)

    def _on_tab_changed(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if isinstance(editor, BBSEditor):
            self.ai_panel.set_context_file(editor.file_path, editor.text())
        else:
            self.ai_panel.set_context_file(None)

    def _toggle_terminal(self) -> None:
        self.terminal.setVisible(not self.terminal.isVisible())

    # ------------------------------------------------------------------ #
    def _on_ai_command(self, command: str) -> None:
        """Injecte dans le terminal une commande validée depuis le panneau IA.

        La confirmation a déjà eu lieu côté CommandCard (et double confirmation
        pour les commandes à risque). Ici on exécute et on affiche un repère.
        """
        self.terminal._append(f"[desktOO ▶ IA] {command}\n")
        # Rend le terminal visible si masqué, pour que l'utilisateur voie le résultat
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        self.terminal.send_command(command)

    def _configure_ai(self) -> None:
        from bbs_desktoo.ui.ai_config_dialog import AIConfigDialog
        dialog = AIConfigDialog(self.settings, self)
        if dialog.exec():
            self.ai_panel.refresh_model_badge()
            provider = self.settings.ai_provider()
            model = self.settings.ai_model()
            self.terminal._append(
                f"[desktOO] Modèle IA configuré : {provider} / {model}\n"
            )

    def _about(self) -> None:
        self.terminal._append(
            "[desktOO] BBS desktOO v0.1.0 — IDE natif Linux, panneau IA agnostique.\n"
            "          GPL-3.0 — développé par blacksamdev — en hommage à "
            "Samuel Bellamy, capitaine du Whydah.\n"
        )

    # ------------------------------------------------------------------ #
    def _restore_state(self) -> None:
        geo = self.settings.window_geometry()
        if geo is not None:
            self.restoreGeometry(geo)
        last = self.settings.last_folder()
        if last and os.path.isdir(last):
            self.set_workspace(last)

    def closeEvent(self, event):
        self.settings.set_window_geometry(self.saveGeometry())
        self.web_ai.shutdown()
        self.terminal.shutdown()
        super().closeEvent(event)
