# BBS desktOO

IDE natif Linux léger avec panneau IA intégré. Membre de la **BBS Suite**.

L'outil est gratuit et open source. Le modèle IA est à toi : tu branches ton
propre accès (Claude API, OpenAI, ou Ollama en local). Zéro Electron, zéro
Chromium embarqué — PyQt6 natif.

## Philosophie

- Gratuit, open source, pas de tracking, pas d'abonnement.
- Agnostique au modèle : l'utilisateur paie son propre accès IA.
- Natif KDE/Linux, léger.
- Pas de lock-in sur un modèle ou un abonnement.

## Layout

```
┌──────────┬───────────────────────────┬──────────────────────┐
│ Explorer │  Éditeur (onglets)        │  Panneau IA          │
│          ├───────────────────────────┤  (≈ double largeur)  │
│          │  Terminal                 │                      │
└──────────┴───────────────────────────┴──────────────────────┘
```

## Stack

- **UI** : Python + PyQt6
- **Éditeur** : QScintilla (coloration syntaxique)
- **Terminal** : QProcess (bash)
- **IA** : appels API agnostiques (Claude, OpenAI, Ollama) — *v0.2.0*

## Installation

```bash
pip install -r requirements.txt
python main.py
```

Sous KDE Neon / Ubuntu 24.04, si PyQt6-QScintilla manque des libs Qt :

```bash
sudo apt install python3-pyqt6 python3-pyqt6.qsci
```

## État

**v0.5.0** — terminal couleur + web durci :
- [x] Colonne IA double : IA web (claude.ai/ChatGPT/Gemini/Mistral) + IA locale (Ollama)
- [x] Injection terminal : commandes en cartes actionnables, double confirmation si risqué
- [x] **Terminal ANSI** : couleurs réelles (prompt, ls --color, git, pip…) au lieu des codes bruts
- [x] **User-Agent Chrome** sur le panneau web : débloque l'authentification ChatGPT/Cloudflare
- [x] Entrée envoie · Maj+Entrée saut de ligne

**v0.6.0** — à venir :
- [ ] Pastilles de statut CI GitHub (vert/jaune/rouge) ouvrant les Actions dans le panneau web
- [ ] Explorateur multi-onglets (split vertical)


## Raccourcis

| Touche | Action |
|--------|--------|
| `Ctrl+S` | Enregistrer le fichier courant |
| `Ctrl+Q` | Quitter |
| `↑` / `↓` | Historique des commandes (terminal) |

---

GPL-3.0 — développé par blacksamdev — en hommage à Samuel Bellamy 🏴‍☠️, le Prince des Pirates, capitaine du Whydah.
