# -*- coding: utf-8 -*-
"""Appel de l'API Claude avec `requests` (sans le SDK, pour démarrer vite)."""

import logging
import time

import requests

import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Une session réutilise la connexion TLS entre deux questions rapprochées.
_session = requests.Session()


class ClaudeError(Exception):
    """Échec d'un appel. `kind` est une clé de config.SPEECH_ERRORS."""

    def __init__(self, kind, status=None, detail=""):
        super().__init__("%s (HTTP %s) %s" % (kind, status, detail))
        self.kind = kind
        self.status = status
        self.detail = detail


class ClaudeReply(object):
    def __init__(self, text, truncated):
        self.text = text
        self.truncated = truncated  # True si coupée par max_tokens


def build_payload(messages, deep=False):
    model = config.MODEL_DEEP if deep else config.MODEL_DEFAULT
    payload = {
        "model": model,
        "max_tokens": config.MAX_TOKENS_DEEP if deep else config.MAX_TOKENS_DEFAULT,
        "system": config.SYSTEM_PROMPT_DEEP if deep else config.SYSTEM_PROMPT,
        "messages": messages,
        "output_config": {
            "effort": config.EFFORT_DEEP if deep else config.EFFORT_DEFAULT
        },
    }
    thinking = config.THINKING_OFF.get(model)
    if thinking:
        payload["thinking"] = thinking
    return payload


def _error_kind(status, error_type, message):
    """Classe une réponse d'erreur de l'API."""
    if status == 402 or error_type == "billing_error" or "credit balance" in message.lower():
        return "credits"
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status == 529 or error_type == "overloaded_error":
        return "overloaded"
    if status >= 500:
        return "server"
    return "bad_request"


def ask_claude(api_key, messages, deep=False):
    """Envoie la conversation à Claude et renvoie un ClaudeReply.

    Lève ClaudeError dans tous les cas d'échec ; la durée est toujours loggée.
    """
    payload = build_payload(messages, deep)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": config.API_VERSION,
        "content-type": "application/json",
    }
    start = time.monotonic()
    try:
        response = _session.post(
            config.API_URL,
            headers=headers,
            json=payload,
            timeout=config.HTTP_TIMEOUT_S,
        )
    except requests.exceptions.Timeout:
        logger.warning(
            "Claude model=%s TIMEOUT après %.2fs",
            payload["model"], time.monotonic() - start,
        )
        raise ClaudeError("timeout")
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "Claude model=%s ERREUR RÉSEAU après %.2fs : %s",
            payload["model"], time.monotonic() - start, exc,
        )
        raise ClaudeError("network", detail=str(exc))

    duration = time.monotonic() - start
    status = response.status_code

    try:
        data = response.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    if status != 200:
        error = data.get("error") or {}
        error_type = error.get("type", "")
        message = error.get("message", "") or response.text[:300]
        kind = _error_kind(status, error_type, message)
        logger.error(
            "Claude model=%s HTTP %s en %.2fs type=%s message=%s",
            payload["model"], status, duration, error_type, message,
        )
        raise ClaudeError(kind, status=status, detail=message)

    usage = data.get("usage") or {}
    stop_reason = data.get("stop_reason")
    logger.info(
        "Claude model=%s HTTP 200 en %.2fs stop=%s tokens_in=%s tokens_out=%s",
        payload["model"], duration, stop_reason,
        usage.get("input_tokens"), usage.get("output_tokens"),
    )

    if stop_reason == "refusal":
        raise ClaudeError("refusal", status=status)

    text = "".join(
        block.get("text", "")
        for block in data.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()
    if not text:
        raise ClaudeError("empty", status=status)

    return ClaudeReply(text, truncated=(stop_reason == "max_tokens"))
