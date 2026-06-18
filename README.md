# BBS desktOO

IDE natif Linux léger avec double panneau IA. Membre de la **BBS Suite**.

L'outil est gratuit et open source. Le modèle IA est à toi : tu branches ton
propre accès, ou tu restes 100 % local avec Ollama. Pas d'abonnement, pas de
tracking, pas de lock-in.

## Philosophie

- Gratuit, open source, pas de tracking, pas d'abonnement.
- Agnostique au modèle : l'utilisateur branche son propre accès IA.
- Natif KDE/Linux par défaut. L'éditeur, le terminal et l'IA locale sont 100 %
  natifs (PyQt6, zéro Electron). Le panneau IA web embarque QtWebEngine
  (Chromium) — choix assumé pour avoir claude.ai dans l'IDE sans changer de
  fenêtre.

## Layout

```
┌──────────┬───────────────────────────┬──────────────────────┐
│ Explorer │  Éditeur (onglets)        │  IA web (embarquée)   │
│          ├───────────────────────────┤──────────────────────┤
│          │  Terminal (PTY)           │  IA locale (Ollama)   │
└──────────┴───────────────────────────┴──────────────────────┘
```

La colonne de droite est splittée verticalement : IA web en haut (copier-coller
assumé), IA locale en bas (chat + injection terminal).

## Stack

- **UI** : Python + PyQt6
- **Éditeur** : QScintilla (coloration syntaxique)
- **Terminal** : PTY réel (couleurs ANSI, sudo, programmes interactifs)
- **IA web** : QtWebEngine (Claude, Gemini, Mistral)
- **IA locale** : Ollama (Qwen, Mistral…) — appels agnostiques (Claude API,
  OpenAI, Ollama)

## Installation

```bash
pip install -r requirements.txt
python3 main.py
```

Sous KDE Neon / Ubuntu 24.04, si des libs Qt manquent :

```bash
sudo apt install python3-pyqt6 python3-pyqt6.qsci
```

### IA locale (recommandé — gratuit, privé)

Installe [Ollama](https://ollama.com) et un modèle de code :

```bash
ollama pull qwen2.5-coder:7b
```

Sur GPU AMD (RDNA2, ex. RX 6600/6650 XT, gfx1032), force la compatibilité ROCm :

```bash
sudo systemctl edit ollama
# [Service]
# Environment="HSA_OVERRIDE_GFX_VERSION=10.3.0"
sudo systemctl restart ollama
```

Puis, dans desktOO : badge modèle → Ollama → `qwen2.5-coder:7b`.

## Fonctionnalités

- Explorateur de fichiers, éditeur multi-onglets avec coloration
  (Python, JS, C/C++, Bash, Markdown, HTML, JSON).
- Terminal PTY intégré : couleurs réelles, `sudo` (mot de passe demandé et
  masqué dans desktOO), programmes interactifs.
- **IA web** : Claude / Gemini / Mistral embarqués, session persistante entre
  les lancements. Bouton ↗ pour ouvrir dans le navigateur système.
- **IA locale** : chat sur le code (contexte du fichier courant joint) et
  **injection terminal** — l'IA propose des commandes dans des blocs ```bash,
  transformées en cartes actionnables.
- **Garde-fous à trois niveaux** sur les commandes injectées :
  - sûr : exécution au premier clic ;
  - ⚠ attention (jaune) : `sudo`, `apt install`, `git push`… repère visuel ;
  - ⚠ risqué (rouge) : `rm -rf`, `dd`, `git reset --hard`… double confirmation.
- Aucune auto-exécution : rien ne tourne sans clic explicite. Aucune clé en dur
  (stockage via QSettings, hors dépôt).

## Raccourcis

| Touche | Action |
|--------|--------|
| `Ctrl+S` | Enregistrer le fichier courant |
| `Ctrl+Q` | Quitter |
| `Entrée` | Envoyer (panneau IA) |
| `Maj+Entrée` | Saut de ligne (panneau IA) |
| `↑` / `↓` | Historique des commandes (terminal) |

## Feuille de route

- [ ] Pastilles de statut CI GitHub (vert/jaune/rouge) ouvrant les Actions dans le panneau web
- [ ] Explorateur multi-onglets (split vertical)
- [ ] Émulateur terminal complet (applications plein écran : vim, htop)

---

GPL-3.0 — développé par blacksamdev — en hommage à Samuel Bellamy 🏴‍☠️, le Prince des Pirates, capitaine du Whydah.
