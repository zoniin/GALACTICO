# E-09 pipeline specification

Companion to `preregistration.md` and `config.json` (same folder). The protocol says what is
decided; this file says what to build. **It is frozen with them:** it is committed in the
registration commit byte for byte as it stands here, its `lf_sha256` is
`pipeline_spec_sha256` in the config, and phase 1 of the runner refuses a mismatch. Where
this file and the protocol disagree, the protocol wins and this file is the defect.

Every number an implementer needs is in `config.json`. Product code cannot read an
experiment's config (ROOT 3b: `galactico/domain/verdicts.py` is the only thing product code
reads from research; `pyproject.toml` packages only `galactico`), so the product-side WP-A
holds its definition values as module constants that `tests/test_candidates.py` ties to the
config (section 3), as E-10's `descriptors.py` does; WP-B receives every value as a
parameter; WP-C to F read thresholds, seeds, lists and sentences from the loaded config. A
numeric literal for a threshold in WP-C, D or E code is a review failure (section 9), and no
function takes a default for a value that is in the config.
Config keys that restate a rule as a sentence (`minutes_rule`, `split_rule`, `ece_binning_rule`
and the like) are read by assertions, not by branches: the pipeline asserts the frozen value
and implements only that value.

---

## 0. Files, ownership, order

Packages, buildable in parallel against the interfaces below. Each owns only the files
listed. All are developed and tested on **synthetic data only**.

| WP | Owns (all new) | Depends on |
|---|---|---|
| A | `galactico/features/candidates.py`, `tests/test_candidates.py` | `features/spec.py` (`Scaling`), `features/axes.py` (`AxisSpec`), `domain/provenance.py` (`EvidenceClass`) |
| B | `galactico/models/shots/{__init__,geometry,logistic,model}.py`, `tests/test_shot_model.py` | numpy, pandas |
| C | `galactico/validation/shot_model_evaluation.py`, `tests/test_shot_model_evaluation.py` | B |
| D | `galactico/validation/candidate_gauntlet.py`, `tests/test_candidate_gauntlet.py` | A, C (types only), `reliability/`, `validation/{lifecycle,replication}.py`, `features/axes.py::compute_baselines` |
| E | `galactico/validation/candidate_synthetic.py` (generators only), `experiments/run_candidate_gauntlet.py` (the runner and `run_selfcheck`), `tests/test_candidate_planted.py`, `tests/test_candidate_runner.py`, `tests/test_candidate_pins.py` | A to D |
| F (LOCAL; built and pinned in the pipeline commit with the rest, its run conditional and lowest priority) | `galactico/validation/candidate_sb.py`, `tests/test_candidate_sb.py` | A to D; `validation/sb_reader.py` and `validation/provider_inputs.py` unchanged |

Root owns: the registration commit and every shared-file edit of section 13, the real run,
`results.json`, `analysis.md`, `MODEL-CARD.md`, every registry edit of section 11.

