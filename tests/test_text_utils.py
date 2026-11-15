# -*- coding: utf-8 -*-
import text_utils


def test_clean_removes_bold_italic_and_code():
    assert text_utils.clean_markdown("Le **ciel** est *bleu* et `clair`.") == (
        "Le ciel est bleu et clair."
    )


def test_clean_removes_headings_and_hashes():
    assert text_utils.clean_markdown("## Titre\nTexte #1") == "Titre Texte 1"


def test_clean_removes_bullets():
    text = "Voici :\n- un\n- deux\n* trois"
    assert text_utils.clean_markdown(text) == "Voici : un deux trois"


def test_clean_keeps_hyphenated_words():
    assert text_utils.clean_markdown("Qu'est-ce que c'est, dis-moi ?") == (
        "Qu'est-ce que c'est, dis-moi ?"
    )


def test_clean_replaces_links_with_their_text():
    text = "Voir [le site](https://example.com/page) pour la suite."
    assert text_utils.clean_markdown(text) == "Voir le site pour la suite."


def test_clean_removes_bare_urls():
    assert text_utils.clean_markdown("Va sur https://example.com/x maintenant") == (
        "Va sur maintenant"
    )


def test_clean_removes_code_fences():
    text = "Exemple :\n```python\nprint(1)\n```\nFin."
    assert text_utils.clean_markdown(text) == "Exemple : print(1) Fin."


def test_clean_flattens_newlines_and_spaces():
    assert text_utils.clean_markdown("Un.\n\nDeux.\r\n   Trois.\t") == "Un. Deux. Trois."


def test_clean_handles_empty_input():
    assert text_utils.clean_markdown("") == ""
    assert text_utils.clean_markdown(None) == ""


def test_escape_ssml_all_reserved_characters():
    assert text_utils.escape_ssml("""A & B < C > D "E" l'F""") == (
        "A &amp; B &lt; C &gt; D &quot;E&quot; l&apos;F"
    )


def test_escape_ssml_escapes_ampersand_once():
    assert text_utils.escape_ssml("<&>") == "&lt;&amp;&gt;"


def test_truncate_leaves_short_text_alone():
    assert text_utils.truncate_at_sentence("Court.", 1500) == "Court."


def test_truncate_cuts_at_sentence_end():
    text = "Première phrase. Deuxième phrase. Troisième phrase très longue."
    result = text_utils.truncate_at_sentence(text, 40)
    assert result == "Première phrase. Deuxième phrase."


def test_truncate_real_size():
    sentence = "Ceci est une phrase de test assez banale. "
    result = text_utils.truncate_at_sentence(sentence * 100, 1500)
    assert len(result) <= 1500
    assert result.endswith(".")
    assert len(result) > 1400


def test_truncate_without_sentence_end_cuts_on_a_word():
    result = text_utils.truncate_at_sentence("mot " * 100, 50)
    assert len(result) <= 50
    assert result.endswith("mot…")


def test_truncate_ignores_decimal_point():
    text = "Cela coûte 3.50 euros en tout. " + "x" * 50
    assert text_utils.truncate_at_sentence(text, 40) == "Cela coûte 3.50 euros en tout."


def test_trim_incomplete_sentence():
    assert text_utils.trim_incomplete_sentence("Une phrase. Une autre coup") == (
        "Une phrase."
    )
    assert text_utils.trim_incomplete_sentence("Complet !") == "Complet !"
    assert text_utils.trim_incomplete_sentence("sans ponctuation") == "sans ponctuation"


def test_to_plain_speech_combines_steps():
    raw = "**D'abord**, ceci.\n\nEnsuite, cela. Et une fin coup"
    assert text_utils.to_plain_speech(raw, 1500, truncated=True) == (
        "D'abord, ceci. Ensuite, cela."
    )
