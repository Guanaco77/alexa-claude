# -*- coding: utf-8 -*-
"""Réglages de la skill : tout ce qu'on peut vouloir changer est ici.

Après une modification dans la console Alexa (onglet Code) : Save, puis Deploy.
"""

# --- Modèles -----------------------------------------------------------------
MODEL_DEFAULT = "claude-sonnet-5-5"   # questions normales
MODEL_FAST = "claude-haiku-5-5"       # repli si les réponses sont trop souvent coupées
MODEL_DEEP = "claude-sonnet-5-5"      # questions approfondies (DeepQuestionIntent)

MAX_TOKENS_DEFAULT = 800
MAX_TOKENS_DEEP = 500

# Alexa coupe la skill après environ 8 secondes : on abandonne l'appel avant.
HTTP_TIMEOUT_S = 6.5

# Niveau d'effort demandé au modèle ("low", "medium" ou "high").
# "low" est le plus rapide ; monter d'un cran allonge le temps de réponse.
EFFORT_DEFAULT = "low"
EFFORT_DEEP = "low"

# Les modèles récents réfléchissent avant de répondre, ce qui consomme du temps
# et des tokens de sortie. Avec 8 secondes pour répondre, on coupe cette
# réflexion. La valeur à envoyer dépend du modèle ; un modèle absent de cette
# table est appelé sans réglage (comportement par défaut de l'API).
THINKING_OFF = {
    "claude-sonnet-5-5": {"type": "between_tools"},
    "claude-haiku-5-5": {"type": "disabled"},
}

# --- API ---------------------------------------------------------------------
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# --- Conversation ------------------------------------------------------------
INVOCATION_NAME = "assistant claude"   # doit correspondre à skill-package/.../fr-FR.json
MAX_HISTORY_TURNS = 5        # échanges (question + réponse) gardés en session
MAX_SPEECH_CHARS = 1500      # longueur maximale lue à voix haute

# --- Prompts système ---------------------------------------------------------
_PROMPT_TEMPLATE = (
    "Tu es Claude, un assistant vocal qui répond via une enceinte Amazon Echo, "
    "en Belgique francophone. Tes réponses sont lues à voix haute par une "
    "synthèse vocale.\n"
    "Règles : réponds en français, {length}, de façon naturelle et orale. "
    "{structure}"
    "Tutoie l'utilisateur. Pas de markdown, pas de listes à puces, pas "
    "d'emojis, pas d'URL, pas de tableaux. Écris les nombres et unités de "
    "façon prononçable. Utilise le système métrique et l'euro. Si la question "
    "est ambiguë, donne la réponse la plus probable en une phrase puis propose "
    "de préciser. Si tu ne sais pas, dis-le simplement."
)

SYSTEM_PROMPT = _PROMPT_TEMPLATE.format(
    length="en 2 à 4 phrases maximum", structure=""
)
SYSTEM_PROMPT_DEEP = _PROMPT_TEMPLATE.format(
    length="en 4 à 8 phrases",
    structure="Structure ta réponse oralement (d'abord, ensuite, enfin). ",
)

# --- Intents de question -----------------------------------------------------
# Alexa ne transmet que le contenu du slot {query}, sans la phrase porteuse :
# pour « pourquoi le ciel est bleu », la skill reçoit « le ciel est bleu ».
# Chaque phrase porteuse qui change le sens a donc son propre intent, et cette
# table donne le début de phrase à remettre devant le slot.
# Elle doit rester synchronisée avec fr-FR.json (un test le vérifie).
QUESTION_PREFIXES = {
    "QuestionIntent": "",
    "QuestionPourquoiIntent": "pourquoi",
    "QuestionCommentIntent": "comment",
    "QuestionQuEstCeQueIntent": "qu'est-ce que",
    "QuestionCEstQuoiIntent": "c'est quoi",
    "QuestionQuiIntent": "qui",
    "QuestionQuiEstIntent": "qui est",
    "QuestionQuiEtaitIntent": "qui était",
    "QuestionQueIntent": "que",
    "QuestionQuelIntent": "quel",
    "QuestionQuelEstIntent": "quel est",
    "QuestionQuelleEstIntent": "quelle est",
    "QuestionQuelsSontIntent": "quels sont",
    "QuestionCombienIntent": "combien",
    "QuestionQuandIntent": "quand",
    "QuestionOuIntent": "où",
    "QuestionEstCeQueIntent": "est-ce que",
    "QuestionSaisTuIntent": "sais-tu",
    "QuestionPeuxTuIntent": "peux-tu",
    "QuestionExpliqueIntent": "explique-moi",
    "QuestionDisMoiIntent": "dis-moi",
    "QuestionRaconteIntent": "raconte-moi",
    "QuestionDonneIntent": "donne-moi",
    "QuestionAideIntent": "aide-moi à",
    "QuestionTraduisIntent": "traduis",
    "QuestionCalculeIntent": "calcule",
    "QuestionResumeIntent": "résume",
    "QuestionDefinisIntent": "définis",
    "QuestionProposeIntent": "propose-moi",
    "QuestionTrouveIntent": "trouve-moi",
    "QuestionQuePensesTuIntent": "que penses-tu de",
    "QuestionParleMoiIntent": "parle-moi de",
    "QuestionEtIntent": "et",
}

DEEP_INTENT = "DeepQuestionIntent"

# Si Alexa range « explique-moi en détail … » dans un intent normal, le slot
# commence par l'un de ces mots : on bascule alors en mode approfondi.
DEEP_MARKERS = ("en détail", "en détails")

# --- Phrases prononcées ------------------------------------------------------
SPEECH_LAUNCH = "Oui, je t'écoute."
SPEECH_LAUNCH_REPROMPT = "Pose-moi ta question."
SPEECH_PROGRESS = "Je réfléchis…"
SPEECH_REPROMPT = "Autre chose ?"
SPEECH_YES = "Je t'écoute."
SPEECH_EMPTY_QUERY = "Je n'ai pas saisi ta question. Tu peux la reformuler ?"
SPEECH_HELP = (
    "Pose-moi n'importe quelle question, par exemple : pourquoi le ciel est "
    "bleu. Si tu veux une réponse plus approfondie, dis : réfléchis à, puis ta "
    "question."
)
SPEECH_GOODBYE = "À bientôt !"
SPEECH_FALLBACK = (
    "Je n'ai pas compris. Commence par exemple par pourquoi, comment ou "
    "explique-moi."
)
SPEECH_NO_KEY = "La clé API n'est pas configurée."
SPEECH_UNEXPECTED = "Désolé, j'ai rencontré un problème. Tu peux réessayer ?"

# Un message par type d'erreur renvoyé par claude_client.ClaudeError.kind.
SPEECH_ERRORS = {
    "timeout": (
        "Désolé, la réponse prenait trop de temps. Tu peux reformuler ou poser "
        "une question plus courte ?"
    ),
    "auth": "La clé API est refusée. Vérifie-la dans le code de la skill.",
    "credits": "Mes crédits sont épuisés pour ce mois-ci.",
    "rate_limit": "Je reçois trop de demandes à la fois. Réessaie dans un instant.",
    "overloaded": "Le service Claude est surchargé. Réessaie dans un instant.",
    "server": "Le service Claude a un problème technique. Réessaie plus tard.",
    "network": "Je n'arrive pas à joindre le service Claude. Réessaie plus tard.",
    "bad_request": (
        "Ma demande a été refusée par le service Claude. Regarde les journaux "
        "de la skill."
    ),
    "refusal": "Je ne peux pas répondre à cette question.",
    "empty": "Je n'ai pas obtenu de réponse. Tu peux reformuler ?",
}