**Registration-time edits** (section 13). `PIPELINE.md` is registered byte for byte.
`config.json` is registered byte for byte after the root has written the keys of
`counted_by_root_before_registration` into the draft (`counted_by_root_rule`): those keys are
the only edits to it after the audit, and the root's committed script and its output are
named in the registration commit. The three keys of `counted_by_root_assumption_pins` are
counted and never edited: the frozen text depends on their values, so a count that departs
from them stops registration and returns the draft to revision and audit
(`counted_by_root_assumption_rule`). `preregistration.md` is registered after two edits and no other: the DRAFT banner
(the one-line block quote under the title, which holds the only relative links but one) is
replaced by the one line
`> References such as ROOT 2.5 or R12 point to [ROOT-DECISIONS.md](../../../docs/research/north-star/ROOT-DECISIONS.md); the working notes they cite are described in the [README](../../../docs/research/north-star/README.md) beside it.`,
and the logo path `../../../../assets/statsbomb/statsbomb-logo.png`, which resolves from the
draft folder, becomes `../../../docs/assets/statsbomb/statsbomb-logo.png`, which resolves
from `committed_experiment_dir`. `REVIEW-RECORD.md` stays in the draft folder as the record
of review; the draft `preregistration.md` and `PIPELINE.md` become one-line pointers to the
registered directory, and the draft `config.json` is deleted, since a pointer line is not
JSON (E-11's draft folder holds two pointers and no config).

**Key names.** No key, at any depth, of `config.json`, `results.json` or the LOCAL file of
the external leg contains `statsbomb`, `pappalardo` or `wyscout` in any letter case, or
starts with `SB_`. A key that concerns the local-tier provider has `sb` as one of its
`_`-separated parts (`sb_root`, `penalty_area_sb`, `sb_verdict_vocabulary`); one that names
the public provider's side beside it has `wy` (`wy_league_of_sb_folder`); `key_naming`.
Values may name a provider. `tests/test_licensing.py` enforces the first name and the `SB_`
prefix on every JSON file under `experiments/`; the runner test of section 8.4 enforces all
three names at every depth. Source paths are values, never keys: `source_hashes` is a list
of `{"path", "lf_sha256"}` objects (section 7.2), so `galactico/providers/pappalardo.py` is
pinned without a key naming its provider. The LOCAL module is `candidate_sb.py` because the
house keeps provider names out of the file paths of a protocol. The same rule holds for the
self-check stamp `selfcheck.json`.

**Licence-guard traps.** Never write, in any committed file, a double-quoted
`possession_team`, `freeze_frame`, `obv_total_net` or `shot_statsbomb_xg`; never a
double-quoted `eventId`, `subEventId`, `matchPeriod` or `tagsList` followed by a colon. No
provider xG field and no freeze frame is read, at all.

**Engineering.** `from __future__ import annotations`; frozen dataclasses; full type hints;
`__all__`; numpy and pandas only (no scipy); ruff clean (line length 100); paths anchored at
`Path(__file__).resolve().parents[n]`; module docstrings state claim and non-claim.

## 1. Shipped interfaces (verified against the code on 14 October 2026)

| # | Provider | Interface | E-09 use | Failure |
|---|---|---|---|---|
| I1 | `galactico/ingestion/sidecar.py` (ADR-0028) | `verify(league)`; `manifest(league)` (`sidecar_schema_version`, `tag_mapping_version`, `actions_event_ids_equal`); `load(league, "events", columns=sidecar_columns)` (one row per raw event that has a position: the `event_id` set of `actions.parquet`); `attach(actions, events, ["body_part", "shot_family"])`, the only sanctioned join; `provenance(league)`. `body_part` is `left_foot`, `right_foot`, `head_or_body`, or null for none or several; `shot_family` is `open_play`, `free_kick`, `penalty` or null | body part on every shot row; the shot-family pins | `SidecarMissing`, `SidecarStale`, `SidecarMismatch`, a manifest whose versions differ from `sidecar_schema_version` / `sidecar_tag_mapping_version`, or `actions_event_ids_equal` not true (`sidecar_requires_actions_event_ids_equal`): phase 2 stops. E-09 contains no tag parsing of its own |
| I2 | `galactico/validation/digests.py` | `lf_sha256(path)`, `lf_sha256_text(text)` | every protocol, config, pipeline and source hash, and the hash of `decide`'s source | — |
| I3 | `galactico/domain/verdicts.py` | `VerdictRecord(experiment_id, subject_id, scope, tier, directory, claim_token, non_claim, not_run_statement, vocabulary, outcomes, protocol_hash, config_hash, token, protocol_commit, results_hash, figures)`; `Outcome(status, limits, statement, registry_move)`; rules V1 to V7; `product_admissible` | five PUBLIC records, `PENDING` at registration (section 11.1) | — |
| I4 | `galactico/domain/thesis.py` | `banned_key_paths(payload, parts=BANNED_KEY_PARTS)` | phase 7 and `tests/test_candidate_runner.py` check every key of `results.json`, `provenance.config` included; E-11 called it without `parts`, and E-09 keeps the stricter call, so no config key holds one of the eight parts (`rank_ties` became `tie_policy`) | — |
| I5 | `tests/conftest.py` | `league_available(competition)` (skips cleanly without the league's frames); no per-league sidecar fixture exists | `tests/test_candidate_pins.py` only, plus an inline skip when `sidecar.manifest(league)` raises `SidecarMissing` | — |
| I6 | `galactico/storage/public.py` | `load_public(league, tables=public_tables, action_columns=action_columns)`: the hosting guard and `provider == "pappalardo"` on every action row | every neutral frame | `LicenseViolation`, `FileNotFoundError`: phase 2 stops |
| I7 | E-11 (registered) | `aggregated_player_quantities` of its config (`e11_config_sha256`); its own `provider_inputs` defines its inputs and does not read `galactico.features.candidates` | the two imported definitions (protocol section 1) | the root recomputes `lf_sha256` of E-11's config before registration (`verified_by_root_before_registration`) |
| I8 | H2 repairs | none relied on | — | E-09 never calls `AxisReliability.lower_bound` (it now returns NaN without an interval), `grade`, `ConfoundVerdict.passed` or `ActionFilter.describe` |

E-09 computes no team-level quantity. If E-10 wants a conceded location value it depends on
the E-09 instrument token and must say so.

## 2. Reuse

| Reused unchanged | From | For |
|---|---|---|
| `decide(reliability_low, confound_r2, baseline_r, kind_is_nuisance)` | `experiments/run_replication.py`, pinned by `frozen_rule_decide_source_sha256` and `frozen_rule_constants` (injected, never copied) | league status |
| `_safe_abs_corr` | same module, pinned by `frozen_correlation_source_sha256` (injected as `correlation`, never copied) | battery correlations, after the guard: 0.0 for a constant vector, NaN under three finite pairs, pairwise-finite rows |
| `split_half_reliability(first, second, correct=False)`, `spearman_brown`, `AxisReliability(...).interval` | `galactico/reliability/core.py` | `r_half`, `r_sb`, the reported house interval. `split_half_reliability` takes **mappings keyed by player id**: it is called with `series.to_dict()` on the index of R, as `run_replication.py` does; a `pd.Series` passed directly is iterated by value and returns `(nan, 0)` |
| `discriminant_validity(..., ties=tie_policy)`, `residualise` | `galactico/reliability/confound.py` | the reported joint audit. Under `ties="average"` a tied k-th place gives `top_k_survivors=None` with `top_k_tied_raw` and `top_k_tied_adjusted` |
| `compute_baselines(actions, minutes)` | `galactico/features/axes.py` | eight house battery columns and `minutes`, called with the minutes of `minutes_rule` |
| `Status`, `LeagueResult`, `classify_replication`, `ConfoundFinding`, `ConfoundKind` | `galactico/validation/{lifecycle,replication}.py` | status enum; reported labels |
| `Scaling` | `galactico/features/spec.py` | scaling enum of a `CandidateSpec` |
| `AxisSpec` | `galactico/features/axes.py` | the claim record of each candidate |
| `EvidenceClass` | `galactico/domain/provenance.py` | evidence class on each spec |
| `load_public`, `assert_may_host` | `galactico/storage/public.py`, `galactico/providers/base.py` | licence posture in the runner |

Not reused, deliberately: `fit_league_xt` / `fit_xt` (no candidate uses xT); `run_league`
(v1 estimator, goalkeeper-inclusive, joint R-squared); `ConfoundVerdict.passed` (a different
rule); `AxisReliability.lower_bound`; the `ConstructSpec` machinery of `spec.py` (ROOT 4: a
definition and its implementation are one object, so `shot_volume` exists once, as a
`CandidateSpec`; section 11.2 generates any `ConstructSpec` form from it at promotion, ROOT
2.10 W3).

`experiments/` is a namespace package. The runner and the tests put the repository root on
`sys.path` (anchored to `Path(__file__)`), then `from experiments.run_replication import
decide, _safe_abs_corr`. Library modules never import `experiments` (`pyproject.toml`
packages only `galactico`, so such an import fails outside a checkout): `decide` and
`_safe_abs_corr` are parameters, `rule` and `correlation`, passed by the runner and the
tests.

## 3. `galactico/features/candidates.py` (WP-A)

Module docstring states: candidates are definitions under test, held outside `spec.SPECS`
because a sixth key there breaks five shipped things; nothing here is a validated construct;
the dict is named `CANDIDATES`, never `SPECS`.

This is a product module (`features` is in the `PRODUCT` tuple of
`tests/test_research_firewall.py`; ROOT 2.5 O3, 2.9 Z3), and product code cannot read an
experiment's config (section 0). Every value below that the config also holds is therefore
a module literal, written once (E-10 PIPELINE 3.7): the three `Zone` records (bounds,
fingerprint strings, phrases), `SENTINEL_STARTS`, `DESCRIBE_NOUNS`, the four `CandidateSpec`s
and the `CLAIMS` texts. The module opens no file and names no path to an experiment
directory; `tests/test_candidates.py` reads the frozen `config.json` (tests are not packaged)
and asserts that each literal equals it. It holds no display name: no product caller needs
one in this release, and the results commit writes `DISPLAY_NAMES` into
`galactico/profiles/build.py` (11.1).

```python
class CandidateMeasure(Enum):
    COUNT = "count"
    SUM_CONVERSION_VALUE = "sum of location-only conversion value"

@dataclass(frozen=True)
class Zone:
    zone: str                              # literal; equals config zones[*].zone (test)
    fingerprint: str                       # literal, e.g. "opponent_half[x>0.5]"; equals config zones[*].fingerprint (test)
    phrase: str                            # literal; equals config zones[*].phrase (test)
    min_start_x_exclusive: float | None = None
    min_start_x_inclusive: float | None = None
    min_start_y_inclusive: float | None = None
    max_start_y_inclusive: float | None = None
    def mask(self, actions: pd.DataFrame) -> pd.Series      # False on sentinel starts

ZONES: dict[str, Zone]                     # literal: three zones keyed by zone; equal to config["zones"] (test)
SENTINEL_STARTS: tuple[tuple[float, float], ...]   # literal; equals config["location_sentinels"] (test)
DESCRIBE_NOUNS: Mapping[str, Mapping[str, str]]    # literal; equals config["describe_nouns"] (test)

@dataclass(frozen=True)
class Clause:
    types: frozenset[str] = frozenset()
    subtypes: frozenset[str] = frozenset()
    flags: frozenset[str] = frozenset()    # boolean columns, all must be true
    zone: str | None = None
    def mask(self, actions: pd.DataFrame) -> pd.Series
    def noun(self) -> str
    @property
    def fingerprint(self) -> str

@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: str                            # "volume" | "style"
    measure: CandidateMeasure
    numerator: tuple[Clause, ...]          # union of clauses, each row counted once
    scaling: Scaling
    denominator: tuple[Clause, ...] = ()
    instrument: str | None = None
    evidence_class: EvidenceClass = EvidenceClass.DERIVED
    def describe(self) -> str
    @property
    def fingerprint(self) -> str

CANDIDATES: dict[str, CandidateSpec]       # literal: 4 specs keyed by candidate_id, config order; equal to config candidates (test)
CLAIMS: dict[str, AxisSpec]                # literal: same 4 keys; fields equal config candidates[*].claim (test)

def rows(clauses: tuple[Clause, ...], actions: pd.DataFrame) -> pd.DataFrame
def capped_minutes(lineups: pd.DataFrame, *, cap: int) -> pd.Series     # minutes_rule
def evaluate_candidate(spec: CandidateSpec, actions: pd.DataFrame, minutes: pd.Series, *,
                       shot_values: pd.Series | None = None) -> pd.Series
__all__ = [...]
```

| Element | Exact behaviour |
|---|---|
| `Clause.mask` | AND of: `type in types` if `types`; `subtype in subtypes` if `subtypes`; each flag column truthy after `fillna(False)`; `ZONES[zone].mask` if `zone`. An empty clause raises `ValueError`; a flag named `success` or `clearance` raises |
| `Zone.mask` | the declared comparisons on `start_x`, `start_y`, AND NOT (start equals a sentinel pair). `opponent_half` is `start_x > 0.50` strictly; `penalty_area` is `start_x >= 0.84` and `0.19 <= start_y <= 0.81`; `penalty_area_sb` (external leg only, `zone_use`) is `start_x >= 0.85` and `0.225 <= start_y <= 0.775` |
| literals | every value of this module that the config holds is a literal, tied to `config.json` by `tests/test_candidates.py`; each `Zone`'s fingerprint is a literal string equal to the config's, never formatted from the bounds; `CANDIDATES` keyed by `candidate_id`; a config key `id` or `name` anywhere is a defect (section 7, phase 7). The module opens no file: it makes no call whose terminal name is `open`, `load` or `loads` or starts with `read_`, imports only from the allowlist of the test below, and holds no string constant, other than its docstring, containing `experiments` or `config.json` |
| `CLAIMS` | a literal `AxisSpec(key=candidate_id, family=family, construct=..., observable_implication=..., confounds=..., negative_control=..., incremental_claim=..., confound_kinds=...)` per candidate, whose fields equal config `candidates[*].claim` (construct, observable implication, negative control, incremental claim), `family`, `tuple(confound_kinds)` and `dict(confound_kinds)` (test); no other text |
| `rows` | rows matching any clause; `actions[mask_1 \| mask_2 \| ...]`; each row once |
| `capped_minutes` | `lineups.minutes.clip(upper=cap)` per row, summed by `player_id`; `cap` is `regulation_minutes_cap` |
| `Clause.fingerprint` | `"\|".join([",".join(sorted(types)), ",".join(sorted(subtypes)), ",".join(sorted(flags)), ZONES[zone].fingerprint if zone else "-"])` |
| union fingerprint | `"+".join(sorted(clause fingerprints))`; `"-"` for an empty tuple |
| `CandidateSpec.fingerprint` | `sha256("\x1f".join([candidate_id, measure.value, numerator_fp, scaling.value, denominator_fp, instrument or "-"]).encode()).hexdigest()[:12]` |
| `Clause.noun` | from `DESCRIBE_NOUNS`, which equals config `describe_nouns` (test): the subtype noun if `subtypes` (one subtype); else the flag noun if `flags` (one flag, no `types`); else the plural type noun (one type) |
| `CandidateSpec.describe` | `"{measure phrase} over {numerator phrase}, {scaling phrase}"`. Numerator phrase: one clause gives `noun + " " + zone phrase` (zone phrase omitted when there is no zone); several clauses that share one zone give their nouns joined by `" or "` in config order, then `", "`, then the zone phrase; several clauses with no zone give their nouns joined by `" or "` and nothing after. Scaling phrase: `per 90 minutes`, or `per ` + the singular noun of the one denominator clause's type (`types_singular`) |
| `__post_init__` | `PER_SELECTED_ACTION` without denominator raises; `PER_90` with one raises; `SUM_CONVERSION_VALUE` without `instrument` raises; `COUNT` with one raises; empty numerator raises; and every shape `describe` cannot word raises (`describe_refusals`): a clause with both types and flags, a clause with more than one type, subtype or flag, numerator clauses with different zones, a denominator of more than one clause, a denominator type without a singular noun, a noun missing from `describe_nouns` |
| `evaluate_candidate`, COUNT | `numerator = rows(...).groupby("player_id").size().reindex(minutes.index).fillna(0.0)` |
| `evaluate_candidate`, SUM | `shot_values` required (Series indexed by `event_id`); every numerator row's `event_id` must be present or `KeyError` naming the count missing; sum per `player_id`, reindexed, `fillna(0.0)` |
| scaling | `PER_90`: `numerator * (90.0 / minutes.replace(0, nan))`, the expression and order of operations of `compute_baselines`, so `shot_volume` equals its `shots_per_90` bit for bit (`(c * 90) / m` and `c * (90 / m)` differ in the last bit in about a quarter of integer cases). `PER_SELECTED_ACTION`: `numerator / rows(denominator).groupby("player_id").size().reindex(index).replace(0, nan)`; no denominator rows gives NaN, never 0 |
| unit | output index is `minutes.index`; a `player_id` of 0 is never in it |

Pinned payloads (the fingerprints in `config.json` were computed from exactly these; `<US>`
is `\x1f`):

| id | payload | sha256[:12] | `describe()` |
|---|---|---|---|
| `shot_volume` | `shot_volume<US>count<US>shot\|\|\|-<US>per 90 minutes<US>-<US>-` | `1c6517c2be31` | `count over shots, per 90 minutes` |
| `shot_location_value` | `shot_location_value<US>sum of location-only conversion value<US>shot\|\|\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>shot_location_v1` | `537cef62eb4e` | `sum of location-only conversion value over shots starting in the opponent half, per 90 minutes` |
| `box_shot_share` | `box_shot_share<US>count<US>shot\|\|\|penalty_area[x>=0.84;0.19<=y<=0.81]<US>per action in the denominator set<US>shot\|\|\|-<US>-` | `af2b2b118e73` | `count over shots starting in the penalty area, per shot` |
| `opp_half_defensive_actions` | `opp_half_defensive_actions<US>count<US>duel\|Ground defending duel\|\|opponent_half[x>0.5]+\|\|interception\|opponent_half[x>0.5]<US>per 90 minutes<US>-<US>-` | `72619cd8130b` | `count over ground defending duel records or interception-flagged events, starting in the opponent half, per 90 minutes` |

If an implementation yields another fingerprint the implementation is wrong. A verdict
attaches to these fingerprints. The house `ConstructSpec.describe` grammar differs (it would
read "..., per shots"); a later `SPECS` registration carries a cross-reference to the
`CandidateSpec` fingerprint it was generated from (section 11.2).

`tests/test_candidates.py` (hand-computable, in the style of `tests/test_spec_contract.py`):
the config tie, which reads the frozen `config.json` and asserts that each literal of the
module equals it: the zones with their bounds, fingerprint strings and phrases;
`location_sentinels`; `describe_nouns`; and for each candidate its clauses, measure, scaling,
denominator, instrument, family, evidence class and every field of its claim (so the
fingerprint, sentence and zone-fingerprint tests below compare two sources, not the config
with itself); the no-file scan, written as `tests/test_research_firewall.py` writes its scan
(`ast.walk` over the whole tree, function bodies included) and run on the real module, where
it finds nothing, and on a planted copy, where it finds the defect: `candidates.py` imports
only from `__future__`, `dataclasses`, `enum`, `hashlib`, `collections.abc`, `typing`,
`numpy`, `pandas`, `galactico.features.spec`, `galactico.features.axes` and
`galactico.domain.provenance` (checked with the firewall's own `imports()`; no `json`,
`pathlib`, `os`, `io` or `importlib`), makes no call whose terminal name is `open`, `load` or
`loads` or starts with `read_`, and holds no string constant other than its docstring that
contains `experiments` or `config.json`; fingerprints and sentences equal `config.json`;
`describe` follows its rule on
two invented specs beyond the four; zone edges at 0.50 / 0.51 and 0.83 / 0.84, 0.18 / 0.19,
0.81 / 0.82; sentinel starts excluded from zone clauses and kept in zone-free clauses; a row
matching both clauses of the union counted once; a flagged clearance counted once, as an
interception; a penalty and a direct free-kick shot (`type == "set_piece"`) never counted;
`player_id` 0 never credited; `capped_minutes` caps a starter substituted at minute 93 at 90;
`Zone.fingerprint` equals the config string for each zone; each refusal of `describe_refusals`
raises on an invented spec, and several zone-less clauses word without a trailing comma;
per-90 scales with minutes and the share does not; a player with no shots has share NaN and
volume 0.0; `shot_volume` equals `compute_baselines(...)["shots_per_90"]` exactly, bit for
bit, on the same frame with the same minutes (the `PER_90` expression above); the E-11 tie, exhaustive and not a sampled parity test (ROOT 2.10
W3: E-11's registered `provider_inputs.py` is the one duplicate that remains, a recorded
exception to Z3): the test imports `galactico.validation.provider_inputs` (a test may import
it; product code may not) and builds one synthetic neutral frame holding every combination
of the public adapter's closed vocabulary (`galactico/providers/pappalardo.py`): every neutral
`type` of `_TYPE_BY_EVENT_ID` and `other`; under every type, every `subtype` that a rule on
either side reads (the `_SET_PIECE_SUBTYPE` values, the subtypes of E-09's clauses and of
E-11's `wy_*_subtypes` lists), the empty string and one invented string; every combination of
the boolean columns the adapter writes (`goal`, `assist`, `key_pass`, `counter_attack`,
`interception`, `clearance`, `dangerous_loss` true or false, and `success` true, false or
null); and the starts (0.50, 0.5), (0.51, 0.5), one own-half start, one opponent-half start
and both `location_sentinels`; every row in a regulation period of one invented linked match,
passed through E-11's `harmonise_wyscout` with E-11's registered config. The input frame's row
count is asserted equal to the product of those sizes, so no combination is missing; the
harmonised frame is asserted to have as many rows as the input (`harmonise_wyscout` drops a
row of an unlinked match or of a period outside `wy_regulation_periods` silently, so a
fixture error would otherwise shrink the comparison), its `event_order` is asserted to be a
permutation of `range(n)`, and rows are compared aligned on `event_order` (a row's position in
the input), since `harmonise_wyscout` sorts its output. On every row,
E-11's `open_play_shot` flag equals the mask of `rows(shot_volume.numerator)`, and E-11's
`duel_or_interception` flag with a finite start x above `opponent_half_x_minimum_exclusive`
equals the mask of `rows(opp_half_defensive_actions.numerator)`. `provider_inputs.py` is
pinned in `source_hashes` (section 7.2), so an edit on either side is visible to the protocol
(E-11's own slow test ties its Wyscout `minutes_regulation` to `lineups.parquet` minutes
clipped at the cap, which is `capped_minutes`); a missing `event_id` in `shot_values` raises;
`CANDIDATES.keys()` is
disjoint from `spec.SPECS` and `CONSTRUCTS` (membership of `REJECTED`, `RESEARCH_ONLY`,
`TESTED_NOT_PROMOTED` and `UNTESTED` is tied to the committed token by the tests of 11.1,
since the results commit puts every candidate in one of them); `spec.SPECS` has exactly its
five shipped keys; no clause can read `success` or `clearance`; every sentence and `CLAIMS`
text passes `labels.scan_labels` (the display names are scanned by the draft guard of
section 13 and, once written, by the copy-guard test of 11.1); no key or family string is in
the banned set.

## 4. `galactico/models/shots/` (WP-B)

Product-side package: pure functions, no threshold, no verdict, no file access. Package
docstring: "A location-only shot conversion model. It is a model (PREDICTIVE). It is not xG
supplied by the provider; the provider supplies none. It sees where a shot started and
whether the provider classed it head-or-body. It does not see defenders, the goalkeeper,
pressure, shot type, the shooter or the team. It says nothing about finishing."

```python
# geometry.py
def shot_geometry(start_x: np.ndarray, start_y: np.ndarray, *, pitch_length_m: float,
                  pitch_width_m: float, goal_width_m: float) -> tuple[np.ndarray, np.ndarray]
    # (distance_m, angle_rad) by the formulas of preregistration 4.1; atan2, no branch

# logistic.py
@dataclass(frozen=True)
class LogisticEstimate:
    coefficients: np.ndarray
    standard_errors: np.ndarray | None     # None when X'WX is singular at the returned coefficients
    log_likelihood: float
    iterations: int
    converged: bool
def estimate_logistic(design: np.ndarray, outcome: np.ndarray, *, offset: np.ndarray | None,
                      max_iterations: int, tolerance: float, max_halvings: int,
                      halving_relative_tolerance: float) -> LogisticEstimate
def logistic_values(coefficients: np.ndarray, design: np.ndarray, *,
                    offset: np.ndarray | None) -> np.ndarray

# model.py
@dataclass(frozen=True)
class ShotModelSpec:
    model_id: str                          # "M0" | "MD" | "M1" | "MFLEX"
    terms: tuple[str, ...]                 # exactly config["model_terms"][model_id]
def shot_models(config: Mapping) -> dict[str, ShotModelSpec]
SHOT_COLUMNS = ("event_id", "game_id", "team_id", "player_id", "start_x", "start_y",
                "distance_m", "angle_rad", "head_or_body", "counter_attack", "goal")
def shot_frame(actions: pd.DataFrame, *, in_domain: pd.Series, geometry: Mapping) -> pd.DataFrame
    # actions carries body_part (sidecar.attach); SHOT_COLUMNS, sorted by event_id
def design_matrix(spec: ShotModelSpec, shots: pd.DataFrame) -> np.ndarray
@dataclass(frozen=True)
class FittedShotModel:
    spec: ShotModelSpec
    coefficients: tuple[float, ...]
    standard_errors: tuple[float, ...] | None
    n_shots: int
    n_goals: int
    base_rate: float
    log_likelihood: float
    iterations: int
    converged: bool
def estimate_shot_model(spec: ShotModelSpec, shots: pd.DataFrame, *, max_iterations: int,
                        tolerance: float, max_halvings: int,
                        halving_relative_tolerance: float) -> FittedShotModel
def conversion_values(model: FittedShotModel, shots: pd.DataFrame) -> np.ndarray
```

| Element | Exact behaviour |
|---|---|
| `shot_frame` | rows with `type == "shot"` where `in_domain` is true; the caller passes `ZONES["opponent_half"].mask(actions)`, so the model domain and the numerator of `shot_location_value` are one predicate (no sentinel start, `start_x > 0.50`); `head_or_body = (body_part == head_or_body_value)` as int; a shot row with null `body_part` raises `ValueError` with the count (coverage is an assumption pin, `counted_by_root_assumption_pins`: a root count below 1.0 stops registration, so on the registered corpus the raise is a guard); includes `player_id` 0 rows (location and label are valid); `goal` as int |
| terms | `intercept` 1; `distance_m`; `angle_rad`; `head_or_body`; `a*b` product; `hinge(v,k)` is `max(v - k, 0)` |
| `estimate_logistic` | Newton / IRLS from zero coefficients on internally standardised non-constant columns, back-transformed; the log-likelihood is `sum(y * eta - logaddexp(0, eta))`, finite for every finite `eta`. Each iteration computes the full Newton step on the standardised scale. If its largest absolute component is below `tolerance` (`irls_tolerance`), that full step is taken, unhalved, and the fit stops with `converged=True`; the stop is judged on the full step, never on a halved one. Otherwise the step is halved while the log-likelihood at the new point falls below the current one by more than `halving_relative_tolerance` x the current one's absolute value (`irls_halving_relative_tolerance`), at most `max_halvings` times (`irls_max_halvings`), so a change at the last bit of a summed log-likelihood is not read as a fall; if after `max_halvings` halvings it still falls by more than that, the fit stops with `converged=False` at the iterate before the step. `converged=False` also at `max_iterations` (`irls_max_iterations`) and on a singular information matrix; never an exception. A non-converged estimate keeps the last iterate it reached (finite, since every iterate is), `standard_errors = sqrt(diag(inv(X'WX)))` at the returned coefficients, or `None` when `X'WX` is singular there; no penalty |
| `M0` | not fitted: `conversion_values` returns the training goal rate for every row, `converged=True` by definition |
| `conversion_values`, `logistic_values` | a numerically stable logistic (`expit` written with `np.exp` of a non-positive argument only), unclipped; in float64 a value can be exactly 0.0 or 1.0 (the TOO_SHARP scenario produces both), which `log_loss` clips at `probability_clip` and `calibration_*` clip for the logit; no test asserts the open interval |

`tests/test_shot_model.py`: geometry at hand-computed points (penalty spot (0.895, 0.5):
d 11.025 m; goal-line centre: theta pi; goal-line outside the post: theta 0; symmetry in
`start_y` about 0.5); a (1,1) and a (0,0) shot are outside `shot_frame` and a (0.51, 0.5) shot
is inside; design matrices term by term; recovery of planted coefficients within four
standard errors at 40,000 synthetic shots; at a converged fit of `M1` and of `MFLEX` on
40,000 synthetic shots, for each of 20 seeds, the log-likelihood gradient `X'(y - p)` is below
1e-6 in absolute value and one further unhalved Newton step changes no standardised
coefficient by more than `irls_tolerance` (the scale the stopping rule controls); a planted
step whose log-likelihood changes only at the last bit is not halved; `M0` equals the
training mean; a permutation of the rows of `actions` changes no byte of `shot_frame`'s output
or of the fit (`shot_frame` sorts by `event_id`), and a permutation of the design rows passed
to `estimate_logistic` directly changes no coefficient by more than 1e-9; a separable toy
sample returns `converged=False` with finite coefficients; a singular information matrix
returns `converged=False` and `standard_errors` `None`; offset fit recovers a known intercept; the
symbol test: every identifier the package defines in `galactico/models/shots/` (an `ast`
walk over function, class and argument names, names assigned at module or function level,
dataclass field names and dict-literal string keys; attribute names of library calls such as
`reset_index`, docstrings and comments are not read), split on `_` and at a change of case
and lower-cased, has no part among the one-word entries of `labels.BANNED_LABEL_TOKENS` and
no part `xg`. The required names pass it (`logistic_values`, `conversion_values`,
`estimate_logistic`, `LogisticEstimate`, `estimate_shot_model`, `FittedShotModel`,
`shot_frame`, `head_or_body`, `goal`, `converged`); `fit` is a banned token, which is why
no defined name holds it. The package docstring's "It is not xG supplied by the provider"
is not an identifier and is not read.

