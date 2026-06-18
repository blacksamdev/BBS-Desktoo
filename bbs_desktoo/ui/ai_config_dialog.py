# bbs_desktoo/ui/ai_config_dialog.py
# BBS desktOO — boîte de dialogue de configuration du modèle IA.
#
# Choix du provider, saisie de la clé (stockée via QSettings, hors dépôt),
# choix du modèle. Pour Ollama : hôte + détection des modèles installés.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFormLayout,
)
from PyQt6.QtCore import Qt

from bbs_desktoo.core.theme import COLORS


# Modèles proposés par défaut dans le sélecteur (l'utilisateur peut saisir
# librement un autre identifiant).
_PRESETS = {
    "claude": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "ollama": ["mistral", "qwen2.5-coder", "llama3.1", "deepseek-coder-v2"],
}

_PROVIDER_LABELS = {
    "claude": "Claude (Anthropic)",
    "openai": "OpenAI",
    "ollama": "Ollama (local)",
}


class AIConfigDialog(QDialog):

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Configurer le modèle IA")
        self.setMinimumWidth(440)
        self.setStyleSheet(f"background: {COLORS['bg_panel']}; color: {COLORS['text_main']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(12)

        intro = QLabel(
            "L'outil est gratuit. Le modèle est à toi — branche ton propre accès.\n"
            "La clé est stockée localement (QSettings), jamais dans le dépôt."
        )
        intro.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(10)

        # --- Provider ---
        self.provider_combo = QComboBox()
        for key, lbl in _PROVIDER_LABELS.items():
            self.provider_combo.addItem(lbl, key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow(self._lbl("Provider"), self.provider_combo)

        # --- Clé API ---
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-… (vide pour Ollama)")
        form.addRow(self._lbl("Clé API"), self.key_edit)

        # --- Modèle (éditable) ---
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        form.addRow(self._lbl("Modèle"), self.model_combo)

        # --- Hôte Ollama ---
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("http://localhost:11434")
        self.host_row_label = self._lbl("Hôte Ollama")
        form.addRow(self.host_row_label, self.host_edit)

        layout.addLayout(form)

        # --- Boutons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Enregistrer")
        save.setObjectName("accent")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

        self._load_current()

    # ------------------------------------------------------------------ #
    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        return lbl

    def _load_current(self) -> None:
        provider = self.settings.ai_provider()
        idx = self.provider_combo.findData(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self._on_provider_changed()
        # Restaure le modèle enregistré s'il existe
        current_model = self.settings.ai_model()
        if current_model:
            i = self.model_combo.findText(current_model)
            if i >= 0:
                self.model_combo.setCurrentIndex(i)
            else:
                self.model_combo.setEditText(current_model)
        self.host_edit.setText(self.settings.ollama_host())

    def _on_provider_changed(self) -> None:
        provider = self.provider_combo.currentData()

        # Modèles présélectionnés
        self.model_combo.clear()
        self.model_combo.addItems(_PRESETS.get(provider, []))

        # Clé déjà enregistrée pour ce provider
        self.key_edit.setText(self.settings.api_key(provider))

        is_ollama = provider == "ollama"
        # Ollama : pas de clé, mais un hôte + détection des modèles locaux
        self.key_edit.setEnabled(not is_ollama)
        self.host_edit.setVisible(is_ollama)
        self.host_row_label.setVisible(is_ollama)

        if is_ollama:
            self._populate_ollama_models()

    def _populate_ollama_models(self) -> None:
        """Tente de lister les modèles réellement installés via /api/tags."""
        try:
            from bbs_desktoo.ai.ollama import OllamaProvider
            host = self.host_edit.text() or "http://localhost:11434"
            installed = OllamaProvider(host=host).list_models()
            if installed:
                self.model_combo.clear()
                self.model_combo.addItems(installed)
        except Exception:
            pass  # silencieux : on garde les presets si Ollama est absent

    # ------------------------------------------------------------------ #
    def _save(self) -> None:
        provider = self.provider_combo.currentData()
        model = self.model_combo.currentText().strip()

        self.settings.set_ai_provider(provider)
        self.settings.set_ai_model(model)
        if provider != "ollama":
            self.settings.set_api_key(provider, self.key_edit.text().strip())
        else:
            self.settings.set_ollama_host(self.host_edit.text().strip() or "http://localhost:11434")

        self.accept()
