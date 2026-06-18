# bbs_desktoo/ui/file_explorer.py
# BBS desktOO — explorateur de fichiers.
#
# QTreeView sur un QFileSystemModel racine sur le dossier ouvert. Émet un
# signal file_opened(path) au double-clic sur un fichier ; la fenêtre
# principale ouvre alors un onglet d'éditeur.
#
# Note : QFileSystemModel a migré de QtWidgets (Qt5) vers QtGui (Qt6).

from PyQt6.QtWidgets import QTreeView, QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import pyqtSignal, QDir, QModelIndex


class FileExplorer(QWidget):
    """Arborescence d'un dossier de travail."""

    file_opened = pyqtSignal(str)

    def __init__(self, root: str | None = None, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QLabel("EXPLORER")
        self.header.setObjectName("sectionHeader")
        layout.addWidget(self.header)

        self.model = QFileSystemModel(self)
        self.model.setRootPath("")
        # On masque les fichiers cachés par défaut (point initial)
        self.model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )

        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(False)
        self.tree.setIndentation(14)
        # On ne montre que le nom (colonnes taille/type/date masquées)
        for col in range(1, 4):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.tree)

        if root:
            self.set_root(root)

    # ------------------------------------------------------------------ #
    def set_root(self, path: str) -> None:
        """Recentre l'arborescence sur un dossier."""
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        # Le nom du dossier racine sert d'en-tête
        import os
        self.header.setText(os.path.basename(path.rstrip("/")).upper() or "EXPLORER")

    # ------------------------------------------------------------------ #
    def _on_double_click(self, index: QModelIndex) -> None:
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_opened.emit(path)