## 5. `galactico/validation/shot_model_evaluation.py` (WP-C)

```python
def brier(p: np.ndarray, y: np.ndarray) -> float
def log_loss(p: np.ndarray, y: np.ndarray, *, clip: float) -> float
def skill(loss: float, reference_loss: float) -> float | None           # 1 - loss/reference; None if reference <= 0
def observed_over_expected(p: np.ndarray, y: np.ndarray) -> float | None
def calibration_slope(p, y, *, clip, max_iterations, tolerance, max_halvings,
                      halving_relative_tolerance) -> float | None
def calibration_intercept(p, y, *, clip, max_iterations, tolerance, max_halvings,
                          halving_relative_tolerance) -> float | None
def calibration_bins(p: np.ndarray, y: np.ndarray, *, n_bins: int) -> list[dict]   # n, mean_probability, observed_rate
def calibration_error(bins: list[dict]) -> tuple[float, float]          # (ece, mce)
def auroc(p: np.ndarray, y: np.ndarray) -> float | None                 # average ranks for ties

@dataclass(frozen=True)
class LoloResult:
    predictions: Mapping[str, pd.DataFrame]   # league -> SHOT_COLUMNS + p_M0, p_MD, p_M1, p_MFLEX
    fits: Mapping[str, Mapping[str, FittedShotModel]]   # held-out league -> model_id -> fit without it
    sample_gate: Mapping[str, object]         # counts per fold; s_count_passed: bool; converged per fold and model; reasons
def leave_one_league_out(shots: Mapping[str, pd.DataFrame], config: Mapping) -> LoloResult
def select_instrument(lolo: LoloResult, config: Mapping) -> dict        # {"instrument", "pooled_gain", "fold_gains", "folds_meeting", "challenger_converged"}
def match_resample_weights(n_matches: int, *, replicates: int, seed: int, league_position: int) -> np.ndarray   # 0-based position
def instrument_report(lolo: LoloResult, instrument: str | None, config: Mapping) -> dict   # section 7 "instrument" block; None on an S-count failure
def instrument_verdict(report: dict, config: Mapping) -> tuple[str, tuple[str, ...]]   # token, failed gate ids
def shot_values(lolo: LoloResult, instrument: str) -> dict[str, pd.Series]   # league -> Series indexed by event_id
```

| Element | Exact behaviour |
|---|---|
| fold f | fit `MD`, `M1`, `MFLEX` on the concatenation of the other leagues' shot frames; predict league f; `p_M0` is the training goal rate |
| gate S-count | evaluated from counts before any fit (`gate_s_count`); on failure return a `LoloResult` with empty `predictions` and `fits` and `s_count_passed=False`; `select_instrument` and `shot_values` are not called, and `instrument_report(lolo, None, config)` returns the null block, computing no statistic: every selection, fit, league and pooled field of the instrument block is null, `failed_gates` is `["S_count"]` and the reason `S_COUNT` (`instrument_inconclusive_rule`) |
| gate S-fit | evaluated in `instrument_report(lolo, instrument, config)`, where the instrument is known: `all(lolo.fits[f][m].converged for f in folds for m in set(gate_s_fit_models) \| {instrument})` (`gate_s_fit_rule`). On the public run this equals the earlier rule, because `MFLEX` is selected only when it converged in every fold; on the external leg it adds the instrument fixed by the public selection. On failure the fits and the R and L statistics are kept and reported with their gates not evaluated (`passed` null), `failed_gates` is `["S_fit"]`, the reason `S_FIT` and the token `INCONCLUSIVE`. A challenger that did not converge in every fold is recorded and is not selectable |
| selection | 4.3 of the protocol; `MFLEX` only when `challenger_converged` is true in every fold |
| resampling | `bootstrap_rule`: `np.random.default_rng([config["seed"], league_position]).multinomial(n, [1/n]*n, size=bootstrap_replicates)`, `league_position` the 0-based index of the held-out league in `leagues` (`position_indexing`; on the external leg the index in `sb_folders`, `sb_leg_config_rule`), `n` the number of unique `game_id`s of the held-out league's in-domain shot frame, in sorted order; statistics recomputed from per-match sums (`sum (p-y)^2`, `sum (p0-y)^2`, log-loss sums of the instrument and of `MD`); pooled statistics add the five leagues' replicate sums |
| intervals | `np.quantile(..., method=interval_quantile_method)` at `interval_quantiles` of the replicate statistic |
| R2 | `gate_r2_gain`: relative gain `(LL_MD - LL_inst) / LL_MD` of the pooled sums, per replicate |
| bins | `ece_binning_rule`: stable sort by probability; `c_0 = 0`, `c_ece_bins = n`; for k = 1 .. `ece_bins` - 1, `c_k` is the smallest `i` with `i >= ceil(k * n / ece_bins)`, `i < n` and `p[i] != p[i-1]`, else `n`; bins are `[c_(k-1), c_k)`, empty bins dropped; a bin never holds part of a run of tied values. No event id enters |
| `calibration_error` | ECE `sum(n_b / n * abs(mean_probability_b - observed_rate_b))` (`ece_weighting`); MCE the largest of those absolute gaps (`mce_rule`) |
| calibration fits | slope: logistic regression of y on `a + b * logit(p)`; intercept: of y on `a` with offset `logit(p)`; `p` clipped at `probability_clip` for the logit; a fit that does not converge returns `None`, which fails its gate in that league (`calibration_fit_failure`) |
| subgroups (R4) | pooled over the five held-out leagues, by the predicates of `gate_r4_subgroups`. Under leave-one-league-out the pooled ratio of a subgroup that is a model term (footed and head-or-body, for an instrument with an intercept and an `H` term) is 1 up to second-order terms, because each fold's training score equations balance the four leagues it trains on; R4 therefore checks a misfit of functional form that all leagues share, mainly in the distance bands (preregistration 4.4, `planning_figures.r4_subgroup_o_e_sd_synthetic_planted`) |
| AUROC | `auroc_rule`: on the concatenated out-of-league predictions; average ranks |
| null calibration error | `ece_null_draws` draws of `y ~ Bernoulli(p)` per league with `default_rng([ece_null_seed, league_position])` (`league_position` as in the resampling row); report the 50th, 95th, 99th percentile of ECE and MCE; reported, not a gate |
| verdict | preregistration 4.5, first failing class wins; `failed` lists the failed gate ids by `instrument_inconclusive_rule`: `["S_count"]`, or `["S_fit"]`, or every failed R and L gate |
| undefined statistic | when S passes, any `None` in a gated statistic fails that gate and is listed. A statistic that is not finite (a model with a non-finite prediction, a `pooled_gain` that cannot be formed) is `None`, never NaN, so phase 7's `allow_nan=False` turns a recorded non-convergence into a verdict, not a failed execution; a non-converged fit's coefficients are its last iterate and its `standard_errors` `None` when its information matrix is singular (section 4) |

`tests/test_shot_model_evaluation.py`: each metric against a hand-computed six-row case;
AUROC with ties; bins of a toy with a tied run straddling a cut: the run stays in one bin and
the result is invariant to row order; ECE of a two-bin toy; skill is `None` on a zero
reference; **leakage** (flipping every label of the held-out league leaves its predictions
byte-identical and changes the other four leagues' predictions); training base rate, not test
rate, is the reference; resample weights depend only on seed and league position; every gate
R1 to R5, L1 to L3, S-count and S-fit reachable in both directions from a hand-built report
dict; a non-converged challenger leaves the instrument at `M1` and S passes; a non-converged
`M1` in one fold gives `INCONCLUSIVE`; with a fixed instrument `MFLEX` (the external leg's
case) that did not converge in one fold, S-fit fails and the token is `INCONCLUSIVE`; an
S-count failure gives, through `instrument_report(lolo, None, config)`, null selection, fits
and metrics, `["S_count"]` and `S_COUNT`; a challenger with a singular information matrix in
one fold gives `None`, never NaN, for its `pooled_gain` and its statistics, and the instrument
`M1`; an S-fit
failure gives `["S_fit"]`, `S_FIT` and R and L gates with `passed` null; a non-converged
calibration fit fails its gate; the bins of `ece_binning_rule` on a hand-built vector whose
cut falls inside, at the start of and at the end of a tied run;
verdict mapping exhaustive over the 2^10 pass/fail combinations with exactly one token each;
the selection rule at both edges (0.0099 / 0.0100 pooled; 3 / 4 folds).

## 6. `galactico/validation/candidate_gauntlet.py` (WP-D)

```python
@dataclass(frozen=True)
class LeagueFrames:
    league: str
    actions: pd.DataFrame      # action_columns minus provider, plus body_part, shot_family (sidecar.attach)
    lineups: pd.DataFrame      # game_id, team_id, player_id, minutes
    players: pd.DataFrame      # player_id, position

@dataclass(frozen=True)
class GateCount:
    league: str; candidate: str
    eligible: int; audit_units: int | None; reliability_units: int
    position_groups: Mapping[str, int]; dropped_position_groups: tuple[str, ...]
    unattributed_share: float | None
    passed: bool; reasons: tuple[str, ...]

@dataclass(frozen=True)
class ReliabilityEstimate:
    n: int; groups: int; r_half: float | None; r_sb: float | None
    house_low: float | None; house_high: float | None; half_low: float | None

@dataclass(frozen=True)
class LeagueEvaluation:
    league: str; candidate: str; gate: GateCount
    status: str                       # "INCONCLUSIVE", or Status.name of decide()'s result: "SHIP" | "SHIP_WITH_BAND" | "REJECT"
    reject_reason: str | None         # "REDUNDANT" | "CONFOUNDED" | "UNRELIABLE"
    inconclusive_reason: str | None   # gate reason, "DEGENERATE:<vector>", "NON_FINITE:<input>", or a league_not_computed_reasons value
    centred: ReliabilityEstimate | None           # gating
    raw_pooled: ReliabilityEstimate | None        # reported
    within_position: Mapping[str, ReliabilityEstimate | None]   # reported
    team_and_position_centred: ReliabilityEstimate | None       # reported; team_and_position_centring
    baseline_correlations: Mapping[str, Mapping[str, float | None]]   # column -> {"raw", "centred", "gating"}
    dropped_battery_columns: tuple[str, ...]
    closest_baselines: tuple[str, ...]; baseline_r: float | None
    nuisance_r2: float | None; nuisance_r2_raw: float | None; nuisance_r2_centred: float | None
    joint_r2: float | None; joint_r2_adjusted: float | None; joint_regressors: int | None
    joint_noise_floor: float | None; ordering_rho: float | None
    top_k_kept: int | None; top_k_tied_raw: int | None; top_k_tied_adjusted: int | None
    house_joint_r2: float | None; house_joint_r2_exceeds_ceiling: bool | None
    damaging_confounds: tuple[str, ...]
    departures_active: tuple[str, ...]            # the lenient departures of preregistration 6.1 in force
    mean: float | None; sd: float | None; zero_share: float | None   # over A, for every league whose count gates passed
    match_set_minutes_share_p05_p95: tuple[float, float] | None
    rule_reasons: tuple[str, ...]

@dataclass(frozen=True)
class CandidateVerdict:
    candidate: str; token: str; rule_row: int
    evaluable: int; surviving: int; ship: int; rejected: int
    statuses: Mapping[str, str]; reject_reasons: Mapping[str, str]
    context_limits: tuple[str, ...]
    house_replication_label: str | None   # classify_replication(...)[0].value

Rule = Callable[[float, float, float, bool], tuple[Status, tuple[str, ...]]]
Correlation = Callable[[np.ndarray, np.ndarray], float]     # run_replication._safe_abs_corr, injected

def match_set_of_game(actions: pd.DataFrame) -> pd.Series                 # index game_id, values 0/1
def eligible_minutes(lineups: pd.DataFrame, players: pd.DataFrame, config: Mapping) -> pd.Series
def player_team(lineups: pd.DataFrame, config: Mapping) -> pd.Series
def unattributed_duel_share(actions: pd.DataFrame, lineups: pd.DataFrame, index: pd.Index) -> pd.Series
def baseline_battery(frames: LeagueFrames, minutes: pd.Series, shot_volume: pd.Series,
                     config: Mapping) -> pd.DataFrame
def count_gates(spec: CandidateSpec, frames: LeagueFrames, config: Mapping) -> GateCount
def centre(values: pd.Series, groups: pd.Series) -> pd.Series
def reliability_estimate(first: pd.Series, second: pd.Series, *, groups: pd.Series | None,
                         config: Mapping, label: str) -> ReliabilityEstimate
def reject_reason(rule: Rule, reliability_low: float, nuisance_r2: float, baseline_r: float,
                  kind_is_nuisance: bool) -> str | None
def evaluate_league(spec: CandidateSpec, frames: LeagueFrames, gate: GateCount,
                    shot_values: pd.Series | None, rule: Rule, correlation: Correlation,
                    config: Mapping) -> LeagueEvaluation
def candidate_verdict(spec: CandidateSpec, evaluations: Sequence[LeagueEvaluation],
                      instrument_token: str, config: Mapping) -> CandidateVerdict
def run_gauntlet(frames: Mapping[str, LeagueFrames], shot_values: Mapping[str, pd.Series] | None,
                 instrument_token: str, rule: Rule, correlation: Correlation,
                 config: Mapping) -> dict
```

| Element | Exact behaviour |
|---|---|
| `match_set_of_game` | `games = sorted(actions["game_id"].unique())`; set = position in `games` modulo 2 (`split_rule`). Identical to `run_replication.py` lines 219 to 223 |
| `eligible_minutes` | `capped_minutes(lineups, cap=regulation_minutes_cap)`; keep `>= minutes_floor`, position in `outfield_positions`, id != 0 |
| `player_team` | team with the most capped minutes; ties to the smallest `team_id` (`player_team_rule`) |
| `baseline_battery` columns | from `compute_baselines(actions[player in index], minutes)`: `minutes, touches, touches_per_90, passes_per_90, pass_completion, mean_x, mean_y, mean_pass_length`; `shot_volume` = the candidate value (asserted equal to `shots_per_90` to 1e-12, same minutes); `opp_half_on_ball_per_90` by `opp_half_on_ball_rule` (types pass or touch, interception flag false, zone `opponent_half`, per 90); `duel_or_interception_per_90` by `duel_or_interception_rule`; `unattributed_duel_share`. All coerced to float64 (`pass_completion` is object dtype upstream) |
| `unattributed_duel_share` | for team t in match m, `u = (ground defending duel rows with player_id 0) / (ground defending duel rows)` (0.0 if none); per player the capped-minutes-weighted mean of `u` over his rows of `lineups` |
| `count_gates` | structure only. A: eligible with a finite full-season value (share floor applied when `share_floor`, counting denominator rows, `share_floor_counts`); R: A with both match-set floors (and match-set share floors); position groups in R below `minimum_position_group` are dropped from R and listed; `unattributed_share` for `opp_half_defensive_actions` = share of pitch-wide union rows with `player_id` 0 in the league; reasons from config gate names |
| match-set values | `evaluate_candidate(spec, actions of match set h for players in R, match-set-h capped minutes, shot_values=...)` |
| `centre` | value minus the mean over the same group among the units passed in |
| `reliability_estimate` | `r_half, n = split_half_reliability(a.to_dict(), b.to_dict(), correct=False)` on the centred values keyed by player id; `g` = groups passed (1 when `groups` is None); `r_sb = spearman_brown(r_half)`; `house = AxisReliability(label, r_sb, n, minutes_floor, period).interval` (None stays None, reported); `half_low = spearman_brown(tanh(atanh(r_half) - interval_z / sqrt(n - 2 - g)))` when `r_half` is finite, `abs(r_half) < 1` and `n - 2 - g >= 1`, else None (`half_low_rule`). The gating value is `half_low` (`reliability_low_rule`) |
| baseline | for each battery column with sd over A at least `degenerate_sd` (others dropped and recorded): `raw = correlation(value, column)` over A; `centred = correlation(centre(value, position), centre(column, position))` over A, `correlation` being the injected house helper (so a constant centred column gives 0.0, not NaN, and a pure position effect is caught by `raw`); no other Pearson is computed in this module; `gating = max(raw, centred)` with NaN propagating (`baseline_centring`); `baseline_r = max(gating)`; `closest_baselines` = every column whose `gating` equals it, in battery order (`baseline_tie_rule`) |
| nuisance | `nuisance_r2 = max(R2 raw, R2 centred)` of the value on `nuisance_columns` over A (`nuisance_centring`), by `residualise`; `None` if there are none |
| joint audit (reported) | `discriminant_validity(value, np.column_stack([touches, team one-hot drop-first, position one-hot drop-first]), key=candidate_id, top_k=top_k, ties=tie_policy)`, an (n, k) float array; adjusted `1 - (1 - R2)(n - 1)/(n - k - 1)`; floor `k/(n - 1)`; `top_k_kept = top_k_survivors` (None on a tie, with the two tied counts and `top_k_tied_statement` in the report); `house_joint_r2` on `[touches, team one-hot]` and its comparison with `nuisance_r2_ceiling`, for candidates with a nuisance column only |
| guard | each vector of `degenerate_vectors` tested on its own: sd below `degenerate_sd`, or zero share above `maximum_zero_share`; then any non-finite rule input or a None `half_low`: status `INCONCLUSIVE`, `inconclusive_reason` names the vector or input, rule not called |
| rule call | `rule(half_low, nuisance_r2 if not None else 0.0, baseline_r, bool(nuisance_columns))` |
| `reject_reason` | `REDUNDANT` if `rule(1.0, 0.0, baseline_r, False)` rejects; else `CONFOUNDED` if `rule(1.0, nuisance_r2, 0.0, kind_is_nuisance)` rejects; else `UNRELIABLE` if `rule(reliability_low, 0.0, 0.0, False)` rejects; else `None`. Thresholds therefore live only in the frozen rule |
| `departures_active` | the departures of preregistration 6.1 that are flagged, in force for this league and candidate: the lenient `identity_column` (`shot_volume`), `presence_column_without_candidate_rows`, `nuisance_only_r2` (candidates with a nuisance column), `goalkeepers_excluded`, and the two-sided `position_centred_reliability` (every league and candidate) |
| within position, context limits | `reliability_estimate` on one position's players in R, uncentred, `g = 1` (`within_position_rule`), when that position has at least `within_position_report_minimum` players; `context_limits` by `context_limit_rule` over the five leagues |
| team and position | `team_and_position_centring`: `reliability_estimate` on the values of R centred within each match set on the cell of `player_team` (`player_team_rule`) and broad position, `groups` that cell, so `g` is the number of cells; reported only |
| `candidate_verdict` | the eight rows of preregistration 9.1, in order; E is the leagues whose status is in `evaluable_statuses`; `rule_row` records which fired; `house_replication_label = classify_replication(...)[0].value` (the function returns the status and a note; the note, which holds counts, is not kept) over evaluable leagues, reported, each built as `LeagueResult(league, axis=candidate_id, n_players=centred.n, reliability=centred.r_sb, reliability_low=centred.half_low, reliability_high=centred.house_high if not None else centred.half_low, confound_r2=nuisance_r2 or 0.0, ordering_rho=ordering_rho if not None else nan, top12_kept=top_k_kept, closest_baseline="+".join(closest_baselines), baseline_r=baseline_r, status=Status[status])`; `None` when E is empty (the house returns `UNREPLICATED` for one league) |
| order in `run_gauntlet` | all `count_gates` for all candidates and leagues first; a candidate with fewer than `minimum_evaluable_leagues` passing gets no statistic computed, and each of its leagues that passed its gates is `INCONCLUSIVE` with `league_not_computed_reasons.too_few_evaluable_leagues`; `shot_location_value` gets none unless the instrument token is `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`, its leagues then `INCONCLUSIVE` with `league_not_computed_reasons.instrument_not_accepted`. Where both reasons apply to a league of `shot_location_value`, `instrument_not_accepted` is recorded (`league_not_computed_precedence`: rows 1 and 2 of 9.1 precede row 3) |

`tests/test_candidate_gauntlet.py`: the imported house `_safe_abs_corr` is passed as
`correlation`, and `lf_sha256_text(inspect.getsource(_safe_abs_corr))` equals
`frozen_correlation_source_sha256`; a spy shows every baseline correlation goes through
`correlation`; a source scan finds no `corrcoef`, `.corr(` or other Pearson in
`candidate_gauntlet.py`; `decide` pinned: `lf_sha256_text(inspect.getsource(decide))`
equals `frozen_rule_decide_source_sha256`, the three module constants equal
`frozen_rule_constants` and equal `baseline_ceiling`, `reliability_number`,
`reliability_band`, and a truth table written from the protocol (edges 0.85 / 0.8501,
0.60 / 0.6001 with and without nuisance, which ties the literal to `nuisance_r2_ceiling` and
`frozen_rule_nuisance_literal`, 0.70 / 0.6999, 0.50 / 0.4999; NaN baseline documented as
passing the raw rule and caught by the guard); `reject_reason` for each of the three reasons
and for none; token rows 1 to 8 each reached, including every case listed in preregistration
9.1, plus exhaustiveness over every multiset of five league statuses with reasons and all
four instrument tokens (one token each, no exception); the status string is `Status.name`
(a `.value` mapping, lower case, would empty E: a test plants it and sees row 3); T24 and "a
pure position effect is caught by the raw correlation" run with the house helper (the
centred value is 0.0, not NaN); `r_half = -0.4` at n = 66 gives `REJECT`
with reason `UNRELIABLE`, and `r_half = -1/3` the same; `match_set_of_game` equals the house
expression on a shuffled frame; centring removes a planted position effect and leaves a
planted player effect; `half_low` on hand numbers with g = 3 and the house interval on the
same; `half_low <= house_low` on a grid wherever both exist; a within-position near-copy of a
battery column is caught by the centred correlation while its raw correlation is below the
ceiling; a pure position effect is caught by the raw correlation; the nuisance R-squared takes
the larger centring; each departure of preregistration 6.1 shown in its stated direction on a
planted frame, each lenient one listed in `departures_active`; a constant vector, a match-set
vector with 0.5001 zeros (and not with 0.50) and an all-NaN battery give `INCONCLUSIVE` naming
the vector, never `SHIP`; goalkeepers and `player_id` 0 absent from every set; gate counts
computed before any value (a spy on `evaluate_candidate` shows zero calls when gates fail);
row-order invariance of the whole league evaluation, including a planted tie at the twelfth
place giving `top_k_kept` None with the tied counts; every returned field `None` rather than
NaN.

