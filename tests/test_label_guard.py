"""The copy guard is fast enough to run on every response, and no answer changed for it.

``labels._banned_in`` asks one combined pattern whether a text holds any banned token at
all, and only then removes the allowed phrases and names the tokens. It also remembers its
answers. Both are shortcuts through one definition, restated here in its plain form.
"""

from __future__ import annotations

import random

from galactico.api import shell
from galactico.domain import labels


def _plain(text: str) -> tuple[str, ...]:
    """Lower-case, single spaces, allowed phrases removed, then each token asked in turn."""
    cleaned = labels._SPACE.sub(" ", text.lower())
    for phrase in labels._ALLOWED_LONGEST_FIRST:
        cleaned = phrase.sub(" ", cleaned)
    return tuple(token for token, pattern in labels._TOKEN_PATTERNS if pattern.search(cleaned))


def test_the_fast_path_and_the_memo_change_no_answer():
    rng = random.Random(7)
    vocabulary = [
        *labels.BANNED_LABEL_TOKENS, *labels.ALLOWED_PHRASES,
        # Near misses: a token inside a word, beside an underscore, and halves of the
        # two-word tokens that must not match apart.
        "Mariano", "knot", "bestseller", "overallx", "ratings", "home_score", "chance_creation",
        "top-up", "likes", "to", "which", "suits", "line", "height", "thanks", "no", "not", "a",
    ]
    separators = [" ", "  ", "\n", "\t ", ", ", ". ", "; ", "-", "_", "(", ")", "", ":", "/", "'"]
    wrong, with_token, clean = [], 0, 0
    for _ in range(20000):
        text = "".join(rng.choice(vocabulary) + rng.choice(separators)
                       for _ in range(rng.randint(1, 6)))
        roll = rng.random()
        text = text.upper() if roll < 0.15 else text.title() if roll < 0.3 else text
        want = _plain(text)
        with_token += bool(want)
        clean += not want
        if labels._banned_in(text) != want or labels._banned_in(text) != want:  # cold, then warm
            wrong.append(text)
    assert wrong == []
    assert with_token > 1000 and clean > 1000  # both the shortcut and the full path ran


def test_a_two_word_token_is_found_across_any_whitespace_and_only_as_whole_words():
    assert labels.scan_labels("He likes   to drift wide.") == ["text: likes to"]
    assert labels.scan_labels("He likes\n\tto drift wide.") == ["text: likes to"]
    assert labels.scan_labels("Dislikes to drift; he likes tomorrow.") == []
    assert labels.scan_labels("The model  thinks so.") == ["text: the model thinks"]


def test_the_memo_is_bounded_and_the_shell_serves_the_same_guard():
    assert labels._banned_in.cache_info().maxsize == 32768
    assert shell.scan_labels is labels.scan_labels
    assert shell.BANNED_LABEL_TOKENS is labels.BANNED_LABEL_TOKENS
    assert shell.ALLOWED_PHRASES is labels.ALLOWED_PHRASES
