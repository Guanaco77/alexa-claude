# -*- coding: utf-8 -*-
"""Tests des handlers, l'API Claude étant simulée au niveau HTTP."""

import pytest
import requests

import claude_client
import config
import lambda_function


class FakeResponse(object):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        if self._body is None:
            raise ValueError("pas de JSON")
        return self._body


def ok_body(text, stop_reason="end_turn"):
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "usage": {"input_tokens": 50, "output_tokens": 20},
    }


def error_body(error_type, message):
    return {"type": "error", "error": {"type": error_type, "message": message}}


class FakeApi(object):
    """Remplace requests.Session.post et mémorise les appels reçus."""

    def __init__(self):
        self.calls = []
        self.result = FakeResponse(200, ok_body("Réponse."))

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(claude_client._session, "post", fake.post)
    monkeypatch.setattr(lambda_function, "load_api_key", lambda: "sk-ant-test")
    monkeypatch.setattr(lambda_function, "send_progressive_response", lambda hi: None)
    return fake


def invoke(event):
    return lambda_function.lambda_handler(event, None)


def ssml(result):
    return result["response"]["outputSpeech"]["ssml"]


def reprompt(result):
    return result["response"]["reprompt"]["outputSpeech"]["ssml"]


def is_open(result):
    return result["response"]["shouldEndSession"] is False


# --- Lancement, aide, arrêt ---------------------------------------------------

def test_launch(load_event):
    result = invoke(load_event("launch"))
    assert ssml(result) == "<speak>Oui, je t&apos;écoute.</speak>"
    assert reprompt(result) == "<speak>Pose-moi ta question.</speak>"
    assert is_open(result)


def test_help(load_event):
    result = invoke(load_event("help"))
    assert "réfléchis à, puis ta question" in ssml(result)
    assert is_open(result)


@pytest.mark.parametrize("name", ["stop", "cancel", "no"])
def test_goodbye(load_event, name):
    result = invoke(load_event(name))
    assert ssml(result) == "<speak>À bientôt !</speak>"
    assert result["response"]["shouldEndSession"] is True


def test_yes_invites_next_question(load_event):
    result = invoke(load_event("yes"))
    assert ssml(result) == "<speak>Je t&apos;écoute.</speak>"
    assert is_open(result)


def test_fallback(load_event):
    result = invoke(load_event("fallback"))
    assert ssml(result).startswith("<speak>Je n&apos;ai pas compris.")
    assert is_open(result)


def test_session_ended(load_event):
    result = invoke(load_event("session_ended"))
    assert "outputSpeech" not in result["response"]


# --- Questions ----------------------------------------------------------------

def test_question_normal_uses_sonnet(load_event, api):
    api.result = FakeResponse(
        200, ok_body("Parce que **l'air** diffuse le bleu.\n\nC'est \"Rayleigh\" & co.")
    )
    result = invoke(load_event("question"))

    assert ssml(result) == (
        "<speak>Parce que l&apos;air diffuse le bleu. "
        "C&apos;est &quot;Rayleigh&quot; &amp; co.</speak>"
    )
    assert reprompt(result) == "<speak>Autre chose ?</speak>"
    assert is_open(result)

    call = api.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["timeout"] == 6.5
    assert call["headers"]["x-api-key"] == "sk-ant-test"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["headers"]["content-type"] == "application/json"
    body = call["json"]
    assert body["model"] == "claude-sonnet-5-5"
    assert body["max_tokens"] == 800
    assert "2 à 4 phrases" in body["system"]
    assert body["thinking"] == {"type": "between_tools"}
    # La phrase porteuse est remise devant le slot.
    assert body["messages"] == [
        {"role": "user", "content": "pourquoi le ciel est bleu"}
    ]


def test_question_stores_history_unescaped(load_event, api):
    api.result = FakeResponse(200, ok_body("C'est l'air."))
    result = invoke(load_event("question"))
    assert result["sessionAttributes"]["history"] == [
        {"role": "user", "content": "pourquoi le ciel est bleu"},
        {"role": "assistant", "content": "C'est l'air."},
    ]