## 7. Runner, results, hashes

`experiments/run_candidate_gauntlet.py` (WP-E). Paths anchored to
`ROOT = Path(__file__).resolve().parents[1]`. Reads Parquet with a column list through
`load_public`, one league at a time for the gauntlet; the five shot frames are held together
(about 40,000 rows).

```python
def load_config() -> dict
def load_league(league: str, config: Mapping) -> LeagueFrames
def frame_digest(frame: pd.DataFrame, *, sort_by: Sequence[str], columns: Sequence[str]) -> str
def preflight(config: Mapping) -> dict                                     # structure only; no protocol check
def verify(config: Mapping, *, protocol_commit: str) -> dict               # phases 1 and 2: the provenance block
def run_selfcheck(config: Mapping, *, rule: Rule, correlation: Correlation) -> dict   # phase 3: the "selfcheck" block
def evaluate(frames: Mapping[str, LeagueFrames], config: Mapping, *, rule: Rule,
             correlation: Correlation) -> dict                             # phases 4 to 6, no provenance
def serialise(result: Mapping, out: Path) -> str                           # phase 7: checks, write, sha256
def guarded(step: Callable[[Phase], str], *, config: Mapping, log: Path) -> int   # the failed-execution rule around step
def run(config: Mapping, *, protocol_commit: str, out: Path) -> int        # phase 1 refusals; then guarded(phases 2 to 7)
def render_model_card(results: Mapping) -> str
def main(argv: Sequence[str] | None = None) -> int
```

`run_selfcheck` lives here, not in `candidate_synthetic.py`: it runs the pipeline (the specs,
`shot_frame`, `leave_one_league_out`, `select_instrument`, `instrument_report`,
`instrument_verdict`, `shot_values`, `run_gauntlet`, `candidate_verdict`) on the generators'
planted data, and reads the league assertions off `LeagueEvaluation` and `GateCount`. The
seam for tests is `evaluate` and `serialise`: a runner test builds a synthetic corpus, calls
`evaluate` with the imported `decide` and `_safe_abs_corr`, joins a synthetic provenance and
selfcheck block it states itself, and calls `serialise` into `tmp_path`. The seam for the
failed-execution rule below is `guarded`: `step` runs phases 2 to 7 and records in the mutable
`Phase` it is given the phase it has reached; `guarded` returns 0 and prints the sha256 when
`step` returns, and on an exception or a phase-7 refusal appends the record, removes every
file `step` wrote and returns 3. It is tested directly, with synthetic steps that raise in
phase 5 and that end in a phase-7 refusal. `verify` and `run` are tested only for their
refusals. The config a test passes is read from the frozen file;
the only key a test may override is `selfcheck_replicates`, and only in a call of
`run_selfcheck` (`selfcheck_smoke_rule`).

Phases of `run`, in order. Nothing in phases 1 to 4 reads an outcome, and nothing is printed
except progress on stderr and, at the end, the sha256 of the file written.

| # | Phase | Stops the run with nothing written if |
|---|---|---|
| 1 | provenance | `lf_sha256_text(inspect.getsource(decide))` differs from `frozen_rule_decide_source_sha256`, a constant of `frozen_rule_constants` differs from the module's, or `lf_sha256_text(inspect.getsource(_safe_abs_corr))` differs from `frozen_correlation_source_sha256`; `lf_sha256(PIPELINE.md)` differs from `pipeline_spec_sha256`; any candidate fingerprint differs from config; `git` is unavailable (fail closed); `<sha>` (`--protocol-commit`) is not an ancestor of `HEAD`, or for any of the three protocol files under `committed_experiment_dir` `<sha>` is not the last line of `git log --diff-filter=A --format=%H -- <path>`, `git log <sha>..HEAD -- <path>` is not empty, or the working file's LF hash differs from that of `git show <sha>:<path>`; the self-check stamp `committed_experiment_dir/selfcheck.json` is not tracked at `HEAD`, its working LF hash differs from that of `git show HEAD:<path>`, its `passed` is not true, or its `config_hash`, `pipeline_hash` or `source_hashes` differ from the current ones (`selfcheck_stamp_rule`); `failed_run_log` exists under `run_output_root` and the committed `analysis.md` at `HEAD` does not contain the sha256 of its bytes; the output file already exists (a determinism re-run writes `<run_output_root>/<determinism_rerun_file>`, which must not exist either). The LF hash of `frozen_rule_path` is recorded in provenance and does not stop the run (`frozen_rule_file_hash_role`) |
| 2 | structural pins | any `expected_*` of config differs or is null; `structure_identity` fails in a league; the period filter drops a row; a shot has no body part; a shot-family disagreement (`shot_family_pins`); the sidecar of I1 fails |
| 3 | self-check | `run_selfcheck` with the imported `decide` and `_safe_abs_corr` does not meet `selfcheck_predicate`, or its block differs from the stamp's `selfcheck` block |
| 4 | count gates | never stops; gates are recorded |
| 5 | instrument | — |
| 6 | candidates | — |
| 7 | write | checks on the whole in-memory object, before any byte is written: the serialised artifact exceeds `results_maximum_bytes`; a key at any depth is in `results_identifier_key_denylist`, is refused by `banned_key_paths(..., parts=BANNED_KEY_PARTS)`, contains `statsbomb`, `pappalardo` or `wyscout` in any letter case, or starts with `SB_`; `json.dumps(..., allow_nan=False)` raises. The walk covers `provenance.config` with no exemption, which is why no config key is `id`, `name` or holds one of the eight parts |

Written as `Path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")`. Never stdout redirection.

**A failed execution.** Any exception after the refusal checks of phase 1, and a refusal in
phase 7, append one record to `<run_output_root>/<failed_run_log>` (gitignored by
`data/public/*`; the location is ROOT 2.10 W7's): the
exception type or the refusal's check name, the phase, the file and line of the innermost
frame in the E-09 source files, and `source_hashes`; never the exception message, which can
hold a count or a value. The runner exits 3; every file the execution wrote is removed. No
value from a failed execution is printed, logged or read. The repair touches only the
failing phase's code; the changed files are reviewed again under section 9 and the self-check
stamp is regenerated and committed (its `source_hashes` change). Before the next start the
committed `analysis.md` at `HEAD` holds the sha256 of the log's bytes (phase 1 refuses
otherwise), so every failure is on the record and disclosed. A gate that fails is a verdict,
not a failure. R5 allows one real run and one determinism re-run; a failed execution counts
against neither, and the disclosure says what phase it reached.

### 7.1 `results.json` shape (aggregate only)

```
{
  "experiment": "E-09", "version": "player-candidates-v2", "tier": "PUBLIC",
  "verdicts": {"<subject>": {"token": "...", "rule_row": n | null, "reason": null | "<a code of verdict_reason_codes>"}},
  "provenance": {
    "experiment": "E-09", "protocol_commit": "...", "protocol_hash": "...", "config_hash": "...",
    "pipeline_hash": "...", "providers": ["pappalardo"],
    "source_hash_policy": "sha256 of LF-normalised bytes",
    "source_hashes": [{"path": "<posix path>", "lf_sha256": "..."}, ...],
    "frozen_rule": {"path": "...", "function": "decide", "source_sha256": "...", "constants": {...},
                    "file_lf_sha256": "...", "correlation_function": "_safe_abs_corr",
                    "correlation_source_sha256": "..."},
    "selfcheck_hash": "...",
    "candidate_fingerprints": {"shot_volume": "1c6517c2be31", ...},
    "frame_hashes": {"<league>": {"actions": "...", "lineups": "...", "players": "...", "sidecar_events": "..."}},
    "sidecar": {"<league>": { ...sidecar.provenance(league)... }},
    "raw_manifest_sha256": "...", "raw_file_sha256": {"events.zip": "...", "matches.zip": "...", "players.json": "..."},
    "packages": {"python": "...", "numpy": "...", "pandas": "...", "pyarrow": "...", "blas": "...",
                 "machine": "..."},
    "data_license": "...", "reuse_disclosure": "...", "config": { ...verbatim... }
  },
  "selfcheck": {"passed": true, "replicates": 12,
                "worlds": {"EFFECT": {"<subject>": {"<token>": count}}, ...},
                "league_assertions": {"NULL": {...}, "NUISANCE": {...}},
                "generator_sanity": {...},
                "instrument_scenarios": {"PLANTED": {"<token>": count}, ...,
                                         "TOO_SHARP": {"<token>": count, "with_R5_failed": count},
                                         "SLOPE_SHIFT": {"<token>": count, "with_R3_failed": count}}},
  "structure": {"<league>": {"matches", "shot_rows", "in_domain_shot_rows", "behind_halfway_shot_rows",
                             "sentinel_start_shot_rows", "goal_rows_on_shots", "eligible_players",
                             "eligible_by_position": {...}, "union_rows", "union_rows_unattributed",
                             "shot_rows_without_regulation_minutes",
                             "union_rows_without_regulation_minutes"}},
  "instrument": {
    "sample_gate": {"s_count_passed", "reasons", "folds": {"<held-out league>": {"train_shots",
                    "train_goals", "heldout_shots", "heldout_goals", "training_rate", "converged": {...}}}},
    "fits": {"<held-out league>": {"<model>": {"terms": [...], "coefficients": [...],
             "standard_errors": [...], "converged", "iterations", "log_likelihood"}}},
    "selection": {"instrument", "specification", "pooled_gain", "fold_gains": {...}, "folds_meeting",
                  "challenger_converged"},
    "leagues": {"<held-out league>": {"<model>": {"brier", "log_loss", "brier_skill", "log_loss_skill",
                "observed_over_expected", "calibration_slope", "calibration_intercept", "ece", "mce",
                "auroc"}, "brier_skill_interval": [lo, hi], "calibration_bins": [{"n",
                "mean_probability", "observed_rate"}], "null_calibration_error": {...}}},
    "pooled": {"<model>": {...same metrics...}, "brier_skill_interval": [lo, hi],
               "log_loss_gain_over_comparator": x, "log_loss_gain_interval": [lo, hi],
               "subgroups": {"<name>": {"n", "goals", "observed_over_expected"}},
               "descriptive_subgroups": {"counter_attack": {...}}},
    "gates": {"S_count": {"passed", "detail"}, "S_fit": {"passed", "models", "detail"}, "R1": ..., "R5": ..., "L1": ..., "L3": ...},
    "token": "...", "reason": null | "S_COUNT" | "S_FIT", "failed_gates": [...]
  },
  "candidates": {
    "<candidate>": {
      "definition": "...", "fingerprint": "...", "evidence_class": "...",
      "leagues": {"<league>": { ...every LeagueEvaluation field, GateCount nested... }},
      "token": "...", "rule_row": n,
      "evaluable": n, "surviving": n, "ship": n, "rejected": n,
      "context_limits": [...], "house_replication_label": "..."
    }
  },
  "registry_effect": {"<subject>": {"registry_move": "...",
                                     "registry_list": "REJECTED" | "RESEARCH_ONLY" | "TESTED_NOT_PROMOTED" | "UNTESTED" | null,
                                     "player_lab_headline": "..." | null}},
  "predictions": {"<subject>": {"token": "...", "reason": "...", "matched": bool}},   # config predictions
  "interpretation_limits": "..."                                                     # config interpretation_limits, verbatim
}
```

