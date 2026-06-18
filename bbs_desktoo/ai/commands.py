# bbs_desktoo/ai/commands.py
# BBS desktOO — extraction et analyse des commandes proposées par l'IA.
#
# L'IA en mode injection répond avec ses commandes dans des blocs ```bash.
# On les extrait, et on signale celles qui touchent à des opérations
# destructrices pour déclencher un avertissement renforcé avant exécution.
#
# Règle d'or : rien ne s'exécute sans clic explicite de l'utilisateur.
# Cette analyse n'autorise/interdit rien — elle informe l'UI du niveau de
# risque pour colorer l'avertissement.

import re


# Blocs ```bash ... ``` ou ```sh ... ``` ou ```shell ... ```
_BLOCK_RE = re.compile(
    r"```(?:bash|sh|shell)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

# Motifs considérés dangereux. Volontairement large : on préfère un faux
# positif (avertissement de trop) à un faux négatif (commande destructrice
# passée sans alerte).
_DANGER_PATTERNS = [
    (r"\brm\s+-[a-z]*[rf]", "Suppression récursive/forcée (rm -rf)"),
    (r"\brm\s+.*\*", "Suppression avec joker (rm ... *)"),
    (r"\bdd\b", "Écriture disque bas niveau (dd)"),
    (r"\bmkfs", "Formatage de système de fichiers (mkfs)"),
    (r"\bfdisk\b|\bparted\b", "Modification de partitions"),
    (r">\s*/dev/sd[a-z]", "Écriture directe sur un disque"),
    (r"\bchmod\s+-R\s+777", "Permissions 777 récursives"),
    (r"\bchown\s+-R\b", "Changement de propriétaire récursif"),
    (r":\(\)\s*\{.*\};:", "Fork bomb"),
    (r"\bmv\s+.*\s+/dev/null", "Déplacement vers /dev/null (perte de données)"),
    (r">\s*/etc/", "Écriture dans /etc"),
    (r"\bsudo\s+rm", "Suppression en sudo"),
    (r"\bgit\s+reset\s+--hard", "Reset Git destructif (perte de modifications)"),
    (r"\bgit\s+clean\s+-[a-z]*f", "Nettoyage Git forcé (suppression de fichiers)"),
    (r"\bgit\s+push\s+.*--force", "Push forcé (réécriture d'historique distant)"),
    (r"\bcurl\b.*\|\s*(sudo\s+)?(sh|bash)", "Exécution directe d'un script distant"),
    (r"\bwget\b.*\|\s*(sudo\s+)?(sh|bash)", "Exécution directe d'un script distant"),
]


def extract_commands(text: str) -> list[str]:
    """Retourne la liste des commandes shell trouvées dans les blocs balisés.

    Chaque bloc = une action proposée. Un bloc de plusieurs commandes simples
    est aplati en chaîne `a && b && c` pour une exécution séquentielle (chaque
    commande attend que la précédente réussisse, et tout part en une seule
    ligne — évite que la ligne suivante soit avalée par un prompt sudo).
    Les structures shell multi-lignes (boucles, if/then…) sont laissées intactes.
    """
    commands = []
    for match in _BLOCK_RE.finditer(text):
        block = match.group(1).strip()
        if block:
            commands.append(join_sequential(block))
    return commands


# Mots-clés de structures shell : si présents, on n'aplatit PAS en && (sinon
# on casserait la syntaxe).
_SHELL_CONSTRUCT_WORDS = {
    "for", "while", "until", "if", "then", "else", "elif", "fi",
    "do", "done", "case", "esac", "function", "{", "}", "select",
}


def join_sequential(block: str) -> str:
    """Aplatit un bloc de commandes simples en `a && b`. Sinon renvoie le bloc.

    Conserve le bloc tel quel si :
    - une seule ligne (rien à chaîner),
    - présence d'une structure de contrôle (for/while/if/case…),
    - présence d'un opérateur de fin de ligne (&&, ||, |, ;, \\) ou d'un heredoc.
    """
    lines = [l.strip() for l in block.splitlines()]
    lines = [l for l in lines if l and not l.startswith("#")]

    if len(lines) <= 1:
        return lines[0] if lines else ""

    for l in lines:
        first = l.split()[0] if l.split() else ""
        if first in _SHELL_CONSTRUCT_WORDS:
            return block.strip()
        if l.endswith(("\\", "&&", "||", "|", ";", "{", "&")):
            return block.strip()
        if "<<" in l:   # heredoc
            return block.strip()

    return " && ".join(lines)


def analyze_danger(command: str) -> list[str]:
    """Retourne la liste des raisons de danger détectées (vide = sûr a priori).

    Une liste non vide => l'UI affiche un avertissement rouge renforcé.
    Une liste vide => avertissement standard (confirmation simple).
    """
    reasons = []
    for pattern, reason in _DANGER_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            reasons.append(reason)
    return reasons


# Motifs « attention » (jaune) : pas destructeurs, mais modifient le système
# ou demandent des privilèges. On veut un repère visuel, sans double
# confirmation. Si la commande est déjà rouge (dangereuse), on ne double pas
# en jaune.
_CAUTION_PATTERNS = [
    (r"\bsudo\b", "Privilèges administrateur (sudo)"),
    (r"\bapt(-get)?\b.*\b(install|remove|purge|upgrade|autoremove)\b", "Modification des paquets système"),
    (r"\bpip\d?\b.*\binstall\b", "Installation d'un paquet Python"),
    (r"\bnpm\b.*\b(install|i|uninstall)\b", "Installation d'un paquet npm"),
    (r"\bsystemctl\b.*\b(start|stop|restart|enable|disable)\b", "Gestion d'un service système"),
    (r"\bgit\s+push\b", "Envoi vers un dépôt distant"),
]


def analyze_caution(command: str) -> list[str]:
    """Retourne les raisons d'« attention » (jaune). Vide si déjà rouge ou sûr."""
    if analyze_danger(command):
        return []   # déjà signalé en rouge, pas de doublon
    reasons = []
    for pattern, reason in _CAUTION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            reasons.append(reason)
    return reasons


def strip_blocks(text: str) -> str:
    """Retire les blocs de commande du texte pour ne garder que l'explication.

    Utile si on veut afficher séparément le commentaire de l'IA et les
    commandes actionnables.
    """
    return _BLOCK_RE.sub("", text).strip()
