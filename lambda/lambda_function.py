# -*- coding: utf-8 -*-
"""Skill Alexa « Claude » : transmet les questions à l'API Claude."""

import importlib
import logging
import threading

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
)
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_model.services.directive import (
    Header,
    SendDirectiveRequest,
    SpeakDirective,
)

import claude_client
import config
import text_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HISTORY_KEY = "history"


def load_api_key():
    """Lit la clé dans lambda/claude_secrets.py ; None si absente ou factice."""
    try:
        module = importlib.import_module("claude_secrets")
    except Exception:  # fichier absent ou invalide
        logger.warning("claude_secrets.py introuvable ou illisible")
        return None
    key = str(getattr(module, "ANTHROPIC_API_KEY", "") or "").strip()
    if not key or key.endswith("..."):
        return None
    return key


def _enqueue_progress(handler_input):
    try:
        request_id = handler_input.request_envelope.request.request_id
        directive_client = handler_input.service_client_factory.get_directive_service()
        directive_client.enqueue(
            SendDirectiveRequest(
                header=Header(request_id=request_id),
                directive=SpeakDirective(speech=config.SPEECH_PROGRESS),
            )
        )
    except Exception as exc:  # ne doit jamais faire échouer la requête
        logger.warning("Réponse progressive non envoyée : %s", exc)


def send_progressive_response(handler_input):
    """Fait dire « Je réfléchis… » pendant l'appel à Claude.

    Envoyé dans un fil séparé pour ne rien retirer aux 8 secondes disponibles.
    """
    try:
        threading.Thread(
            target=_enqueue_progress, args=(handler_input,), daemon=True
        ).start()
    except Exception as exc:
        logger.warning("Réponse progressive non lancée : %s", exc)


def get_query(handler_input):
    # "query" pour les questions, "reply" pour la réponse libre : Alexa
    # interdit qu'un même nom de slot ait deux types différents.
    for name in ("query", "reply"):
        slot = ask_utils.get_slot(handler_input, name)
        if slot and slot.value:
            return slot.value.strip()
    return ""


def build_question(intent_name, query):
    """Reconstitue la question et dit si elle est en mode approfondi."""
    deep = intent_name == config.DEEP_INTENT
    lowered = query.lower()
    for marker in config.DEEP_MARKERS:
        if lowered.startswith(marker + " "):
            deep = True
            query = query[len(marker):].strip()
            break
    prefix = config.QUESTION_PREFIXES.get(intent_name, "")
    question = ("%s %s" % (prefix, query)).strip()
    return question, deep


def keep_open(handler_input, speech, reprompt=config.SPEECH_REPROMPT):
    return (
        handler_input.response_builder
        .speak(text_utils.escape_ssml(speech))
        .ask(text_utils.escape_ssml(reprompt))
        .response
    )


def close(handler_input, speech):
    return (
        handler_input.response_builder
        .speak(text_utils.escape_ssml(speech))
        .set_should_end_session(True)
        .response
    )


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        return keep_open(
            handler_input, config.SPEECH_LAUNCH, config.SPEECH_LAUNCH_REPROMPT
        )


class QuestionIntentHandler(AbstractRequestHandler):
    """Tous les intents de question, normaux et approfondis."""

    def can_handle(self, handler_input):
        if not ask_utils.is_request_type("IntentRequest")(handler_input):
            return False
        name = ask_utils.get_intent_name(handler_input)
        return name == config.DEEP_INTENT or name in config.QUESTION_PREFIXES

    def handle(self, handler_input):
        query = get_query(handler_input)
        if not query:
            return keep_open(
                handler_input, config.SPEECH_EMPTY_QUERY, config.SPEECH_LAUNCH_REPROMPT
            )

        api_key = load_api_key()
        if not api_key:
            return close(handler_input, config.SPEECH_NO_KEY)

        question, deep = build_question(
            ask_utils.get_intent_name(handler_input), query
        )
        if not question:
            return keep_open(
                handler_input, config.SPEECH_EMPTY_QUERY, config.SPEECH_LAUNCH_REPROMPT
            )

        session = handler_input.attributes_manager.session_attributes
        history = list(session.get(HISTORY_KEY) or [])
        messages = history + [{"role": "user", "content": question}]

        send_progressive_response(handler_input)

        try:
            reply = claude_client.ask_claude(api_key, messages, deep=deep)
        except claude_client.ClaudeError as error:
            speech = config.SPEECH_ERRORS.get(error.kind, config.SPEECH_UNEXPECTED)
            if error.kind in ("auth", "credits"):
                # Inutile de garder la session : rien ne marchera sans action.
                return close(handler_input, speech)
            return keep_open(handler_input, speech)

        answer = text_utils.to_plain_speech(
            reply.text, config.MAX_SPEECH_CHARS, truncated=reply.truncated
        )
        if not answer:
            return keep_open(handler_input, config.SPEECH_ERRORS["empty"])

        history = messages + [{"role": "assistant", "content": answer}]
        session[HISTORY_KEY] = history[-2 * config.MAX_HISTORY_TURNS:]

        return keep_open(handler_input, answer)


class YesIntentHandler(AbstractRequestHandler):
    """« Oui » en réponse à « Autre chose ? »."""

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input):
        return keep_open(handler_input, config.SPEECH_YES, config.SPEECH_LAUNCH_REPROMPT)


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        return keep_open(handler_input, config.SPEECH_HELP, config.SPEECH_LAUNCH_REPROMPT)


class GoodbyeIntentHandler(AbstractRequestHandler):
    """Stop, Annuler, Non et retour à l'accueil : on ferme la session."""

    def can_handle(self, handler_input):
        return (
            ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.NavigateHomeIntent")(handler_input)
        )

    def handle(self, handler_input):
        return close(handler_input, config.SPEECH_GOODBYE)


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return keep_open(handler_input, config.SPEECH_FALLBACK, config.SPEECH_LAUNCH_REPROMPT)


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error("Erreur non gérée : %s", exception, exc_info=True)
        return keep_open(handler_input, config.SPEECH_UNEXPECTED)


sb = CustomSkillBuilder(api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(QuestionIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(GoodbyeIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