def test_followup_sends_history(load_event, api):
    result = invoke(load_event("question_followup"))
    messages = api.calls[0]["json"]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "et au coucher du soleil"
    assert len(result["sessionAttributes"]["history"]) == 4


@pytest.mark.parametrize(
    "intent_name, slot_value, expected",
    [
        ("ReplyEnIntent", "novembre", "en novembre"),
        ("ReplyCEstIntent", "pour un gâteau", "c'est pour un gâteau"),
        ("FreeReplyIntent", "novembre", "novembre"),
    ],
)
def test_reply_to_a_question_from_claude(load_event, api, intent_name, slot_value, expected):
    event = load_event("question_followup")
    event["request"]["intent"]["name"] = intent_name
    event["request"]["intent"]["slots"]["query"]["value"] = slot_value
    result = invoke(event)
    messages = api.calls[0]["json"]["messages"]
    assert messages[-1] == {"role": "user", "content": expected}
    assert len(messages) == 3
    assert is_open(result)


def test_history_is_capped_at_five_exchanges(load_event, api):
    event = load_event("question_followup")
    history = []
    for i in range(7):
        history.append({"role": "user", "content": "question %d" % i})
        history.append({"role": "assistant", "content": "réponse %d" % i})
    event["session"]["attributes"]["history"] = history

    result = invoke(event)

    kept = result["sessionAttributes"]["history"]
    assert len(kept) == 10
    assert kept[0] == {"role": "user", "content": "question 3"}
    assert kept[-1] == {"role": "assistant", "content": "Réponse."}


def test_deep_question(load_event, api):
    result = invoke(load_event("deep_question"))
    body = api.calls[0]["json"]
    assert body["model"] == config.MODEL_DEEP
    assert body["max_tokens"] == 500
    assert "4 à 8 phrases" in body["system"]
    assert "d'abord, ensuite, enfin" in body["system"]
    assert body["messages"][-1]["content"] == "l'avenir des voitures électriques"
    assert is_open(result)


def test_en_detail_in_normal_intent_switches_to_deep(load_event, api):
    event = load_event("question")
    event["request"]["intent"]["name"] = "QuestionExpliqueIntent"
    event["request"]["intent"]["slots"]["query"]["value"] = "en détail la photosynthèse"
    invoke(event)
    body = api.calls[0]["json"]
    assert body["max_tokens"] == 500
    assert body["messages"][-1]["content"] == "explique-moi la photosynthèse"


def test_haiku_gets_its_own_thinking_setting(load_event, api, monkeypatch):
    monkeypatch.setattr(config, "MODEL_DEFAULT", config.MODEL_FAST)
    invoke(load_event("question"))
    body = api.calls[0]["json"]
    assert body["model"] == "claude-haiku-5-5"
    assert body["thinking"] == {"type": "disabled"}


def test_empty_query_asks_to_rephrase(load_event, api):
    result = invoke(load_event("question_empty"))
    assert "reformuler" in ssml(result)
    assert is_open(result)
    assert api.calls == []


def test_answer_cut_by_max_tokens_drops_unfinished_sentence(load_event, api):
    api.result = FakeResponse(
        200, ok_body("Première phrase. Deuxième phrase coup", stop_reason="max_tokens")
    )
    result = invoke(load_event("question"))
    assert ssml(result) == "<speak>Première phrase.</speak>"


# --- Erreurs ------------------------------------------------------------------

def test_timeout_keeps_session_open(load_event, api):
    api.result = requests.exceptions.ReadTimeout("trop long")
    result = invoke(load_event("question"))
    assert ssml(result) == (
        "<speak>Désolé, la réponse prenait trop de temps. Tu peux reformuler "
        "ou poser une question plus courte ?</speak>"
    )
    assert is_open(result)
    assert "history" not in result.get("sessionAttributes", {})


