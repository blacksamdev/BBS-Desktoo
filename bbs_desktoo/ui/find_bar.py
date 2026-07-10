# bbs_desktoo/ui/find_bar.py
# BBS desktOO — barre de recherche dans le fichier courant (Ctrl+F).
#
# Petite barre horizontale au-dessus du terminal : champ de recherche,
# précédent/suivant, sensibilité à la casse, fermeture (Échap ou ×).
# La recherche s'appuie sur QScintilla (findFirst, avec bouclage) et agit
# sur l'éditeur actif fourni par la fenêtre principale via un callable.
#
# Comportement :
#   - la frappe relance la recherche depuis le début de la sélection (live) ;
#   - Entrée = occurrence suivante, Maj+Entrée = précédente ;
#   - champ teinté en rouge si aucune occurrence ;
#   - Échap referme la barre et rend le focus à l'éditeur.

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from bbs_desktoo.core.theme import COLORS


class FindBar(QWidget):
    """Barre de recherche compacte, masquée par défaut."""

    def __init__(self, current_editor, parent=None):
        """current_editor : callable qui renvoie le BBSEditor actif (ou None)."""
        super().__init__(parent)
        self._current_editor = current_editor

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(6)

        lab = QLabel("Rechercher")
        lab.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        lay.addWidget(lab)

        self.field = QLineEdit(self)
        self.field.setPlaceholderText("texte à trouver…")
        self.field.textChanged.connect(self._on_text_changed)
        self.field.returnPressed.connect(self.find_next)
        lay.addWidget(self.field, stretch=1)

        self.prev_btn = self._btn("↑", "Occurrence précédente (Maj+Entrée / Maj+F3)")
        self.prev_btn.clicked.connect(self.find_prev)
        lay.addWidget(self.prev_btn)

        self.next_btn = self._btn("↓", "Occurrence suivante (Entrée / F3)")
        self.next_btn.clicked.connect(self.find_next)
        lay.addWidget(self.next_btn)

        self.case_box = QCheckBox("Aa")
        self.case_box.setToolTip("Sensible à la casse")
        self.case_box.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        self.case_box.stateChanged.connect(self._on_text_changed)
        lay.addWidget(self.case_box)

        close_btn = self._btn("×", "Fermer (Échap)")
        close_btn.clicked.connect(self.close_bar)
        lay.addWidget(close_btn)

        self.setStyleSheet(
            f"FindBar {{ background: {COLORS['bg_panel']};"
            f" border-top: 1px solid {COLORS['border']}; }}"
        )
        self._field_style_ok = self.field.styleSheet()
        self.hide()

    # ------------------------------------------------------------------ #
    def _btn(self, label: str, tip: str) -> QPushButton:
        b = QPushButton(label)
        b.setFixedSize(24, 22)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_input']}; color: {COLORS['text_muted']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 4px; font-size: 12px; }}"
            f"QPushButton:hover {{ color: {COLORS['text_main']}; border-color: {COLORS['text_dim']}; }}"
        )
        return b

    # ------------------------------------------------------------------ #
    def open_bar(self) -> None:
        """Affiche la barre et met le focus dans le champ.

        Si l'éditeur a une sélection, elle pré-remplit le champ (réflexe
        habituel des IDE).
        """
        ed = self._current_editor()
        if ed is not None and ed.hasSelectedText():
            sel = ed.selectedText()
            if sel and "\n" not in sel:
                self.field.setText(sel)
        self.show()
        self.field.setFocus()
        self.field.selectAll()

    def close_bar(self) -> None:
        self.hide()
        ed = self._current_editor()
        if ed is not None:
            ed.setFocus()

    # ------------------------------------------------------------------ #
    def _mark_not_found(self, found: bool) -> None:
        if found:
            self.field.setStyleSheet(self._field_style_ok)
        else:
            self.field.setStyleSheet(
                f"QLineEdit {{ border: 1px solid {COLORS['accent']}; }}"
            )

    def _search(self, forward: bool, from_selection_start: bool = False) -> None:
        ed = self._current_editor()
        text = self.field.text()
        if ed is None or not text:
            self._mark_not_found(True)
            return
        # Pour repartir de la sélection (frappe live) ou chercher en arrière,
        # on replace le curseur au début de la sélection courante — sinon
        # QScintilla retrouve l'occurrence déjà sélectionnée.
        if (from_selection_start or not forward) and ed.hasSelectedText():
            line, col, _, _ = ed.getSelection()
            ed.setCursorPosition(line, col)
        found = ed.findFirst(
            text,
            False,                          # pas de regex
            self.case_box.isChecked(),      # casse
            False,                          # mot entier : non
            True,                           # bouclage en fin de fichier
            forward,
        )
        self._mark_not_found(found)

    def _on_text_changed(self) -> None:
        self._search(forward=True, from_selection_start=True)

    def find_next(self) -> None:
        if not self.isVisible():
            self.open_bar()
            return
        self._search(forward=True)

    def find_prev(self) -> None:
        if not self.isVisible():
            self.open_bar()
            return
        self._search(forward=False)

    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.find_prev()
            return
        super().keyPressEvent(event)
