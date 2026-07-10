# bbs_desktoo/ui/file_explorer.py
# BBS desktOO — explorateur de fichiers multi-arborescences.
#
# La colonne de gauche peut empiler plusieurs arborescences (split vertical),
# pour travailler sur deux projets en parallèle (ex. Desktoo en haut, Popcorn
# en bas). Bouton + pour ajouter une arborescence, × pour en retirer une.
#
# Chaque arborescence (_TreePane) émet :
#   - file_opened(path)        : double-clic sur un fichier
#   - terminal_here(path)      : « Placer le terminal ici » (clic droit)
#   - copy_path(path)          : « Copier le chemin » (clic droit)
#
# FileExplorer ré-émet ces signaux vers la fenêtre principale et conserve une
# interface compatible (set_root, file_opened).
#
# Note : QFileSystemModel a migré de QtWidgets (Qt5) vers QtGui (Qt6).

import os

from PyQt6.QtWidgets import (
    QTreeView, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QMenu, QApplication,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import pyqtSignal, QDir, QModelIndex, Qt

from bbs_desktoo.core.theme import COLORS


class _TreePane(QWidget):
    """Une arborescence sur un dossier, avec en-tête et menu contextuel."""

    file_opened = pyqtSignal(str)
    terminal_here = pyqtSignal(str)
    copy_path = pyqtSignal(str)
    close_requested = pyqtSignal(object)   # se transmet lui-même

    def __init__(self, root: str | None = None, closable: bool = False, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # En-tête : nom du dossier + bouton de fermeture (si autorisé)
        head = QWidget(self)
        head.setStyleSheet(f"background: {COLORS['bg_panel']};")
        h = QHBoxLayout(head)
        h.setContentsMargins(0, 0, 4, 0)
        h.setSpacing(0)
        self.header = QLabel("EXPLORER")
        self.header.setObjectName("sectionHeader")
        h.addWidget(self.header)
        h.addStretch()
        # Bouton de fermeture, toujours créé ; le conteneur le masque quand il
        # ne reste qu'une seule arborescence.
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Fermer cet explorateur")
        self.close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_dim']};"
            f" border: none; font-size: 15px; font-weight: 700; }}"
            f"QPushButton:hover {{ color: {COLORS['accent']}; }}"
        )
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        h.addWidget(self.close_btn)
        layout.addWidget(head)

        # Modèle + arbre
        self.model = QFileSystemModel(self)
        self.model.setRootPath("")
        self.model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )

        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(False)
        self.tree.setIndentation(14)
        for col in range(1, 4):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self._on_double_click)
        # Menu contextuel (clic droit)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.tree)

        if root:
            self.set_root(root)

    # ------------------------------------------------------------------ #
    def set_root(self, path: str) -> None:
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.header.setText(os.path.basename(path.rstrip("/")).upper() or "EXPLORER")
        self._root = path

    def _on_double_click(self, index: QModelIndex) -> None:
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_opened.emit(path)

    # ------------------------------------------------------------------ #
    def _on_context_menu(self, pos) -> None:
        index = self.tree.indexAt(pos)
        if index.isValid():
            path = self.model.filePath(index)
            # Pour « placer le terminal ici » : si c'est un fichier, on prend
            # son dossier parent.
            dir_path = path if self.model.isDir(index) else os.path.dirname(path)
        else:
            # Clic dans le vide -> racine de l'arborescence
            path = getattr(self, "_root", "")
            dir_path = path

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: {COLORS['bg_input']}; color: {COLORS['text_main']};"
            f" border: 1px solid {COLORS['border']}; }}"
            f"QMenu::item:selected {{ background: {COLORS['accent']}; }}"
        )
        act_term = menu.addAction("Placer le terminal ici")
        act_copy = menu.addAction("Copier le chemin")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen == act_term and dir_path:
            self.terminal_here.emit(dir_path)
        elif chosen == act_copy and path:
            self.copy_path.emit(path)


class FileExplorer(QWidget):
    """Conteneur d'arborescences empilées (split vertical)."""

    file_opened = pyqtSignal(str)
    terminal_here = pyqtSignal(str)
    copy_path = pyqtSignal(str)

    def __init__(self, root: str | None = None, parent=None):
        super().__init__(parent)
        self._panes: list[_TreePane] = []
        self._last_root = root

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barre d'en-tête du conteneur : titre + bouton « ajouter »
        bar = QWidget(self)
        bar.setStyleSheet(f"background: {COLORS['bg_panel']}; border-bottom: 1px solid {COLORS['border']};")
        b = QHBoxLayout(bar)
        b.setContentsMargins(8, 2, 6, 2)
        title = QLabel("EXPLORATEUR")
        title.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;"
        )
        b.addWidget(title)
        b.addStretch()
        self.add_btn = QPushButton("+ Explorateur")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setToolTip("Ajouter une arborescence pour un autre projet")
        self.add_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_input']}; color: {COLORS['text_muted']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 5px; padding: 1px 8px;"
            f" font-size: 10px; }}"
            f"QPushButton:hover {{ border-color: {COLORS['text_dim']}; color: {COLORS['text_main']}; }}"
        )
        self.add_btn.clicked.connect(self._on_add_clicked)
        b.addWidget(self.add_btn)
        layout.addWidget(bar)

        # Splitter vertical qui empile les arborescences
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.splitter, stretch=1)

        # Première arborescence (fermable comme les autres ; on empêche juste
        # de fermer la toute dernière restante).
        self._add_pane(root, closable=True)

    # ------------------------------------------------------------------ #
    def _add_pane(self, root: str | None, closable: bool) -> _TreePane:
        pane = _TreePane(root, closable=closable)
        pane.file_opened.connect(self.file_opened.emit)
        pane.terminal_here.connect(self.terminal_here.emit)
        pane.copy_path.connect(self.copy_path.emit)
        pane.close_requested.connect(self._remove_pane)
        self.splitter.addWidget(pane)
        self._panes.append(pane)
        self._update_close_buttons()
        return pane

    def _remove_pane(self, pane: _TreePane) -> None:
        if pane in self._panes and len(self._panes) > 1:
            self._panes.remove(pane)
            pane.setParent(None)
            pane.deleteLater()
            self._update_close_buttons()

    def _update_close_buttons(self) -> None:
        """Masque le × quand il ne reste qu'une arborescence (rien à fermer)."""
        only_one = len(self._panes) <= 1
        for p in self._panes:
            p.close_btn.setVisible(not only_one)

    # ------------------------------------------------------------------ #
    def _on_add_clicked(self) -> None:
        """Demande un dossier et ajoute une arborescence fermable."""
        from PyQt6.QtWidgets import QFileDialog
        start = self._last_root or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Ajouter un dossier à l'explorateur", start)
        if path:
            self._add_pane(path, closable=True)
            self._last_root = path

    # ------------------------------------------------------------------ #
    def set_root(self, path: str) -> None:
        """Définit la racine de la PREMIÈRE arborescence (compat. fenêtre principale)."""
        if self._panes:
            self._panes[0].set_root(path)
        self._last_root = path