def test_error_401_invalid_key(load_event, api):
    api.result = FakeResponse(401, error_body("authentication_error", "invalid x-api-key"))
    result = invoke(load_event("question"))
    assert "clé API est refusée" in ssml(result)
    assert result["response"]["shouldEndSession"] is True


@pytest.mark.parametrize(
    "status, error_type, message",
    [
        (402, "billing_error", "Billing problem"),
        (400, "invalid_request_error", "Your credit balance is too low to access the API."),
    ],
)
def test_credits_exhausted(load_event, api, status, error_type, message):
    api.result = FakeResponse(status, error_body(error_type, message))
    result = invoke(load_event("question"))
    assert ssml(result) == "<speak>Mes crédits sont épuisés pour ce mois-ci.</speak>"
    assert result["response"]["shouldEndSession"] is True


@pytest.mark.parametrize(
    "status, error_type, expected",
    [
        (429, "rate_limit_error", "trop de demandes"),
        (529, "overloaded_error", "surchargé"),
        (500, "api_error", "problème technique"),
        (400, "invalid_request_error", "refusée par le service"),
    ],
)
def test_other_api_errors_are_distinct(load_event, api, status, error_type, expected):
    api.result = FakeResponse(status, error_body(error_type, "détail"))
    result = invoke(load_event("question"))
    assert expected in ssml(result)
    assert is_open(result)


def test_error_without_json_body(load_event, api):
    api.result = FakeResponse(502, None)
    result = invoke(load_event("question"))
    assert "problème technique" in ssml(result)


def test_network_error(load_event, api):
    api.result = requests.exceptions.ConnectionError("réseau")
    result = invoke(load_event("question"))
    assert "joindre le service" in ssml(result)
    assert is_open(result)


def test_refusal(load_event, api):
    api.result = FakeResponse(200, {"content": [], "stop_reason": "refusal"})
    result = invoke(load_event("question"))
    assert "Je ne peux pas répondre" in ssml(result)
    assert is_open(result)


def test_missing_api_key(load_event, api, monkeypatch):
    monkeypatch.setattr(lambda_function, "load_api_key", lambda: None)
    result = invoke(load_event("question"))
    assert ssml(result) == "<speak>La clé API n&apos;est pas configurée.</speak>"
    assert api.calls == []


def test_load_api_key_without_secrets_file():
    # Le dépôt ne contient pas claude_secrets.py : la clé doit être absente.
    assert lambda_function.load_api_key() is None


def test_load_api_key_rejects_placeholder(monkeypatch):
    import sys
    import types

    module = types.ModuleType("claude_secrets")
    module.ANTHROPIC_API_KEY = "sk-ant-..."
    monkeypatch.setitem(sys.modules, "claude_secrets", module)
    assert lambda_function.load_api_key() is None
    module.ANTHROPIC_API_KEY = "sk-ant-api03-vraie"
    assert lambda_function.load_api_key() == "sk-ant-api03-vraie"


def test_progressive_response_failure_does_not_break_the_answer(
    load_event, api, monkeypatch
):
    # Sans jeton valide, l'envoi échoue : la réponse doit quand même arriver.
    monkeypatch.undo()
    monkeypatch.setattr(claude_client._session, "post", api.post)
    monkeypatch.setattr(lambda_function, "load_api_key", lambda: "sk-ant-test")

    class Boom(object):
        def get_directive_service(self):
            raise RuntimeError("service indisponible")

    def broken(handler_input):
        handler_input.service_client_factory = Boom()
        lambda_function._enqueue_progress(handler_input)

    monkeypatch.setattr(lambda_function, "send_progressive_response", broken)
    result = invoke(load_event("question"))
    assert ssml(result) == "<speak>Réponse.</speak>"


def test_unexpected_exception_is_caught(load_event, api, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(claude_client, "ask_claude", explode)
    result = invoke(load_event("question"))
    assert "rencontré un problème" in ssml(result)
    assert is_open(result)