Rules: no player, team or match identifier anywhere (the only ids are league names); no key
at any depth, `provenance.config` included and exempted from nothing, in
`results_identifier_key_denylist`, refused by `banned_key_paths(..., parts=BANNED_KEY_PARTS)`
(no key named `rank`, `ranking`, `score`, `total`, `index` and the like, and no key with one of
the eight parts), or naming a provider (section 0); a missing value is
`null`; counts are ints; under `results_maximum_bytes` and the 512 KB of
`scripts/check_licensing.py` (expected about 250 KB: the verbatim config echo alone is about
68 KB at indent 2). The top-level `experiment`, `tier` and `verdicts` are the contract
`tests/test_verdict_registry.py` reads. In `selfcheck.instrument_scenarios`, a scenario that
names a `failing_gate` also records `with_<gate>_failed`: the number of replicates whose token
is in `expected` and whose failed gates include that gate, the count `selfcheck_predicate`
compares with `minimum_replicates_matching`. In `structure`,
`shot_rows_without_regulation_minutes` and `union_rows_without_regulation_minutes` count the
shot rows and the `opp_half_defensive_actions` union rows of eligible players in player-matches
whose capped minutes are 0 (a substitute who came on at or after the 90th minute): E-09's
season sums keep them, where E-11's `player_match` unit drops them (preregistration 3).

### 7.2 Hash discipline

