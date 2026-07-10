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
from bbs_desktoo.core.theme import COLORS
from bbs_desktoo.ui.file_explorer import FileExplorer
from bbs_desktoo.ui.editor import BBSEditor
from bbs_desktoo.ui.terminal import BBSTerminal
from bbs_desktoo.ui.ai_panel import AIPanel
from bbs_desktoo.ui.web_ai_panel import WebAIPanel
from bbs_desktoo.ui.github_status import GitHubStatus
from bbs_desktoo.ui.find_bar import FindBar


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.setWindowTitle("BBS desktOO")
        self.resize(1400, 900)

        self._open_editors: dict[str, BBSEditor] = {}  # path -> éditeur
        self._web_tabs: list = []                       # vues web ouvertes au centre

        self._build_menu()
        self._build_layout()
        self._restore_state()

    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        root = QSplitter(Qt.Orientation.Horizontal)

        # --- Gauche : explorateur ---
        self.explorer = FileExplorer()
        self.explorer.file_opened.connect(self.open_file)
        self.explorer.terminal_here.connect(self._terminal_here)
        self.explorer.copy_path.connect(self._copy_path)
        root.addWidget(self.explorer)

        # --- Centre : éditeur (onglets) + barre de recherche + terminal ---
        center = QSplitter(Qt.Orientation.Vertical)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Conteneur onglets + barre de recherche (Ctrl+F), masquée par défaut
        from PyQt6.QtWidgets import QVBoxLayout, QWidget as _QW
        self.find_bar = FindBar(self._current_editor_or_none)
        editor_zone = _QW()
        ez = QVBoxLayout(editor_zone)
        ez.setContentsMargins(0, 0, 0, 0)
        ez.setSpacing(0)
        ez.addWidget(self.tabs, stretch=1)
        ez.addWidget(self.find_bar)
        center.addWidget(editor_zone)

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

        m_edit = bar.addMenu("Édition")
        act_find = m_edit.addAction("Rechercher…", lambda: self.find_bar.open_bar())
        act_find.setShortcut("Ctrl+F")
        act_next = m_edit.addAction("Occurrence suivante", lambda: self.find_bar.find_next())
        act_next.setShortcut("F3")
        act_prev = m_edit.addAction("Occurrence précédente", lambda: self.find_bar.find_prev())
        act_prev.setShortcut("Shift+F3")

        m_view = bar.addMenu("Vue")
        m_view.addAction("Afficher/masquer le terminal", self._toggle_terminal)
        m_view.addSeparator()
        act_bigger = m_view.addAction("Police plus grande", lambda: self._zoom_editors(+1))
        act_bigger.setShortcut("Ctrl++")
        act_smaller = m_view.addAction("Police plus petite", lambda: self._zoom_editors(-1))
        act_smaller.setShortcut("Ctrl+-")
        act_reset = m_view.addAction("Police par défaut", lambda: self._set_editors_font(11))
        act_reset.setShortcut("Ctrl+0")

        m_ai = bar.addMenu("IA")
        m_ai.addAction("Configurer le modèle…", self._configure_ai)

        bar.addMenu("Aide").addAction("À propos de BBS desktOO", self._about)

        # Pastilles de statut CI GitHub, dans une barre d'outils dédiée sous le
        # menu (bien visible, sans collision avec les boutons de la fenêtre).
        # Clic sur une pastille -> ouvre la page Actions dans un onglet au centre.
        from PyQt6.QtWidgets import QToolBar, QLabel
        toolbar = QToolBar("CI")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            f"QToolBar {{ background: {COLORS['bg_panel']}; border-bottom: 1px solid {COLORS['border']}; padding: 2px 6px; spacing: 4px; }}"
        )
        ci_label = QLabel("CI  ")
        ci_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        toolbar.addWidget(ci_label)
        self.github_status = GitHubStatus(self.settings)
        self.github_status.open_url.connect(self._open_in_web_panel)
        toolbar.addWidget(self.github_status)
        self.addToolBar(toolbar)

    def _open_in_web_panel(self, url: str) -> None:
        """Ouvre une URL (page Actions GitHub) dans un onglet web au centre."""
        self.open_web_tab(url, "GitHub Actions")

    def open_web_tab(self, url: str, title: str) -> None:
        """Crée un onglet web au centre, à côté des fichiers de code.

        La vue partage le profil persistant du panneau web (mêmes cookies, donc
        session GitHub conservée si tu es connecté). Seuls http/https acceptés.
        """
        if not url.startswith(("http://", "https://")):
            return
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEnginePage
        from PyQt6.QtCore import QUrl

        view = QWebEngineView()
        page = QWebEnginePage(self.web_ai.profile, view)
        view.setPage(page)
        view.setUrl(QUrl(url))

        idx = self.tabs.addTab(view, title)
        self.tabs.setTabToolTip(idx, url)
        self.tabs.setCurrentIndex(idx)
        self._web_tabs.append(view)

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
    # Garde-fous d'ouverture : fichiers binaires refusés (charabia inutile),
    # fichiers volumineux sur confirmation (QScintilla charge tout en mémoire,
    # un très gros fichier gèle l'interface).
    BIG_FILE_BYTES = 8 * 1024 * 1024   # 8 Mo

    @staticmethod
    def _looks_binary(path: str) -> bool:
        """Heuristique : un octet nul dans les premiers Ko => binaire."""
        try:
            with open(path, "rb") as fh:
                return b"\x00" in fh.read(8192)
        except OSError:
            return False

    def _check_openable(self, path: str) -> bool:
        if self._looks_binary(path):
            self.terminal._append_plain(
                f"[desktOO] fichier binaire, non ouvert : {path}\n"
            )
            return False
        try:
            size = os.path.getsize(path)
        except OSError:
            return True
        if size > self.BIG_FILE_BYTES:
            from PyQt6.QtWidgets import QMessageBox
            mo = size / (1024 * 1024)
            rep = QMessageBox.question(
                self, "Fichier volumineux",
                f"{os.path.basename(path)} fait {mo:.1f} Mo.\n"
                "L'ouvrir peut ralentir l'éditeur. Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return rep == QMessageBox.StandardButton.Yes
        return True

    def open_file(self, path: str) -> None:
        # Onglet déjà ouvert -> on y bascule
        if path in self._open_editors:
            editor = self._open_editors[path]
            self.tabs.setCurrentWidget(editor)
            return

        if not self._check_openable(path):
            return

        editor = BBSEditor(font_size=self.settings.editor_font_size())
        editor.font_size_changed.connect(self._on_editor_font_changed)
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
        widget = self.tabs.widget(index)
        if isinstance(widget, BBSEditor) and widget.file_path in self._open_editors:
            del self._open_editors[widget.file_path]
        elif widget in self._web_tabs:
            # Onglet web : détruire la page avant la vue (ordre QtWebEngine)
            self._web_tabs.remove(widget)
            try:
                widget.setPage(None)
                widget.deleteLater()
            except RuntimeError:
                pass
        self.tabs.removeTab(index)

    def _on_tab_changed(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if isinstance(editor, BBSEditor):
            self.ai_panel.set_context_file(editor.file_path, editor.text())
        else:
            self.ai_panel.set_context_file(None)

    def _terminal_here(self, path: str) -> None:
        """« Placer le terminal ici » : positionne le terminal dans le dossier."""
        if not self.terminal.isVisible():
            self.terminal.setVisible(True)
        self.terminal.set_cwd(path)
        self.terminal._append_plain(f"[desktOO] terminal placé dans : {path}\n")

    def _copy_path(self, path: str) -> None:
        """« Copier le chemin » : met le chemin dans le presse-papier."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(path)
        self.terminal._append_plain(f"[desktOO] chemin copié : {path}\n")

    def _toggle_terminal(self) -> None:
        self.terminal.setVisible(not self.terminal.isVisible())

    # ------------------------------------------------------------------ #
    def _current_editor_or_none(self):
        """L'éditeur de l'onglet actif, ou None (onglet web, aucun onglet)."""
        w = self.tabs.currentWidget()
        return w if isinstance(w, BBSEditor) else None

    def _all_editors(self) -> list:
        return [self.tabs.widget(i) for i in range(self.tabs.count())
                if isinstance(self.tabs.widget(i), BBSEditor)]

    def _zoom_editors(self, delta: int) -> None:
        """Augmente/diminue la police de tous les éditeurs ouverts."""
        size = self.settings.editor_font_size() + delta
        self._set_editors_font(size)

    def _set_editors_font(self, size: int) -> None:
        for ed in self._all_editors():
            ed.set_font_size(size)
        # Mémorise la taille effective (bornée par l'éditeur)
        editors = self._all_editors()
        effective = editors[0].font_size() if editors else size
        self.settings.set_editor_font_size(effective)

    def _on_editor_font_changed(self, size: int) -> None:
        """Un éditeur a zoomé (Ctrl+molette) : propager aux autres + mémoriser."""
        self.settings.set_editor_font_size(size)
        for ed in self._all_editors():
            if ed.font_size() != size:
                ed.set_font_size(size)

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
        self.github_status.shutdown()
        # Détruire les pages des onglets web AVANT de libérer le profil partagé.
        for view in self._web_tabs:
            try:
                view.setPage(None)
                view.deleteLater()
            except RuntimeError:
                pass
        self._web_tabs.clear()
        self.web_ai.shutdown()
        self.terminal.shutdown()
        super().closeEvent(event)
