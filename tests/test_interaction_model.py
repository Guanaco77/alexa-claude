# -*- coding: utf-8 -*-
"""Contrôles du modèle d'interaction et du manifeste."""

import json
import os
import re
import subprocess

import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(
    ROOT, "skill-package", "interactionModels", "custom", "fr-FR.json"
)


def load_model():
    with open(MODEL_PATH, encoding="utf-8") as f:
        return json.load(f)["interactionModel"]["languageModel"]


def custom_intents():
    return [i for i in load_model()["intents"] if not i["name"].startswith("AMAZON.")]


def test_invocation_name():
    assert load_model()["invocationName"] == "assistant claude" == config.INVOCATION_NAME


def test_only_french_locale():
    with open(os.path.join(ROOT, "skill-package", "skill.json"), encoding="utf-8") as f:
        manifest = json.load(f)["manifest"]
    assert list(manifest["publishingInformation"]["locales"]) == ["fr-FR"]
    assert os.listdir(os.path.dirname(MODEL_PATH)) == ["fr-FR.json"]


def test_required_builtin_intents():
    names = {i["name"] for i in load_model()["intents"]}
    for name in ("Help", "Cancel", "Stop", "NavigateHome", "Fallback", "No"):
        assert "AMAZON.%sIntent" % name in names


def test_model_and_config_list_the_same_question_intents():
    names = {i["name"] for i in custom_intents()}
    assert names == set(config.QUESTION_PREFIXES) | {config.DEEP_INTENT}


def test_every_utterance_has_a_carrier_phrase_and_one_slot():
    for intent in custom_intents():
        assert intent["slots"] == [{"name": "query", "type": "AMAZON.SearchQuery"}]
        assert intent["samples"], intent["name"]
        for sample in intent["samples"]:
            assert sample.count("{query}") == 1, sample
            carrier = sample.replace("{query}", "").strip()
            assert re.search(r"\w", carrier), "phrase porteuse absente : %r" % sample


def test_utterances_use_allowed_characters_only():
    for intent in load_model()["intents"]:
        for sample in intent["samples"]:
            assert re.match(r"^[a-zà-ÿœ' {}-]+$", sample), sample
            assert sample == sample.strip()
            assert "  " not in sample


def test_no_utterance_appears_twice():
    seen = {}
    for intent in load_model()["intents"]:
        for sample in intent["samples"]:
            assert sample not in seen, "%r : %s et %s" % (
                sample, seen.get(sample), intent["name"],
            )
            seen[sample] = intent["name"]


def test_at_least_thirty_question_utterances():
    total = sum(
        len(i["samples"]) for i in custom_intents() if i["name"] != config.DEEP_INTENT
    )
    assert total >= 30


def test_each_prefix_matches_its_first_utterance():
    """Le préfixe remis devant le slot est bien la phrase porteuse de l'intent."""
    for intent in custom_intents():
        prefix = config.QUESTION_PREFIXES.get(intent["name"], "")
        if prefix:
            assert intent["samples"][0] == prefix + " {query}", intent["name"]


def test_no_secret_is_tracked_or_present():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    ).stdout.split()
    assert "lambda/claude_secrets.py" not in tracked
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        assert "lambda/claude_secrets.py" in f.read().split()
    pattern = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")
    for path in tracked:
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8", errors="ignore") as f:
            assert not pattern.search(f.read()), "clé possible dans %s" % path