| Hash | Of | How |
|---|---|---|
| `protocol_hash`, `config_hash`, `pipeline_hash` | the three registered files | `lf_sha256(path)` |
| `source_hashes` | `experiments/run_candidate_gauntlet.py`, `experiments/run_replication.py`, `galactico/features/{candidates,spec,axes}.py`, `galactico/models/shots/*.py` (the glob expanded and sorted), `galactico/validation/{candidate_gauntlet,shot_model_evaluation,candidate_synthetic,candidate_sb,sb_reader,provider_inputs,lifecycle,replication,digests}.py` (`provider_inputs.py` is E-11's registered module that the tie test of section 3 imports, ROOT 2.10 W3), `galactico/reliability/{core,confound}.py`, `galactico/ingestion/sidecar.py`, `galactico/providers/pappalardo.py` (it sets type, subtype, the flags and the coordinates of every neutral column read), `galactico/providers/base.py` (`assert_may_host`), `galactico/storage/public.py`, `galactico/domain/thesis.py` (phase 7 gates on it), `galactico/domain/provenance.py` (`EvidenceClass`) | a list of `{"path": <posix path relative to the root>, "lf_sha256": <hex>}` objects, one per file, sorted by `path`, so `sort_keys` leaves it byte-stable and no key names a provider (section 0); the self-check stamp and the LOCAL file of the external leg carry the same list |
| `frozen_rule` | `decide`, `_safe_abs_corr` and their module | `source_sha256` = `lf_sha256_text(inspect.getsource(decide))` and `correlation_source_sha256` = `lf_sha256_text(inspect.getsource(_safe_abs_corr))` (both gating, phase 1); `file_lf_sha256` = `lf_sha256(frozen_rule_path)` (recorded only) |
| `selfcheck_hash` | `committed_experiment_dir/selfcheck.json` | `lf_sha256`; phase 1 has tied the stamp to the current hashes |
| `frame_hashes` | the frames actually used | `frame_digest`: select the listed columns in the listed order, cast `success` to nullable boolean and ids to int64, sort by the key (`event_id`; lineups by `game_id, player_id`; players by `player_id`), `reset_index(drop=True)`, `sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes())`. Parquet file bytes are **not** hashed: the footer embeds the pandas version |
| `sidecar` | each league's sidecar | `sidecar.provenance(league)` verbatim (schema and tag-mapping versions, content hashes, raw digests) |
| `raw_manifest_sha256`, `raw_file_sha256` | `data/public/pappalardo/MANIFEST.json` | `lf_sha256` of the manifest; plus the `sha256` of the manifest's `files` entries named in `raw_manifest_entries` (`events.zip`, `matches.zip`, `players.json`: the manifest is keyed by downloaded asset, not by league), echoed verbatim |
| `packages` | the interpreter | Python, numpy, pandas and pyarrow versions; the BLAS library and version numpy reports; `platform.platform()` and `platform.processor()` as `machine`. The determinism re-run must be byte-identical on the same machine |
| `protocol_commit` | git | verified in phase 1; never a literal in source; the commit that first added the three protocol files, as `VerdictRecord.protocol_commit` defines it for `preregistration.md` |
| results | `results.json` | root records `lf_sha256` of it in the five records |

### 7.3 The commands

Preflight, any number of times after the pipeline commit, which adds the runner after
registration (section 13), so the root's structure counts before registration use their own
committed script. Structure and synthetic only; it prints the gate counts, the structural
pins and the self-check table, and writes nothing in the repository:

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --preflight

The self-check stamp, after the pipeline commit and the review of section 9 (synthetic only;
writes `selfcheck.json` with `passed`, `config_hash`, `pipeline_hash`, `source_hashes` and the
`selfcheck` block, refuses to overwrite; the root commits it unchanged in a commit of its own):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --selfcheck --out experiments/preregistered/E-09-player-candidates/selfcheck.json

**The single command the root runs for the real execution, once:**

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --out experiments/preregistered/E-09-player-candidates/results.json

Determinism re-run, once (writes `<run_output_root>/<determinism_rerun_file>` and compares
its bytes with `experiments/preregistered/E-09-player-candidates/results.json`; exit code 1
unless byte-identical, and the re-run file is then kept for the record, never committed):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --protocol-commit <sha> --determinism-rerun

Model card, generated from the committed results, never typed (writes
`experiments/preregistered/E-09-player-candidates/MODEL-CARD.md` beside them; refuses to
overwrite):

    .venv/Scripts/python.exe -B experiments/run_candidate_gauntlet.py --render-card experiments/preregistered/E-09-player-candidates/results.json

## 8. Synthetic suite and the planted checks

`galactico/validation/candidate_synthetic.py` holds the generators only. **Independent of
what it checks**: it imports numpy and pandas only, plus `LeagueFrames` as a container. It
writes its own geometry from the formulas in the protocol and builds neutral-schema rows
directly, with `body_part` and `shot_family` columns as the sidecar would attach them. An
`ast` test, written as `tests/test_research_firewall.py` writes its scan (`ast.walk` over the
whole tree, function bodies included, plus `import_module` and `__import__` called with a
string), asserts it imports nothing from `features.candidates`, `models.shots`,
`shot_model_evaluation` or `candidate_gauntlet` other than `LeagueFrames`. The self-check
itself, which runs the pipeline on these data, is `run_selfcheck` in the runner (section 7).

```python
def synthetic_league(world: Mapping, *, world_position: int, league_position: int,
                     replicate: int, config: Mapping) -> LeagueFrames
def synthetic_corpus(world: Mapping, *, world_position: int, replicate: int,
                     config: Mapping) -> dict[str, LeagueFrames]
def synthetic_shots(scenario: Mapping, *, scenario_position: int, replicate: int,
                    config: Mapping) -> dict[str, pd.DataFrame]
def generator_sanity(config: Mapping) -> dict                  # latent parameters and own geometry only
```

Seeds: `selfcheck_seed_rule` (worlds and scenarios on separate streams; resampling inside the
self-check as in the real run), positions 0-based (`position_indexing`). Worlds are read from
`synthetic_worlds` by their `world` key and scenarios from `synthetic_instrument_scenarios` by
their `scenario` key; no entry has a `name` key.

### 8.1 Generator (per league; parameters are the `synthetic_*` keys)

| Step | Rule |
|---|---|
| squad | `synthetic_teams` teams; per team `synthetic_position_counts` outfield players and `synthetic_goalkeepers_per_team` goalkeeper; the last DF and the last MD are fringe players (`synthetic_fringe_positions`) |
| fixtures | double round-robin by the circle method, `synthetic_rounds` rounds, 380 matches; `game_id` increases with the round |
| appearances | a regular plays a match with probability `synthetic_regular_appearance_probability`, a fringe player with `synthetic_fringe_appearance_probability`; 90 minutes when he plays; the goalkeeper always plays |
| passes | `synthetic_passes_per_player_match` per player-match; `type "pass"`, start and end uniform on the unit square, rounded to `synthetic_coordinate_decimals`; `success` true with probability `synthetic_pass_success_probability` |
| shots | per player-match Poisson(rate); rate = position mean x `exp(N(-s^2/2, s))` with `s` = `shot_rate_log_sd`, a lognormal multiplier of unit mean (so the position mean is the mean rate), drawn once per player; distance ~ Gamma(shape `synthetic_distance_gamma_shape`, scale s/shape) x (`synthetic_head_or_body_distance_factor` if head-or-body), clipped to `synthetic_distance_clip_m`, with s the player's distance scale (`distance_scale_m`); lateral offset = min(abs(Normal(0, `synthetic_lateral_sd_m`)), distance), on the attacker's left with probability `synthetic_lateral_left_probability`; head-or-body with probability `synthetic_head_or_body_probability`; (distance, offset) to (`start_x`, `start_y`) by `synthetic_shot_coordinate_rule` (X = sqrt(d^2 - c^2), `start_x = 1 - X / 105`, `start_y = 0.5 -/+ c / 68`, left at the smaller y), coordinates rounded to `synthetic_coordinate_decimals`; goal ~ Bernoulli(logistic(`synthetic_truth_coefficients` . features of the rounded coordinates)); `shot_family` `open_play` |
| ground defending duels | opponent-half and own-half counts per player-match are independent Poissons with the player's two rates: position mean x `exp(N(-s^2/2, s))` with `s` = `opp_half_duel_rate_log_sd` and `own_half_duel_rate_log_sd`, or, where `shared_duel_rate_log_sd` is set, one shared multiplier `exp(N(-s^2/2, s))` with that `s` on both (every lognormal multiplier of this generator has unit mean); `start_x` uniform on the integer percents of `synthetic_duel_start_x_percent`; `start_y` uniform on the unit square, rounded; each record's `player_id` set to 0 with the team's unattributed probability (linear from `low` to `high` across teams) |
| interceptions | per player-match Poisson(`interception_ratio` x duel rate) in each half region; a `touch` row with `interception` true; never unattributed |
| goalkeeper | pass rows only |
| planted traps in every league | one penalty and one direct free-kick shot per team (`type "set_piece"`, `shot_family` `penalty` / `free_kick`), two shots with `start_x <= 0.50`, one duel row and one shot row at the (1,1) sentinel and one shot row at (0,0), one shot by `player_id` 0 |

### 8.2 Planted worlds (candidates; five synthetic leagues each)

| World | What is planted | Must be classified (config `expected`, `never`) |
|---|---|---|
| `EFFECT` | within-position spread in shot rate, player-specific shot distance scale independent of rate, within-position spread in both duel rates, flat unattributed share | instrument `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`; all four candidates `ESTABLISHED_NUMBER` or `ESTABLISHED_BAND` |
| `NULL` | no within-position spread in anything; strong position means; one distance scale | every candidate `NOT_ESTABLISHED_*` (`shot_location_value` `NOT_ESTABLISHED_REDUNDANT`); never `ESTABLISHED_*`. League assertions (`league_assertions`): the raw pooled reliability of `shot_volume` above 0.70 and its centred bound below the band in every replicate league, which documents why the gate is position-centred |
| `NUISANCE` | one opponent-half duel rate for everyone; own-half rate widely spread; team-level unattributed probability across a range that keeps the league's union share at or below `maximum_unattributed_share` | `opp_half_defensive_actions` `NOT_ESTABLISHED_CONFOUNDED`; never `ESTABLISHED_*` or `INCONCLUSIVE`. League assertion: union share at most the gate in every replicate league |
| `REDUNDANT_WITHIN_POSITION` | as `EFFECT`, but one shared multiplier on a player's two duel rates, so within a position the candidate is a fixed share of all his defensive activity | `opp_half_defensive_actions` `NOT_ESTABLISHED_REDUNDANT`; never `ESTABLISHED_*` |

Generator sanity assertions (about the data, not the pipeline; `synthetic_generator_sanity`
and `generator_sanity_rules`): in `EFFECT` the population correlation between a player's
latent shot rate and his latent value rate is below its bound; in `NUISANCE` the latent
share of the opponent-half value's variance carried by team attribution is above its bound.

### 8.3 Planted instrument scenarios (five leagues x `synthetic_instrument_shots_per_league`)

Distance scale `synthetic_instrument_distance_scale_m` for every shot; match ids by
`synthetic_instrument_match_rule`; otherwise the shot rule of 8.1, coordinates by
`synthetic_shot_coordinate_rule`. The median of `TOO_SHARP` and `SLOPE_SHIFT` is taken over
the league's own synthetic shots after rounding (`synthetic_logit_median_rule`); the
scenario frames' columns are `synthetic_instrument_frame_rule`; `league_position` 2 is the
0-based index into `leagues`, Italy (`position_indexing`).

| Scenario | What is planted | Must be classified |
|---|---|---|
| `PLANTED` | every league follows the truth coefficients | `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`, and `ACCEPTED` alone in at least the `also` count; never `INCONCLUSIVE` |
| `NO_SIGNAL` | goal probability `goal_rate` for every shot | `NOT_ESTABLISHED` |
| `TOO_SHARP` | logit multiplied by `logit_multiplier` around its median, shifted by `logit_shift` | `NOT_ESTABLISHED`, with R5 among the failed gates |
| `LEVEL_SHIFT` | one league's odds multiplied by `odds_multiplier` | `ACCEPTED_WITHIN_LEAGUE`; never `ACCEPTED` |
| `SLOPE_SHIFT` | one league's logit, centred on its median, multiplied by `logit_slope_multiplier` | `NOT_ESTABLISHED`, with R3 among the failed gates |

**Feasibility, checked at event level before this revision was written.** The reviser
implemented this generator, the gauntlet of preregistration 6, the decision rule of 9 and
the instrument gates of 4 (with the bootstrap) in a throwaway script on synthetic numbers
only, and ran each world and scenario for 40 replicates. The counts are in
`selfcheck_feasibility`; every predicate held with the margins recorded there. The audit
revision set the `minimum_replicates_matching` values (9 of 12, and 8 of 12 for `PLANTED`'s
`also`) so that the seventeen minimum conditions hold together with 0.9941 at the
conservative miss rate (observed misses + 1) / 40, against 0.9296 for the earlier 10, 10 and
9 (`joint_minimum_pass_probability`); a broken pipeline gives the opposite token in most
replicates and still fails them, and every never list is unchanged. The script is a working
note, not kept; the pipeline's own self-check is the check that binds.

**What may be adjusted, and until when.** The binding self-check first runs after
registration, when the pipeline exists, so the window below applies only to the reviser's
own simulation before the protocol commit: there `synthetic_*` parameters may be edited if a
stated rate is not met, with the reason recorded in the review record. Thresholds, gates,
the decision rule and the rates themselves may not be edited to make a check pass. After the
protocol commit nothing in `config.json` changes; a self-check that fails after registration
stops the run, and the protocol is superseded by a new experiment id (ADR-0029, Reversal).

### 8.4 Test files

| File | Content | Marker |
|---|---|---|
| `tests/test_candidate_planted.py` | 8.2 and 8.3 at `selfcheck_replicates`, through the runner's `run_selfcheck` with the imported `decide` and `_safe_abs_corr`; the league assertions; the generator sanity assertions; the independence `ast` test on `candidate_synthetic.py`; the planted traps never credited | `slow` for the full replicate count; the 2-replicate deterministic smoke variant always runs and asserts `selfcheck_smoke_rule` (every never list holds, each world and scenario gives an expected token in at least one replicate per subject, two runs byte-identical) |
| `tests/test_candidate_runner.py` | phase order (a spy shows no value computed before phase 4 ends); each phase-1 and phase-2 stop, including a changed `decide` source, a changed `_safe_abs_corr` source, a changed constant, a changed `PIPELINE.md`, a null pin, a broken `structure_identity`, a stamp that is missing, untracked, not passed or holds an old hash, and a failure log not disclosed in `analysis.md`; refusal to overwrite; through `guarded` with synthetic steps, a raised exception in phase 5 and a phase-7 refusal each append one record without the message, remove every written file and return 3; a synthetic corpus whose `M1` has a singular information matrix in one fold goes through `evaluate` and `serialise` to an instrument `INCONCLUSIVE` with reason `S_FIT`, with no NaN in the file; determinism (two `evaluate` and `serialise` runs on a synthetic corpus byte-identical); `results.json` schema, size, `allow_nan`; on a `results.json` built by `serialise` from the frozen config (with `provenance.config` the verbatim echo): the denylist walk, `banned_key_paths(..., parts=BANNED_KEY_PARTS)` and the three-name walk at every depth each find nothing, and each finds a planted `id`, `rank_ties` or `wyscout_x` key placed outside and inside the echo; `galactico/providers/pappalardo.py` appears as a `path` value of `source_hashes` with its true `lf_sha256`, the list sorted by `path` with one entry per file of 7.2; config read from the frozen file and only `selfcheck_replicates` overridden; every threshold in code traced to a config key (source scan of `shot_model_evaluation.py`, `candidate_gauntlet.py` and the runner for the literals 0.85, 0.70, 0.60, 0.82 finds none outside docstrings); a synthetic tree built from a runner `results.json` with the five records of section 11.1 passes every checker of `tests/test_verdict_registry.py` | — |
| `tests/test_candidate_pins.py` | on the real corpus, **structure only**: the `expected_*` pins, `structure_identity`, period filter, body-part coverage, clause overlap, shot-family pins, fingerprints; skips per league through `league_available` and when the league's sidecar manifest is absent | `slow`; skips without data |

No test computes a candidate statistic or a model fit on real rows.

## 9. Pre-outcome code-review checklist

Signed off by a reviewer who did not write the package, after the pipeline commit and before
the self-check stamp and the run.

1. `git status` shows no `results.json` under the E-09 folder and no cached real-data output of this pipeline anywhere.
2. No agent report lists a real-data execution beyond `--preflight` and `tests/test_candidate_pins.py`.
3. Fingerprints computed by the code equal `config.json` (four of four); `candidates.py` opens no file, names no experiment path, and its constants equal `config.json` (`tests/test_candidates.py`, the config tie and the no-file scan).
4. `lf_sha256_text(inspect.getsource(decide))` equals `frozen_rule_decide_source_sha256` and the constants equal `frozen_rule_constants`; `_safe_abs_corr`'s source hash equals `frozen_correlation_source_sha256`; both are imported and injected (`rule`, `correlation`), not copied, and no library module imports `experiments`; no threshold literal in WP-C, D, E code.
5. `candidate_gauntlet.py`, `shot_model_evaluation.py`, `candidate_synthetic.py`, `candidate_sb.py` are in the firewall tuple; nothing under `galactico/api`, `galactico/optimization`, `galactico/profiles`, `galactico/match_lab` imports them; `galactico/models/shots` imports nothing from `galactico/validation` or `experiments`.
6. `spec.SPECS` has five keys; `CONSTRUCTS` has five; the shipped fingerprints are unchanged; the full suite is green without the corpus.
7. The model sees only `distance_m`, `angle_rad`, `head_or_body`: `design_matrix` reads no other column; the strings `opportunity`, `success`, `blocked`, `zone` do not occur in `galactico/models/shots/`.
8. Leave-one-league-out leakage test present and passing; the reference rate is the training rate.
9. No goals-minus-model quantity anywhere (`grep` for a subtraction of a value sum from a goal count in WP files).
10. The share floor, match-set floor, minutes floor and goalkeeper exclusion are applied before any value is computed; gate counts precede statistics (spy test).
11. Every departure of preregistration 6.1 has its named test and its direction; lenient ones are listed in `departures_active`.
12. Self-check passes from a clean checkout, and `--preflight` on the real corpus prints all pins matching and the count gates (planning values: eligible 319 / 306 / 306 / 270 / 306 on nominal minutes, which capped minutes can only lower; share sets about 80 / 84 / 88 / 66 / 80).
13. `results.json` writer: UTF-8, LF, `allow_nan=False`, sorted keys, size check, denylist, banned-key (with `BANNED_KEY_PARTS`) and provider-name walks over the whole object, `provenance.config` included, no identifiers, `source_hashes` a sorted list of path and hash pairs, the registry contract at the top level.
14. Phase 1 refuses a wrong commit, a commit that is not an ancestor of `HEAD`, a protocol file not first added in it, a dirty protocol, a changed `PIPELINE.md`, a changed `decide` or `_safe_abs_corr`, a missing or stale self-check stamp, an undisclosed failure log, an existing output.
15. Protocol, config, this file and the code agree on every name in section 7.1; preregistration 9.1 has eight rows and the code has eight branches.
16. Ruff clean; `from __future__ import annotations`; frozen dataclasses; `__all__`; docstrings state claim and non-claim.
17. The committed self-check stamp `selfcheck.json` matches the reviewed source hashes, the config hash and the pipeline hash; it was written by `--selfcheck` after this review, not before.
18. External leg: `candidate_sb.py` was built in the pipeline commit, before any public outcome, with every frame rule of section 10 frozen in config; `lf_sha256(sb_reader.py)` equals its entry in E-11's `acceptance.json`; no StatsBomb-derived number, coefficient or identifier is in a committed file; `sb_output_root` and `sb_root` resolve under `data/licensed/`; `candidate_sb.py` passes `check_licensing.check`.

## 10. External leg (WP-F, LOCAL; built with the pipeline, run conditionally)

`galactico/validation/candidate_sb.py` is written, reviewed and pinned in the pipeline commit
with every other source file (section 13), because `tests/test_research_firewall.py` requires
a listed module to exist and because every frame rule below must be fixed before any public
outcome is known; its path and `sb_reader.py`'s are in the `source_hashes` of section 7.2. It
runs through `experiments/run_candidate_gauntlet.py --external --protocol-commit <sha>`, only
after `results.json` is committed and only for candidates of `sb_leg_candidates` at
`ESTABLISHED_*`. LOCAL_LICENSED end to end (`sb_leg_tier`): nothing under `galactico/api`,
`galactico/optimization`, `galactico/profiles`, `galactico/match_lab`, `galactico/models` or
`galactico/features` imports it, and it imports nothing from `experiments`.

```python
def sb_frames(folder: str, config: Mapping, *, e11_config: Mapping) -> LeagueFrames   # the neutral frame below
def sb_shot_detail(folder: str, game_ids: Collection[int], config: Mapping) -> pd.DataFrame
    # event_id (str), shot_type, body_part, read from sb_reader.iter_events; keys reached through variables
def sb_box_spec(config: Mapping) -> CandidateSpec                          # config sb_box_spec; never in CANDIDATES
def sb_leg_config(config: Mapping) -> dict                                 # the leg's view of the config, sb_leg_config_rule
def sb_verdict(candidate: str, evaluations: Sequence[LeagueEvaluation],
               refit_token: str | None, config: Mapping) -> tuple[int, str]   # (row of preregistration 11, token)
def sb_level_shift(public: Mapping[str, float | None], local: Mapping[str, float | None],
                   config: Mapping) -> float | None
def run_external(results: Mapping, config: Mapping, *, e11_config: Mapping, rule: Rule,
                 correlation: Correlation) -> dict
```

| Rule | Detail |
|---|---|
| inputs | `sb_root` only; no path under `sb_forbidden_roots` is opened. Before anything is read, `sb_reader.folder_manifest` of each of `sb_folders` equals `sb_folder_digests` (the three null digests are counted by the root before registration) |
| readers | `galactico.validation.sb_reader` (E-11, registered) imported unchanged: `read_matches`, `read_events(scale=sb_location_scale)`, `read_team_sheets(..., cap=regulation_minutes_cap, regulation_periods=sb_regulation_periods, goalkeeper_position=sb_goalkeeper_position, dismissal_card_types_exclude=sb_dismissal_card_types_exclude, spell_end_reason_contains=sb_spell_end_reason_contains)`, whose `minutes_regulation` is `sb_minutes_rule`; the Wyscout `goalkeeper_position` is never passed, and `is_goalkeeper`, `dismissed` and `permanent_off` are not read. Body part and the position names of spells are read by `candidate_sb.py` from the raw lists `sb_reader.iter_events` and the lineup files yield; each spell's regulation minutes come from `sb_reader._spell`, imported as a private member (one rule, never a second implementation, ROOT 2.9 Z3), under the pin `sb_reader_pin_rule`. `sb_reader` is not extended, since its hash is in E-11's committed acceptance stamp and an edit before E-11's run would invalidate it |
| vocabulary | a shot type outside `sb_known_shot_types`, a body part outside the keys of `sb_body_part_map`, or a position name outside `sb_position_groups` stops the leg before any statistic |
| frames | rows by `sb_event_row_rule`; columns by `sb_frame_columns_rule`: `type` by `sb_kind_type_map` (Pass, Shot, Duel; Interception, Clearance, Miscontrol, Dispossessed and Block as `touch`; every other kind dropped), `success` on passes = not `has_outcome`, `goal` = shot outcome in `sb_goal_outcomes`, `counter_attack` = `play_pattern` in `sb_counter_attack_play_patterns`. The open-play shot that keeps a Shot row and the `interception` flag are not written again here: they are E-11's `open_play_shot` and `interception` flags, computed by `galactico.validation.provider_inputs._statsbomb_flags(rows, e11_config, "open_play")` on the `read_events` rows, imported as a private member as `_spell` is (one rule, never a second implementation, ROOT 2.9 Z3; `sb_flags_rule`), under the existing pins (`provider_inputs.py` in `source_hashes`; `e11_config` is E-11's registered config, whose `lf_sha256` equals `e11_config_sha256`). E-11's interception family (an Interception event, or a Pass of an interception type) matches the Wyscout tag that `opp_half_on_ball_rule` excludes on passes; the shipped `StatsBombProvider` mapping, which makes an Interception a duel, is not used; `sb_open_play_shot_types`, `sb_interception_kinds` and `sb_interception_pass_types` restate E-11's keys of the same names and are asserted equal to them; `subtype` null, `body_part` by `sb_body_part_map`, `shot_family` `open_play` on kept shots; ids renamed from `sb_game_id`, `sb_team_id`, `sb_player_id`; periods by `sb_period_labels`; positions by `sb_position_rule`, goalkeepers the GK group at season level; `event_id` kept as the provider's string and never cast to an integer (`frame_digest` hashes it as a string on this leg); `location_sentinels` apply through `Zone.mask` and the leg's sentinel-start shot rows are counted; a frame with no pass row is refused before any statistic (`sb_frame_refusal`) |
| battery | `sb_battery_rule`, on the frames above |
| box | the leg-only spec `sb_box_spec`: `box_shot_share`'s clauses with the zone `penalty_area_sb` (bounds inclusive, `zone_use`), fingerprint `23bf9214db9b`, sentence `sb_box_spec.sentence`; `CANDIDATES` keeps its four keys |
| leg config | every public function the leg calls receives `sb_leg_config(config)`, the leg's view of the config written out exactly in `sb_leg_config_rule`: `leagues` becomes `sb_folders`, so `league_position` is the 0-based index in `sb_folders` for `bootstrap_rule` and the null-ECE seed; `gate_s_count` becomes `sb_gate_s_count`; `gate_r1_leagues_required`, `gate_r3_leagues_required` and `gate_l_leagues_required` become `sb_gate_leagues_required`; `minimum_evaluable_leagues` becomes `sb_minimum_evaluable_leagues`; `context_limit_rule` and every pooled statistic count over the four folders; every other key is unchanged. No other substitution is made |
| instrument | the specification selected on the public run, refitted leave-one-league-out over the four folders through `sb_leg_config`, with `sb_gate_s_count`, S-fit on `gate_s_fit_models` and the instrument in every fold (`gate_s_fit_rule`: no reselection and no fallback to `M1`), the R and L gates in `sb_gate_leagues_required` of 4, the pooled gates at the public thresholds |
| gauntlet | the same functions with the injected `rule` and `correlation` (the runner passes `decide` and `_safe_abs_corr`), through `sb_leg_config`; `candidate_verdict`, the public rule of 9.1, is not called on the leg |
| token | preregistration section 11, rows in order; `sb_verdict` returns the row (1 to 5) and the token; `sb_verdict_vocabulary`; the sentence `sb_statements[token]` |
| level shift | `sb_level_shift_rule`: the public input is `LeagueEvaluation.mean` from the committed `results.json`, per league, null where the count gates failed; the local input the same on the leg; reported only |
| output | `sb_output_root/sb_results_file` (gitignored). **Never committed.** Keys: `experiment`, `version`, `tier` (`LOCAL_LICENSED`), `provenance` (`protocol_commit`, `protocol_hash`, `config_hash`, `pipeline_hash`, `source_hashes` as the list of 7.2, `sb_folder_digests` as checked, `public_results_sha256` = `lf_sha256` of the committed `results.json`, `packages`), `structure` per folder, `instrument` (the 7.1 instrument block's shape), `candidates` (per candidate the 7.1 candidate block's shape without `token` and `rule_row`, which only the public rule assigns, plus `sb_token`, `sb_rule_row` (1 to 5) and `sb_sentence`; its `evaluable`, `surviving`, `ship` and `rejected` are the counts the leg's rows read), `level_shift`. The key rules of section 0 and phase 7 apply to it. The research note `sb_report` carries aggregate findings in prose and tables with the StatsBomb logo and attribution; no coefficient table |
| refusals | in both modes, `--external` refuses, writing nothing, unless every phase-1 check of section 7 passes except the output check; `results.json` under `committed_experiment_dir` is tracked at `HEAD` with a working LF hash equal to that of `git show HEAD:<path>`; at least one candidate of `sb_leg_candidates` holds an `ESTABLISHED_*` token there; `sb_root` and `sb_output_root` resolve under `data/licensed/` and `PROVIDERS["statsbomb"].tier` is `LOCAL_LICENSED`; every `sb_folder_digests` value is non-null and equals its `folder_manifest`; `sb_reader_pin_rule` holds; `lf_sha256` of E-11's registered `config.json` equals `e11_config_sha256`; `sb_failed_run_log` exists only if `analysis.md` at `HEAD` holds the sha256 of its bytes. Per mode: under `--external`, `sb_results_file` does not exist; under `--external --determinism-rerun`, `sb_results_file` exists and `sb_determinism_rerun_file` does not |
| determinism | `--external --determinism-rerun` writes `<sb_output_root>/<sb_determinism_rerun_file>` and exits 1 unless it is byte-identical to `sb_results_file`; the re-run file is kept for the record and never committed |
| pin after registration | `sb_reader.py` is E-11's registered code, and E-11's failed-execution rule allows a repair of it with a re-stamped `acceptance.json`. A change to `sb_reader.py` after E-09's registration means the leg is not run and produces no label (`sb_reader_pin_rule` refuses it for good), and `analysis.md` says so; it is not a failed execution of E-09. `tests/test_candidate_sb.py` then asserts the refusal instead of the equality below |
| failed execution | the rule of section 7, with the log `sb_output_root/sb_failed_run_log` |
| registry | none: the leg writes no `VerdictRecord` and changes no registry (DISSENT 7, ROOT 2.9 Z5) |

`opp_half_defensive_actions` is not in this leg; its cross-provider status is E-11's token for
the same subject id.

`tests/test_candidate_sb.py` (synthetic only, invented names and ids): a hand-built synthetic
event list and lineup pair through `sb_frames` gives the exact neutral frame (types, the
dropped kinds and dropped non-open-play shots, `success`, `goal`, `counter_attack`, the
interception flag on an Interception event and on a Pass of an interception type,
`body_part`, `shot_family`, renamed ids, string `event_id`); a shots-only frame, and any frame
with no pass row, is refused; the box edges on the provider's lattice (x = 101.9/102.0, y =
17.9/18.0/62.0/62.1, divided by 120 and 80) through `Clause.mask` with the zone
`penalty_area_sb`, and `sb_box_spec`'s fingerprint and sentence; `read_team_sheets` is
called with the three `sb_` keys and never with the Wyscout goalkeeper code; the position
map, its tie rule and spell minutes from `sb_reader._spell`; the period map; an unknown shot
type, body part or position name stops the leg; with the selected `MFLEX` not converging in
one fold while `MD` and `M1` converge, the token is `INSTRUMENT_NOT_ACCEPTED` through row 1
before row 2, and no gauntlet value of `shot_location_value` is computed; `sb_leg_config`
differs from the config in exactly the keys `sb_leg_config_rule` names, and four synthetic
`PLANTED` folders through it give a refit of `ACCEPTED` or `ACCEPTED_WITHIN_LEAGUE`, after
which `shot_location_value` reaches leg rows 3 to 5, while one folder failing R1 gives
`INSTRUMENT_NOT_ACCEPTED`; a spy shows the kept shots and the `interception` flag come from
`provider_inputs._statsbomb_flags`, and `sb_open_play_shot_types`, `sb_interception_kinds` and
`sb_interception_pass_types` equal E-11's registered keys; every token row reached, row 1
before row 2, with `sb_verdict` returning the row; every refusal above, in both modes (the
plain leg refuses an existing `sb_results_file`, the re-run refuses a missing one or an
existing re-run file), and a committed `results.json` with no established leg candidate is
refused; the LOCAL file passes the key rules and its candidate block holds `sb_token` and
`sb_rule_row` and no `token` or `rule_row`; a string `event_id` survives hashing; the module
passes `check_licensing.check`; no product package imports it; `lf_sha256(sb_reader.py)`
equals the `galactico/validation/sb_reader.py` entry of `source_hashes` in E-11's
`acceptance.json` and `sb_reader_source_sha256_in_e11_acceptance` (a test against `HEAD`
alone would not fail once an edit is committed), or, where `sb_reader.py` was changed after
E-09's registration, `--external` refuses on `sb_reader_pin_rule` (the row above).

