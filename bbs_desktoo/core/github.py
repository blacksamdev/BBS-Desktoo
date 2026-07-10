# bbs_desktoo/core/github.py
# BBS desktOO — récupération du statut CI GitHub Actions d'un dépôt.
#
# Interroge l'API GitHub Actions pour le dernier run d'un dépôt et en déduit
# un statut simple : success / failure / building / none / error. L'UI mappe
# ça sur une pastille verte / rouge / jaune / grise.
#
# Sans token : 60 requêtes/heure (suffisant pour un polling lent sur quelques
# dépôts publics). Avec token (réglages) : 5000/heure.

import re

import httpx


def parse_repo(ref: str) -> tuple[str, str] | None:
    """Extrait (owner, repo) d'une URL GitHub ou d'une forme 'owner/repo'.

    N'accepte que les caractères valides GitHub (assainissement d'entrée) :
    owner = alphanumérique et tirets ; repo = alphanumérique, points,
    tirets, underscores.
    """
    ref = ref.strip()
    # URL complète : https://github.com/owner/repo(.git)
    m = re.search(r"github\.com[/:]([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$", ref)
    if m:
        return m.group(1), m.group(2)
    # Forme courte owner/repo
    m = re.match(r"^([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?$", ref)
    if m:
        return m.group(1), m.group(2)
    return None


def actions_url(owner: str, repo: str) -> str:
    """URL de la page Actions du dépôt (ouverte au clic sur la pastille)."""
    return f"https://github.com/{owner}/{repo}/actions"


def fetch_status(owner: str, repo: str, token: str = "") -> dict:
    """Retourne le statut CI du dernier run du dépôt.

    Renvoie un dict :
      {
        "state":  "success" | "failure" | "building" | "none" | "error",
        "detail": str,        # libellé lisible
        "url":    str,        # lien direct du run (ou page Actions)
      }
    """
    api = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=1"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = httpx.get(api, headers=headers, timeout=10)
    except Exception as exc:
        return {"state": "error", "detail": f"réseau : {exc}", "url": actions_url(owner, repo)}

    if resp.status_code == 404:
        return {"state": "error", "detail": "dépôt introuvable ou privé", "url": actions_url(owner, repo)}
    if resp.status_code == 403:
        return {"state": "error", "detail": "quota API atteint (ajoute un token)", "url": actions_url(owner, repo)}
    if resp.status_code != 200:
        return {"state": "error", "detail": f"HTTP {resp.status_code}", "url": actions_url(owner, repo)}

    runs = resp.json().get("workflow_runs", [])
    if not runs:
        return {"state": "none", "detail": "aucun run CI", "url": actions_url(owner, repo)}

    run = runs[0]
    status = run.get("status")          # queued | in_progress | completed
    conclusion = run.get("conclusion")  # success | failure | cancelled | ...
    run_url = run.get("html_url", actions_url(owner, repo))
    name = run.get("name") or run.get("display_title") or "CI"

    if status != "completed":
        return {"state": "building", "detail": f"{name} — en cours", "url": run_url}
    if conclusion == "success":
        return {"state": "success", "detail": f"{name} — OK", "url": run_url}
    if conclusion in ("failure", "timed_out", "startup_failure"):
        return {"state": "failure", "detail": f"{name} — échec", "url": run_url}
    # cancelled, skipped, neutral, action_required…
    return {"state": "none", "detail": f"{name} — {conclusion}", "url": run_url}
