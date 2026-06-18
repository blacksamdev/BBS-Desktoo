# bbs_desktoo/ui/editor.py
# BBS desktOO — éditeur de code basé sur QScintilla.
#
# Coloration syntaxique selon l'extension, numéros de ligne, ligne courante
# surlignée, thème BBS appliqué au lexer.

import os

from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython,
    QsciLexerJavaScript,
    QsciLexerBash,
    QsciLexerCPP,
    QsciLexerMarkdown,
    QsciLexerHTML,
    QsciLexerJSON,
)
from PyQt6.QtGui import QColor, QFont

from bbs_desktoo.core.theme import COLORS


# Association extension -> classe de lexer QScintilla
_LEXERS = {
    ".py":   QsciLexerPython,
    ".js":   QsciLexerJavaScript,
    ".jsx":  QsciLexerJavaScript,
    ".ts":   QsciLexerJavaScript,
    ".sh":   QsciLexerBash,
    ".bash": QsciLexerBash,
    ".c":    QsciLexerCPP,
    ".h":    QsciLexerCPP,
    ".cpp":  QsciLexerCPP,
    ".hpp":  QsciLexerCPP,
    ".md":   QsciLexerMarkdown,
    ".html": QsciLexerHTML,
    ".htm":  QsciLexerHTML,
    ".json": QsciLexerJSON,
}


class BBSEditor(QsciScintilla):
    """Éditeur mono-fichier. Un onglet de l'éditeur central en instancie un."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path: str | None = None
        self._font = QFont("JetBrains Mono", 11)
        self._font.setFixedPitch(True)
        self.setFont(self._font)
        self._configure()

    # ------------------------------------------------------------------ #
    def _configure(self) -> None:
        c = COLORS

        # Couleurs de base de la zone d'édition
        self.setPaper(QColor(c["bg_deep"]))
        self.setColor(QColor(c["text_main"]))

        # --- Marge des numéros de ligne ---
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginsBackgroundColor(QColor(c["bg_deep"]))
        self.setMarginsForegroundColor(QColor(c["text_dim"]))

        # --- Ligne courante surlignée ---
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#1E2228"))
        self.setCaretForegroundColor(QColor(c["accent"]))
        self.setCaretWidth(2)

        # --- Sélection ---
        self.setSelectionBackgroundColor(QColor(c["accent"]))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))

        # --- Indentation ---
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setIndentationGuides(True)

        # --- Confort ---
        self.setUtf8(True)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor(c["bg_input"]))
        self.setMatchedBraceForegroundColor(QColor(c["accent"]))

    # ------------------------------------------------------------------ #
    def _apply_lexer_theme(self, lexer) -> None:
        """Applique la palette BBS au lexer (fond, défaut, commentaires, chaînes)."""
        c = COLORS
        lexer.setDefaultPaper(QColor(c["bg_deep"]))
        lexer.setDefaultColor(QColor(c["text_main"]))
        lexer.setFont(self._font)
        lexer.setPaper(QColor(c["bg_deep"]))  # fond uniforme sur tous les styles

        # Styles communs récurrents (indices stables d'un lexer à l'autre
        # pour Python ; on reste prudent et on ne touche qu'aux plus fiables).
        if isinstance(lexer, QsciLexerPython):
            lexer.setColor(QColor("#CC7ADB"), QsciLexerPython.Keyword)
            lexer.setColor(QColor("#4EC94E"), QsciLexerPython.DoubleQuotedString)
            lexer.setColor(QColor("#4EC94E"), QsciLexerPython.SingleQuotedString)
            lexer.setColor(QColor("#4EC94E"), QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(QColor("#4EC94E"), QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(QColor("#555B63"), QsciLexerPython.Comment)
            lexer.setColor(QColor("#555B63"), QsciLexerPython.CommentBlock)
            lexer.setColor(QColor("#5B9BD5"), QsciLexerPython.FunctionMethodName)
            lexer.setColor(QColor("#5B9BD5"), QsciLexerPython.ClassName)
            lexer.setColor(QColor("#D4A843"), QsciLexerPython.Number)
            lexer.setColor(QColor("#E87D3E"), QsciLexerPython.Decorator)

    # ------------------------------------------------------------------ #
    def load_file(self, path: str) -> None:
        """Charge un fichier dans l'éditeur et applique le lexer adéquat."""
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            self.setText(fh.read())
        self.file_path = path

        ext = os.path.splitext(path)[1].lower()
        lexer_cls = _LEXERS.get(ext)
        if lexer_cls is not None:
            lexer = lexer_cls(self)
            self._apply_lexer_theme(lexer)
            self.setLexer(lexer)
        else:
            self.setLexer(None)
            self.setColor(QColor(COLORS["text_main"]))
            self.setPaper(QColor(COLORS["bg_deep"]))

    def save_file(self, path: str | None = None) -> str:
        """Sauvegarde le contenu. Retourne le chemin écrit."""
        target = path or self.file_path
        if target is None:
            raise ValueError("Aucun chemin de fichier associé à cet éditeur.")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(self.text())
        self.file_path = target
        return target
