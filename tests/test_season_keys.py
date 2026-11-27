"""The season key grammar: slugs, entity and match keys, legacy keys and club plates.

A key is a URL, so each test targets a way a URL could mislead or break: two spellings of one
name giving two keys, a letter lost in folding, a key the grammar should refuse accepted (an
upper-case letter, an accent, a path separator), a match key that does not parse back to its
id, or a legacy OpenFootball id read as something else.

This file also holds B5's guard on the keys of what the season pages serve: until the season
routes exist (P0), that is every model object's JSON (``test_season_model.py`` builds one of
each); P0-A extends it to every ``/api/season/*`` reply.
"""

from __future__ import annotations

from datetime import date

import pytest

from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import keys
from galactico.match_centre.season.keys import (
    KEY,
    MADRID_FD_ID,
    MADRID_KEY,
    Key,
    entity_key,
    fold,
    legacy,
    match_key,
    parse,
    plate,
    slugify,
)


@pytest.mark.parametrize(("name", "slug"), [
    ("Vinícius Júnior", "vinicius-junior"),
    ("Real Madrid CF", "real-madrid-cf"),
    ("Deportivo Alavés", "deportivo-alaves"),
    ("Atlético de Madrid", "atletico-de-madrid"),
    ("Brasileirão Série A", "brasileirao-serie-a"),
    ("Supercopa de España", "supercopa-de-espana"),
    ("1. FC Köln", "1-fc-koln"),
    ("Martin Ødegaard", "martin-odegaard"),
    ("Łukasz Ćwik", "lukasz-cwik"),
    ("Straße", "strasse"),
    ("Kemal Ölçü", "kemal-olcu"),
    ("St. Pauli", "st-pauli"),
    ("  A--B  ", "a-b"),
    ("N'Golo  O’Kanté", "n-golo-o-kante"),
    ("Real Madrid v Norte 2026-11-28", "real-madrid-v-norte-2026-11-28"),
])
def test_slugs_fold_accents_case_and_separators(name, slug):
    assert slugify(name) == slug
    assert KEY.fullmatch(slug)


def test_a_name_with_nothing_to_keep_has_no_slug():
    assert slugify("Борисов") == ""
    assert slugify("—") == ""
    with pytest.raises(ValueError):
        entity_key(None, "Борисов")
    with pytest.raises(ValueError):
        entity_key(86, "")


def test_fold_sets_accents_and_case_aside_and_keeps_the_words():
    assert fold("Vinícius  Júnior") == "vinicius junior"
    assert fold("ÁLVARO") == fold("alvaro")
    assert fold("Ødegaard") == "odegaard"


@pytest.mark.parametrize(("key", "fd_id", "slug"), [
    ("86-real-madrid", 86, "real-madrid"),
    ("real-madrid", None, "real-madrid"),
    ("564762-real-madrid-v-norte-2026-11-28", 564762, "real-madrid-v-norte-2026-11-28"),
    ("70017-kai-delantero", 70017, "kai-delantero"),
    ("1860-munchen", 1860, "munchen"),
    ("86", None, "86"),
    ("12345678901-x", None, "12345678901-x"),
])
def test_the_grammar_reads_an_id_and_a_slug(key, fd_id, slug):
    assert parse(key) == Key(fd_id=fd_id, slug=slug, whole=key)


@pytest.mark.parametrize("key", [
    "", "Real-Madrid", "real_madrid", "real--madrid", "-real", "real-", "86-", "86--x",
    "vinícius-junior", "real madrid", "86-real madrid", "../etc", "a/b", "a.b",
    "es.1-2026-0123456789abcdef", "real-madrid/", " real-madrid",
])
def test_the_grammar_refuses_what_is_not_a_key(key):
    assert KEY.fullmatch(key) is None
    assert parse(key) is None


def test_parse_refuses_what_is_not_text():
    assert parse(86) is None
    assert parse(None) is None


def test_the_madrid_key_is_the_one_the_rule_writes():
    assert entity_key(MADRID_FD_ID, "Real Madrid") == MADRID_KEY == "86-real-madrid"
    assert entity_key(None, "Real Madrid") == "real-madrid"


@pytest.mark.parametrize("bad", [True, -1, 10**10, 1.5, "86"])
def test_an_id_outside_the_grammar_writes_no_key(bad):
    with pytest.raises(ValueError):
        entity_key(bad, "Real Madrid")


def test_a_match_key_names_both_clubs_and_the_day_and_parses_back():
    key = match_key(564762, "Real Madrid", "Alavés", date(2026, 11, 28))
    assert key == "564762-real-madrid-v-alaves-2026-11-28"
    assert parse(key) == Key(564762, "real-madrid-v-alaves-2026-11-28", key)
    assert match_key(564762, "Real Madrid", "Alavés", "2026-11-28") == key
    cup = match_key(None, "Atlético Prueba", "Real Madrid", date(2027, 1, 15))
    assert cup == "atletico-prueba-v-real-madrid-2027-01-15"
    assert parse(cup).fd_id is None
    with pytest.raises(ValueError):
        match_key(1, "Real Madrid", "Norte", "28 November 2026")


def test_a_slug_that_begins_with_digits_keeps_its_whole_reading():
    """Without an id from football-data.org, ``1860-munchen`` is a slug; ``whole`` keeps it."""
    read = parse("1860-munchen")
    assert (read.fd_id, read.slug, read.whole) == (1860, "munchen", "1860-munchen")


def test_legacy_keys_are_read_by_openfootballs_rule():
    assert legacy("es.1-2026-0123456789abcdef") == ("es.1", 2026)
    assert legacy("ucl-2026-fedcba9876543210") == ("ucl", 2026)
    assert legacy("es.1-2026-0123456789ABCDEF") is None
    assert legacy("xx.1-2026-0123456789abcdef") is None
    assert legacy("86-real-madrid") is None
    assert legacy(None) is None
    assert parse("es.1-2026-0123456789abcdef") is None


@pytest.mark.parametrize(("short", "tla", "expected"), [
    ("Real Madrid", "RMA", "RMA"),
    ("Real Madrid", " rma ", "RMA"),
    ("Real Madrid", None, "RM"),
    ("Real Madrid", "", "RM"),
    ("Norte CF", None, "NOR"),
    ("Ribera Alta", None, "RA"),
    ("FC Test City", None, "TC"),
    ("Atlético Prueba de la Sierra", None, "APD"),
    ("Ölçü", None, "OLC"),
])
def test_a_plate_is_the_sources_tla_else_the_declared_initials(short, tla, expected):
    assert plate(short, tla) == expected


def test_a_plate_alias_is_the_only_departure_from_the_rule(monkeypatch):
    assert keys.PLATE_ALIASES == {}
    monkeypatch.setitem(keys.PLATE_ALIASES, "Ribera Alta", "RIA")
    assert plate("Ribera Alta") == "RIA"
    assert plate("Ribera Alta", "RAL") == "RAL"
    with pytest.raises(ValueError):
        plate("FC")


def test_model_keys_pass_the_reply_key_guard():
    """B5, until the season routes exist: every model object's JSON (the full and the sparse
    sample of each class) carries no key ``banned_key_paths`` refuses with
    ``BANNED_KEY_PARTS``."""
    from test_season_model import SAMPLES

    from galactico.match_centre.season.model import to_json

    for samples in SAMPLES.values():
        for cls, obj in samples.items():
            assert banned_key_paths(to_json(obj), parts=BANNED_KEY_PARTS) == [], cls.__name__