## 11. Registry consequences

### 11.1 At registration, and after the run

**At registration** (root, the registration commit; section 13): five PUBLIC records in
`galactico/domain/verdicts.py`, token `PENDING`: `experiment_id = registry_experiment_id`,
`tier = Tier.PUBLIC`, `directory = committed_experiment_dir`, `not_run_statement` from
`registry_common`; candidate records (`registry_candidate_subjects`) with `scope`,
`claim_token`, `non_claim` from `registry_candidate`, `vocabulary = verdict_vocabulary.candidate`,
`outcomes` from `registry_outcomes.candidate` (status, limits, statement, registry_move); the
instrument record (`registry_instrument_subjects`) likewise from `registry_instrument` and the
`instrument` entries; `protocol_hash`, `config_hash` = `lf_sha256` of the registered files. In
the same commit `product_admissible` gains an explicit, empty promotion set (ROOT 2.10 W1;
protocol section 10; section 13): a PUBLIC, executed, established E-09 record admits nothing
until a later promotion, which is its own change set with its own ADR (11.2).

**After the run** (root, the results commit):

| Token | Edit |
|---|---|
| any | each record takes `token` from `results.json` `verdicts`, `protocol_commit` and `results_hash`; remove `shot_profile` and `defensive_action_profile` from `UNTESTED` in `galactico/profiles/build.py` (line 111; one tuple, read by `galactico/api/player_lab.py` and `scripts/generate_docs.py`); write `TESTED_NOT_PROMOTED` (empty unless a candidate is established) and `DISPLAY_NAMES` there; regenerate the README and METRICS blocks; add the E-09 row state to `experiments/preregistered/README.md` |
| `INCONCLUSIVE`, `INCONCLUSIVE_INSTRUMENT` | add the candidate id to `UNTESTED` (`untested_edit`; a declared hand edit tied to the token by a test, not a `registry_move`) |
| `NOT_ESTABLISHED_REDUNDANT`, `_CONFOUNDED`, `_UNRELIABLE` | `REJECTED[id] = (headline, detail)` from `player_lab_text[token]`, the headline filled by `baseline_fill_rule` through `baseline_prose`, or through `nuisance_prose`; add `test_<id>_stays_rejected` asserting absence from `CONSTRUCTS` and `spec.SPECS` |
| `NOT_ESTABLISHED_MIXED` | `RESEARCH_ONLY[id] = (headline, detail)` from `player_lab_text[token]` |
| `ESTABLISHED_*` | no `registry_move` (rule V6 refuses one on an ESTABLISHED outcome, and V6 is not changed; ARCH D1); `TESTED_NOT_PROMOTED[id] = (headline, detail)` from `player_lab_text[token]` (`tested_not_promoted_edit`, a declared hand edit tied to the token by a test); `product_admissible` stays false through the explicit, empty promotion set of the registration commit (ROOT 2.10 W1) |
| every candidate in a list | `DISPLAY_NAMES[id]` = its config `display_name` (`display_name_edit`), a literal in product code that a test ties to the registered config's `display_name`; `/api/constructs` serves it as the label, and `_display_name` keeps the id rule for ids it does not hold |
| any E-09 record whose badge reads TESTED | `galactico/api/planning.py`: the sentence that replaces `REGISTERED_NOT_TESTED_STATEMENT` once `verdict_reading` returns `None` is `planning_after_run.research_sentence`, after any sentence written for another experiment (`research_sentence_rule`); the tests that assert `REGISTERED_NOT_TESTED_STATEMENT` change with it: `tests/test_planning_render.py`, `tests/test_squad_api.py`, `tests/test_transfer_api.py`, `tests/test_planning_api.py` |
| any | whatever the tokens, and whether or not any E-09 record reads TESTED, the `shots` entry of `NOT_MEASURED_EXTRA` becomes `planning_after_run.shots_entry_tested`, `shots_entry_instrument_only` or `shots_entry_untested` by `shots_entry_rule`; its tests change with it |
| instrument, any token | `MODEL-CARD.md` rendered |
| instrument `ACCEPTED`, `ACCEPTED_WITHIN_LEAGUE` | the `docs/LIVE-DATA-GAP-MATRIX.md` note of `gap_matrix_edit`: a location-only conversion model (PREDICTIVE) on the free corpus, never provider xG; the xG / xA row itself is not relabelled. Under `NOT_ESTABLISHED` and `INCONCLUSIVE` the matrix is not edited |

Counts after any outcome (`player_lab_counts_after_run`): proposed = 5 + |`REJECTED`| +
|`RESEARCH_ONLY`| + |`TESTED_NOT_PROMOTED`| + |`UNTESTED`| = 13; tested = 13 minus the ids in
`UNTESTED` (`carrying_value` and every inconclusive candidate); surviving = 5. A test over
all 4,096 assignments of the eight candidate tokens to the four candidates asserts these
counts, that each candidate is in exactly one of the four lists, and that the list is the one
`registry_lists_after_run` names for its token. These edits change served Player Lab and
planning output, and each consumer of the lists changes in the same commit:

| File | Change |
|---|---|
| `galactico/profiles/build.py` | `TESTED_NOT_PROMOTED`, `DISPLAY_NAMES`; `UNTESTED` and the two text registries as above |
| `galactico/api/player_lab.py` | serves `tested_not_promoted` (id, label, headline, detail) and `counts.tested_not_promoted`; adds the list to `proposed` and `tested`; `surviving` stays `len(shipped)`; labels from `DISPLAY_NAMES` |
| `scripts/generate_docs.py` | `counts()` adds the list to proposed and tested and gains a "tested, not promoted" clause; `rejected_table()` gains a "tested, not promoted" row type; README and METRICS regenerated |
| `web/index.html` | `renderWhy` gains a card type for the new list |
| `tests/test_registry_contract.py` | `test_a_construct_has_exactly_one_status` adds `TESTED_NOT_PROMOTED` to the pairwise-disjoint check and keeps it out of `assert all(...)`, since it may be empty; the digit-free test covers it, the copy-guard test covers it and `DISPLAY_NAMES`; the token-to-list test |
| `tests/test_served_credit.py`, `tests/test_docs_consistency.py` (`test_the_hero_states_the_documented_counts`), `tests/test_web_render.py` fixtures, `e2e/smoke.spec.js` constructs shape, `tests/test_player_lab.py` | the new key, the new clause and the counts |
| the planning tests named above | the research sentence and the `shots` entry |

R13 and ADR-0011 pin that output, and ROOT 2.2 authorises the placeholder replacement. ROOT
2.10 W8 makes the post-run product edits (the Player Lab lists `TESTED_NOT_PROMOTED` and
`DISPLAY_NAMES`, the frozen planning sentences, the gap-matrix note) the results commit's
consequences, overriding R13 and ADR-0011 for exactly those edits, and the results commit
carries an ADR that names them and each file above, as ADR-0025 and ADR-0027 did.
The headlines and details hold no digit; they and the display names pass the copy guard
(`tests/test_registry_contract.py`); a display name may hold "per 90", as the served estimator denominators ("per 90 minutes") do.

### 11.2 A later promotion (`CONSTRUCTS` plus `SPECS`) — every hardcoded list

Not in this release (ARCH D1). Listed so that a later promotion is one deliberate release with
its own ADR, gated on the PUBLIC E-09 token only:

| # | Where | Change |
|---|---|---|
| 1 | `galactico/domain/constructs.py` | `_register(ConstructDefinition(id, claim, family, estimators=..., reference_estimator=..., display_name=<config display_name>, known_confounds=..., invalid_contexts=(... "goalkeeper" ..., the context limits of `results.json`, "cross-league comparison" ...), external_replication=<a second-provider label or UNTESTED>))`. A label beside the construct, never its gate (ADR-0018) |
| 2 | `galactico/features/spec.py::SPECS` | generated from the `CandidateSpec` (ROOT 4: one object), with a cross-reference to its fingerprint. `shot_volume` is expressible today (`Measure.COUNT`, `ActionFilter({"shot"})`, `PER_90`); the other three are **not**: they need a subtype filter, an OR of clauses, a zone on `start_x`, and a model-weighted measure. New `ActionFilter` fields must enter `fingerprint` only when non-default or all five shipped fingerprints change |
| 3 | the three `Measure` switch sites | `features/spec.py` (`evaluate`), `profiles/uncertainty.py` (lines 104 to 110), `match_lab/model.py` (lines 184 to 186) |
| 4 | `galactico/features/estimators.py` | `ESTIMATOR_DENOMINATORS` labels every per-action spec "completed passes" (wrong for `box_shot_share`, whose denominator is shots); `CHANNEL_GEOMETRY` / `describe_style` assume a 0.5 reference for any style share |
| 5 | `galactico/match_lab/model.py` | the hardcoded five-label dict (`labels`, line 153); a sixth key raises `KeyError` |
| 6 | `tests/test_player_lab.py`, `tests/test_registry_contract.py` | exact shipped set |
| 7 | `galactico/profiles/build.py` | `REJECTED` / `RESEARCH_ONLY` / `UNTESTED`; `RELIABILITY_CURVE` if a floor above 900 is wanted; `_render_state` has no band path, so an `ESTABLISHED_BAND` construct renders as insufficient signal today |
| 8 | `scripts/build_profiles.py`, the Player Lab bundle | rebuild; until then `/api/*` returns 503 (stale `semantic_versions`) |
| 9 | `galactico/optimization/historical.py` | `feature_fingerprints` is built from `SPECS` (line 247): every XI snapshot's provenance changes although the frozen file is not edited |
| 10 | `galactico/profiles/uncertainty.py` | every `SPECS` key is bootstrapped for every player |
| 11 | `scripts/generate_docs.py`, README.md, METRICS.md | regenerate `constructs`, `claims`, `rejected`, `counts`, `fingerprints` |
| 12 | `galactico/providers/statsbomb.py::MAPPING_AUDIT` | correct the existing "shot" row (it maps eventId 10 plus free-kick shots); add the defensive row with E-11's mapping |
| 13 | `galactico/domain/metrics.py` | the legacy `REGISTRY` seeds `defensive_action_profile`; `tests/test_domain.py` asserts it. Leave or retire deliberately |
| 14 | `galactico/domain/metrics.py::Family` | a per-90 count has no member other than the one named with a word this build does not put on an unvalidated label; `family="volume"` is internal for this release, and a neutral `Family` member is added at this promotion (ROOT 2.10 W4, DISSENT 3) |
| 15 | `galactico/domain/verdicts.py` | the promotion set, explicit and empty from the registration commit (ROOT 2.10 W1), gains the promoted id |
| 16 | `galactico/api/decision_lab.py` | **not changed.** The shipped requirement dict stays three keys |

### 11.3 Requirement dimensions

None in this release. No E-09 construct becomes an XI, Squad or Transfer requirement
dimension, a planning-page number or a value beside a player (ARCH D1). A later promotion that
proposes one decides it in its own ADR on the PUBLIC token alone; `box_shot_share` never
becomes one; `shot_location_value` stays UNAVAILABLE in every dated snapshot until an
instrument fitted strictly before the decision date exists (R9) and passes its
`followup_as_of_minimum_training_shots` gate, and under `ACCEPTED_WITHIN_LEAGUE` it would be
same-league only. A requirement sum of shot rates is not team shots: who shoots depends on
who else plays.

## 12. Model card — frozen template

`render_model_card(results)` emits exactly these sections; every number is read from
`results.json`, none is typed. `{...}` marks a field.

1. **Model details.** `shot_location_v1`; specification `{selection.specification}`; unpenalised logistic regression, IRLS, NumPy `{packages.numpy}`; formula of preregistration 4.1; pitch convention from `{config.pitch_length_m}` x `{config.pitch_width_m}` m, goal `{config.goal_width_m}` m; coefficients and standard errors for each of the five leave-one-league-out fits (table; when S-count failed, the words "not fitted" in place of the table); protocol commit `{...}`; training-frame hashes.
2. **Intended use.** Valuing the origin of open-play shots in aggregate over a player-season, within one league, for men's top-division club football of the season `{config.season}`, as input to a candidate that passes its own lifecycle.
3. **Out of scope, as prohibitions.** A verdict on a single shot. Finishing skill. Goalkeeper evaluation. Comparison with any provider's xG as if on one scale. Any season, tier, sex or provider not evaluated. Any dated decision, until a strictly-prior fit exists.
4. **What enters and what does not.** In: shot origin, provider head-or-body class. Not in: defender and goalkeeper positions, pressure, shot type, ball height, assist type, shooter, team, league, game state. Excluded as outcome-informed (preregistration 4.1): opportunity tag, accuracy tags, blocked tag, goal-mouth zone tags, counter-attack tag. The model is fitted on `distance_m`, `angle_rad` and `head_or_body` only; section 9 check 7 enforces this, and no sidecar column other than `body_part` and `shot_family` is loaded (`sidecar_columns`).
5. **Training data.** Pappalardo et al. 2019, CC BY 4.0; provider `Shot` events, periods `{config.periods}`, origin in the opponent half and not at a location sentinel; exclusions with counts `{structure}`; label = goal flag on the shot row; goals and shots by held-out league from `{instrument.sample_gate.folds}` (`heldout_goals`, `heldout_shots`), which are filled under every token, an S-count failure included.
6. **Evaluation.** Leave one league out, five folds; match-level resampling, `{config.bootstrap_replicates}` replicates, coefficients fixed.
7. **Metrics**, per held-out league and pooled, for `M0`, `MD`, `M1`, `MFLEX`: Brier, log loss, both skills against the training rate, observed over expected, calibration slope and intercept, ECE and MCE with the simulated null percentiles, AUROC (gated by R5 only as a leak check; not a skill criterion). Table from `{instrument.leagues}`, `{instrument.pooled}`; when S-count failed, the words "not fitted" in place of the table.
8. **By factor.** Observed over expected for footed, head-or-body, three distance bands (gated by R4; the footed and head-or-body ratios are close to 1 by construction under leave-one-league-out, preregistration 4.4); counter-attack flag (descriptive). Calibration bins per league. When S-count failed, the words "not fitted" in place of these tables.
9. **Uncertainty not in any number here.** (a) coefficient uncertainty: omitted from intervals; (b) omitted information: published comparisons with models that also see defender and goalkeeper positions put the per-shot disagreement at the same order as the mean shot value; its between-player part cannot be estimated from this corpus; (c) location error: integer-percent coordinates, unpublished operator accuracy; (d) outcome variance is not uncertainty about the model sum.
10. **Evidence class.** PREDICTIVE. Every construct built on it inherits it.
11. **Verdict and scope.** `{instrument.token}`, its statement from `registry_outcomes.instrument`; reason `{instrument.reason}`; failed gates `{instrument.failed_gates}`. Under `ACCEPTED_WITHIN_LEAGUE`: values carry no goal unit and are not compared across leagues.
12. **Caveats.** Metres are a convention on percent coordinates; the provider's pitch drawing is not metric; head-or-body is not header; one season; national-team matches not evaluated; in-sample valuation is forbidden (a league is always valued by the fit that excluded it).
13. **Temporal validity.** Full-season out-of-league fits are measurement instruments for research only.
14. **Change policy.** Formula and thresholds frozen at the protocol commit. A refit is a new model id with a new card; the specification selected by preregistration 4.3 is named in the id (`shot_location_v1/M1` or `/MFLEX`).

