# -*- coding: utf-8 -*-
"""Mise en forme du texte de Claude pour la synthèse vocale d'Alexa."""

import re

_SENTENCE_END = ".!?…"


def clean_markdown(text):
    """Retire le markdown résiduel et met le texte sur une seule ligne."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Blocs de code : on garde le contenu, pas les clôtures.
    text = re.sub(r"```[\w+-]*\n?", "", text)
    # Images et liens : ![alt](url) -> alt, [texte](url) -> texte.
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # URL nues : imprononçables.
    text = re.sub(r"https?://\S+", "", text)
    # Débuts de ligne : titres, citations, puces.
    text = re.sub(r"(?m)^[ \t]*#{1,6}[ \t]*", "", text)
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    text = re.sub(r"(?m)^[ \t]*[-*+•][ \t]+", "", text)
    # Emphase et code en ligne.
    text = text.replace("`", "").replace("*", "").replace("#", "")
    text = re.sub(r"__+", "", text)
    text = re.sub(r"~~+", "", text)
    # Séparateurs de tableau.
    text = text.replace("|", " ")
    # Une seule ligne, espaces compactés.
    text = re.sub(r"\s+", " ", text).strip()
    # Pas d'espace avant une virgule ou un point laissé par un retrait.
    text = re.sub(r" +([,.])", r"\1", text)
    return text


def trim_incomplete_sentence(text):
    """Retire une dernière phrase inachevée (réponse coupée par max_tokens).

    Le texte est renvoyé tel quel s'il ne contient aucune phrase complète.
    """
    text = text.rstrip()
    if not text or text[-1] in _SENTENCE_END:
        return text
    last = max(text.rfind(c) for c in _SENTENCE_END)
    if last <= 0:
        return text
    return text[: last + 1]


def truncate_at_sentence(text, limit):
    """Tronque à `limit` caractères au plus, en coupant à la fin d'une phrase."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    # Fin de phrase = ponctuation suivie d'un espace (ou de la limite).
    ends = [m.end() for m in re.finditer(r"[.!?…]+(?=\s|$)", head + " ")]
    ends = [e for e in ends if e <= limit]
    if ends and ends[-1] >= limit // 2:
        return head[: ends[-1]]
    # Pas de fin de phrase exploitable : on coupe sur un mot.
    cut = head.rfind(" ")
    if cut <= 0:
        cut = limit - 1
    return head[:cut].rstrip(" ,;:") + "…"


def escape_ssml(text):
    """Échappe les caractères réservés du SSML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def to_plain_speech(text, limit, truncated=False):
    """Texte propre et borné, non échappé (forme gardée dans l'historique)."""
    text = clean_markdown(text)
    if truncated:
        text = trim_incomplete_sentence(text)
    return truncate_at_sentence(text, limit)