## 13. Order of operations and shared-file requests to the root

One order, the house order (north-star README, E-11 PIPELINE section 13), with E-09's root
rulings first: root rulings (ROOT 2.10, ruled and applied), the root's amendment of ROOT
2.2's `shot_location_value` parenthesis, independent audit to READY, structure counts,
registration, the pipeline, the self-check stamp, the run.

**Before registration** (nothing below is an outcome):

| Step | Detail |
|---|---|
| Root rulings | done: ROOT-DECISIONS 2.10 (18 October 2026) rules W1 to W10 on this draft, and no question waits for a ruling, except the textual amendment of ROOT 2.2's `shot_location_value` parenthesis (the next row; `root_rulings_applied`, `root_rulings_rule`). Applied in the revision of 18 October: W1, the explicit, empty promotion set of `product_admissible` (protocol section 10, 11.1, the registration commit below; OPEN QUESTION 1 closed); W2, open-play shots under the subject id `shot_volume`, and for `shot_location_value`, the non-penalty design removed from the config and kept in REVIEW-RECORD as the design not chosen (DISSENT 6 and OPEN QUESTION 6 closed as a design; ROOT 2.2's text waits for the next row); W3, candidates are `CandidateSpec`, and E-11's registered `provider_inputs.py` is the one recorded exception to Z3 on the public provider, tied by the exhaustive test of section 3 and pinned in `source_hashes`, while the external leg imports its flags (DISSENT 2 closed); W4, `family="volume"` internal for this release (DISSENT 3); W5, the two acceptance tiers and the R1 thresholds stand (DISSENT 5, OPEN QUESTION 2); W6, no registry record for the LOCAL leg (DISSENT 7); W7, the failed-run log under `run_output_root` (section 7); W8, the results commit's ADR naming the post-run product edits (11.1); W9, the draft guard in `tests/test_protocol_drafts.py` (below) |
| Root amendment | before the registration commit, the root amends ROOT 2.2's `shot_location_value` parenthesis to match this config (`root_amendment_before_registration`): location-only conversion-model-weighted open-play shots starting in the opponent half per 90 (no penalties, no direct free kicks), amended by 2.10 W2; or the root records in 2.10 that W2 covers both shot candidates. W2 ruled the design for both by removing `root_2_2_design`, whose `shot_location_value` weighted non-penalty shots, but its text amended only `shot_volume`'s parenthesis, so 2.2's letter still says non-penalty shots for `shot_location_value` (DISSENT 6). E-09 is not registered while it does. The partial amendment is the root's edit of 8e4f4cf; only the root edits ROOT-DECISIONS |
| Audit | an independent audit of the ruled revision that walks every branch of 4.5, 9.1 and 11, until one finds no blocker (E-11 and E-10 precedent; ROOT 2.9 Z4; ROOT 2.10 W10) |
| Structure counts | after the audit, the root runs one committed structure-only script over the five leagues and writes the keys of `counted_by_root_before_registration` (`counted_by_root_rule`): the null pins are filled, every pinned count carried over from working notes is recounted and replaced where it differs, with the difference stated; the three `sb_folder_digests` that are null are computed with `sb_reader.folder_manifest` on the local folders. These keys are the only edits to `config.json` after the audit. The three keys of `counted_by_root_assumption_pins` (body-part coverage 1.0, clause overlap 0, shot-family disagreements 0) are counted and never written: the frozen text depends on them (`shot_frame` raises on a null body part, preregistration 5.4 states that the clauses do not overlap, phase 2 stops on a disagreement), so a count that departs stops registration, and the draft returns to a revision that freezes a rule for those rows, then to an audit (`counted_by_root_assumption_rule`) |
| Verified values | `verified_by_root_before_registration`: `pipeline_spec_sha256` is `lf_sha256` of this file as it stands (an edit before registration means recomputing it); the `decide` and `_safe_abs_corr` source hashes and `decide`'s constants; the two sidecar versions against `galactico.ingestion.sidecar`; `e11_config_sha256` against the registered E-11 config; `sb_reader_source_sha256_in_e11_acceptance` against E-11's `acceptance.json` and the file |

**The registration commit** changes served output, and says so:

| File | Change |
|---|---|
| `experiments/preregistered/E-09-player-candidates/` | the three registered files (section 0); `experiments/preregistered/README.md` row `E-09 player candidates`, `preregistered, not run` |
| `galactico/domain/verdicts.py` | the five `PENDING` records of section 11.1; `product_admissible(c)` returns `verdict_for("E-09", c).may_gate and c in PROMOTED`, `PROMOTED` an explicit, empty frozenset (`promotion_set_in_this_release`; ROOT 2.10 W1), so a PUBLIC, executed, established E-09 record admits nothing until a later promotion, its own change set with its own ADR; the docstring's paragraph naming E-09 a draft and saying `product_admissible` is false while E-09 is not registered; and its sentence that `may_gate` is the only value that may unlock a number-bearing panel gains that for E-09 a panel is unlocked through `product_admissible` only |
| `tests/test_verdict_registry.py` | the shipped-registry test (it lists E-11's sixteen records); the `product_admissible` test gains the promotion set; a test that `product_admissible` is false for every E-09 subject under every token of the config; a test that no route or page unlocks anything on an E-09 `may_gate` in this release (`web/labs-shared.js` `mayGate` is not consulted for E-09) |
| `tests/test_protocol_drafts.py` | the E-09 draft guard is already there (ROOT 2.10 W9, added with the revision that applied the rulings, as E-11's was) and ties the E-09 files, each check run on the files, where it finds nothing, and on a copy with the defect planted, where it finds it (M-06): `lf_sha256` of `PIPELINE.md` equals `pipeline_spec_sha256`; every record built from the config under `PENDING` and under every token constructs and its `as_payload` passes `runtime.finalize`; every `player_lab_text`, `baseline_prose`, `nuisance_prose`, `planning_after_run` sentence, display name, sentence and `claim` text passes `labels.scan_labels`, and the Player Lab texts, the two prose maps and every `registry_outcomes` statement hold no digit; on `{"provenance": {"config": config}}` and on a skeleton of the full 7.1 shape (every key section 7.1 names and every field of the section 6 dataclasses, read from this file): the exact-key denylist walk, `banned_key_paths(..., parts=BANNED_KEY_PARTS)` and the provider-name walk each find nothing, and each finds a planted `id`, `rank_ties` or `wyscout_x` key. The registration commit points the guard at `committed_experiment_dir`, as E-11's registration did |
| `tests/test_preregistration_order.py` | nothing: `PROTOCOL` already holds `PIPELINE.md` |
| `tests/test_licensing.py` | remove the draft `preregistration.md` and `PIPELINE.md` from their lists (they become one-line pointers) and add the registered pair to `NO_FIGURE_FORMED_FROM_STATSBOMB`; the registered `preregistration.md` draws the logo by the registration-time path |
| `LICENSING.md` | its sentence that "the draft protocols E-09, E-11 and E-12" print analysis formed from StatsBomb data is false for E-09, which is on `NO_FIGURE_FORMED_FROM_STATSBOMB`; the root's wording |
| draft folder | `preregistration.md` and `PIPELINE.md` become one-line pointers; `config.json` is deleted (section 0) |
| `galactico/api/planning.py` | the `shots` entry of `NOT_MEASURED_EXTRA` says no registered protocol tests a shot construct, which is false once E-09 is registered; the root's wording for the registered, not run state (the post-run sentences are frozen, `planning_after_run`) |
| prose that calls E-09 an unreviewed draft or a draft with no review | `docs/research/north-star/README.md`, `KNOWN_LIMITATIONS.md` ("Registered or drafted, not run", the sidecar entry), ROOT-DECISIONS 2.6's registry sentence, ADR-0018's registry paragraph, ADR-0028's "Confidence" sentence |
| ROOT-DECISIONS 2.2 | the `shot_location_value` parenthesis, if the root has not amended it before (the "Root amendment" row; `root_amendment_before_registration`) |
| `docs/assets/statsbomb/statsbomb-logo.png` | the existing file, unchanged |

**After registration, before the run:**

| Step | Detail |
|---|---|
| The commit that adds the pipeline | the source files and tests of section 0, `candidate_sb.py` and its tests included. In that commit, and not before, `tests/test_research_firewall.py` gains `galactico.validation.shot_model_evaluation`, `candidate_gauntlet`, `candidate_synthetic` and `candidate_sb` in `RESEARCH_PIPELINES` (`test_the_lists_name_modules_that_exist` requires each listed file to exist) |
| Review and stamp | the checklist of section 9; then `--selfcheck` on the frozen config writes `selfcheck.json` (section 7.3, `selfcheck_stamp_rule`), committed beside the protocol unchanged in a commit of its own after the pipeline and before the results. A failed stamp stops E-09 before any outcome (section 8.3). Any later change to a pinned source file means a new stamp, and phase 1 refuses an old one |

**After the run:** the results commit (`results.json`, `analysis.md`, `MODEL-CARD.md`, the
record tokens and hashes, the registry, planning and gap-matrix edits of 11.1, and the ADR
that names them, ROOT 2.10 W8). `analysis.md` goes on the `tests/test_licensing.py` list that
fits it if it names the
provider; the external leg's `sb_report` goes on `FORMED_FROM_STATSBOMB` in the commit that
adds it.

## DISSENT

1. **"CONSTRUCTS plus SPECS" cannot be the consequence of a positive verdict in this release.**
   Evidence: `ConstructSpec` cannot express three of the four candidates (11.2 row 2) and
   `features/spec.py` is frozen for implementers; a sixth `SPECS` key changes
   `feature_fingerprints` in every XI snapshot, stales the Player Lab bundle (503) and raises
   in Match Lab, all of which R13 pins. ARCH D1 has since ruled the same way: no promotion in
   this release. The full registration list (11.2) is kept for the later release.
2. **Candidates are `CandidateSpec`, not `ConstructSpec`.** The root layout says "candidate
   ConstructSpecs". Same evidence. `shot_volume` exists once, as a `CandidateSpec`, and is
   tested equal to the house `shots_per_90` column; a `ConstructSpec` form is generated from
   it at promotion, never written beside it (ROOT 4, ROOT 2.9 Z3). On the public provider one
   duplicate remains and cannot be removed: E-11's registered `provider_inputs.py` computes the
   same two imported definitions for its own purpose. E-11's code is registered and pinned,
   and product code may not import it. ROOT 2.10 W3 ruled both points: candidates are
   `CandidateSpec`, and the duplicate is a recorded exception to Z3, tied not by a sampled
   parity test but by the test of section 3, which imports `provider_inputs` and asserts equal
   masks on every row type, subtype and flag combination of the public adapter's closed
   vocabulary, with `provider_inputs.py` pinned in `source_hashes` (section 7.2). On the second
   provider there is no duplicate: W3's reason does not apply to `candidate_sb.py`, which is
   research code, so the external leg takes the open-play shot and the interception flag from
   `provider_inputs._statsbomb_flags` itself, imported as a private member as `sb_reader._spell`
   is, under the same pins (section 10, `sb_flags_rule`). Closed.
3. **The registry's only family for a per-90 magnitude is named with a banned word.** `Family`
   has QUALITY, STYLE, PHYSICAL, TEAM; shipped per-90 constructs use the first. Candidates
   carry `family="volume"` here. ROOT 2.10 W4 accepted the name as internal for this release;
   a neutral `Family` member is added at promotion (11.2 row 14). Closed.
4. **The frozen `decide()` is reused unchanged, but not with Stage 1B's inputs.** Its battery
   contains shots per 90 (the candidate itself); `decide(0.9, 0.0, float("nan"), False)`
   returns `SHIP`; the house R-squared is joint with team although the rule's docstring
   thresholds nuisance variance; the baseline and nuisance statistics here are the larger of
   two centrings, and the reliability bound is the half-r bound. The rule body and thresholds
   are untouched and pinned by source hash; every input departure is tabled with its
   direction in preregistration 6.1.
5. **Two-tier instrument acceptance.** The root asked for frozen acceptance thresholds; this
   design freezes them and adds a scope tier (`ACCEPTED_WITHIN_LEAGUE`). A single tier would
   most likely reject the instrument on Italy's level (planning figure 0.897), a property no
   within-league candidate uses. ROOT 2.10 W5 accepted the two tiers and the R1 thresholds.
   Closed.
6. **`shot_volume` and `shot_location_value` count open-play shots, not all non-penalty shots
   (ROOT 2.2).** Evidence: the registered E-11 defines `shot_volume` as open-play shots and
   `non_penalty_shot_volume` separately, and its token applies to an E-09 candidate only if
   E-09 imports its definition unchanged; the house `shots_per_90` baseline counts the neutral
   `shot` type only, so the identity of 5.1 holds; a direct free kick's origin is set by where
   the foul was given, not chosen by the shooter, and its conversion follows another process,
   which the location-only model would value as an open-play shot from that spot. The display
   names say "open-play", and `shot_volume`'s says "no direct free kicks". ROOT 2.10 W2 ruled
   for open-play shots on this evidence: for `shot_volume` by its text, which amended ROOT
   2.2's first parenthesis, and for `shot_location_value` by removing `root_2_2_design`, whose
   `shot_location_value` weighted non-penalty shots. W2's text did not amend the second
   parenthesis, which still reads non-penalty shots; that textual amendment is pending with the
   root and E-09 is not registered before it (section 13, "Root amendment";
   `root_amendment_before_registration`). The non-penalty design once written beside this one
   is removed from the config and kept in REVIEW-RECORD as the design not chosen. Closed as a
   design; open as a text of ROOT 2.2 until the root amends it.
7. **No registry record for the external leg.** ROOT 2.9 Z5 has since ruled the same way for
   E-10's LOCAL arm: a hosted label from such an arm needs its own LOCAL record, created by a
   later protocol. A LOCAL `VerdictRecord` in E-09's directory
   would make `tests/test_verdict_registry.py::local_estimate_failures` read E-09's PUBLIC
   `results.json`, whose aggregate floats it refuses, and would require its `analysis.md` to
   carry the StatsBomb logo. The leg's token is therefore a label in its credited note only,
   and moves nothing. ROOT 2.10 W6 accepted this, as Z5 for E-10. Closed.

## OPEN QUESTIONS

1. ARCH D1 against `product_admissible`: closed by ROOT 2.10 W1. No candidate is promoted in
   this release, and the registration commit gives `product_admissible` an explicit, empty
   promotion set (section 13); a later promotion is its own change set with its own ADR.
2. Thresholds R1 (0.08 pooled, 0.03 per-league lower bound) differ from the reconnaissance
   proposal (0.08 point and 0.05 lower bound in every league). By derived sampling error
   (`planning_figures.r1_league_brier_skill_se`) the proposal fails a model whose true skill
   is 0.10 in about one run in five (`planning_figures.open_question_2_proposal_failure_rate_at_true_skill_0_10`).
   ROOT 2.10 W5 accepted the frozen thresholds. Closed.
3. A per-shot mean of the instrument was left out in favour of `box_shot_share`. If the
   root wants it, it is a fifth candidate and needs its own protocol.
4. Should Euro 2016 and World Cup 2018 be an external transport test of the instrument? Not
   in this protocol.
5. Whether E-10 uses `shot_location_v1` for conceded shot value; if so its protocol must cite
   the instrument token.
6. ROOT 2.2 against DISSENT 6: ruled by ROOT 2.10 W2. `shot_volume` and `shot_location_value`
   count open-play shots, as E-11 registered for `shot_volume`, and the non-penalty design is
   removed (DISSENT 6). W2's text amended only `shot_volume`'s parenthesis of ROOT 2.2; the
   root amends `shot_location_value`'s, or records that W2 covers both, before the registration
   commit (section 13, "Root amendment").
