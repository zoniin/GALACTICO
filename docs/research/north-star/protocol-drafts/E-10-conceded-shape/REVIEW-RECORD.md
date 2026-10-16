# E-10 review record

What each round of review found in the E-10 draft and what was done with it. The draft
(`preregistration.md`, `config.json`, `PIPELINE.md`, `descriptor_test_vectors.json`) is not
registered and nothing in it has been run. Every number below was computed on synthetic
seasons or is arithmetic; no file under `data/` was opened in any round.

## 14 October 2026 — first review, three lenses, and the revision

Three adversarial reviewers read the draft against ROOT-DECISIONS, the ADRs, the house
lifecycle and the registered E-11 protocol: a statistician (17 findings), a reader of the
football data (20) and a reader for the constitution (28). One reviser verified each finding
against the draft, the shipped code and the rules, and applied it or rejected it. Every finding
held. All 65 are applied; three have a part rejected, with the reason in the table.

| Severity | Findings | Applied | Rejected in full | Applied with a part rejected |
|---|---|---|---|---|
| blocker | 16 | 16 | 0 | 0 |
| major | 26 | 26 | 0 | 1 |
| minor | 23 | 23 | 0 | 2 |

Several findings are one defect seen by two or three lenses; each is listed under its own id.

### What the revision changed, in short

- **Vocabulary.** A descriptor's verdict now names the first of ROOT 2.2's questions that
  failed: `DEFENDER_SHAPE_SIGNAL`, `FORECAST_NOT_SHOWN`, `SIDE_NOT_SHOWN`, `NOT_RELIABLE`,
  `STRENGTH_NOT_EXCLUDED`, `INCONCLUSIVE`. The level is its own subject (`LEVEL_ESTABLISHED`,
  `FORECAST_NOT_SHOWN`, `NOT_RELIABLE`, `INCONCLUSIVE`) with its own gates; `LEVEL_ONLY` is
  gone. Every sentence is true in every branch that reaches it.
- **Registry.** Seven PUBLIC records built from `registry_*` entries of the config; badges are
  those `badge_text` produces; three figures per established record; the REPLICATED row that
  let a LOCAL verdict unlock a hosted panel is deleted (ADR-0018).
- **Statistics.** ROOT O5's critical value; one shared world of (league, week) multiplicities
  for every estimand; criterion (a) as a p-value so the primary and Holm read the same thing;
  Holm's order fixed; criterion (g) is the house confound audit with the lifecycle's nuisance
  ceiling; an opponent- and venue-balanced split; the gate plants latent-strength shapes at four
  sizes and runs at three overdispersion values.
- **Data.** The shipped sidecar API (`load`, `attach`, `verify`, `provenance`); validity once
  per match, with dismissals checked against the sheet; Match Lab's goal rule with own goal
  first; results from the sheet for strength; `sb_reader` for the replication with E-11's pass
  types; float64 cuts; the `oracle` columns defined.
- **Names.** No key names a provider; the LOCAL module is `conceded_shape_sb.py`; labels follow
  ROOT H14-H21; the S4 and S5 sentence no longer holds a phrase the copy guard refuses.
- **Order.** Registration with PENDING records, then the pipeline, then the gate stamp, then the
  run; `pipeline_spec_sha256` pins `PIPELINE.md`.

### Statistics lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-statistics-1 | blocker | Reachable branches where (a) passed printed a sentence saying no out-of-sample information was found; the claim omitted (d), (e), (g); WIDTH_ONLY mislabelled "no defender shape" | Applied. Claim restated as the conjunction; one token per failing question with its own frozen sentence and precedence (`verdict_precedence`); WIDTH_ONLY labelled a width-only defender shape everywhere, DISSENT 1 corrected; truth tables extended to the statement |
| R-statistics-2 | blocker | The gate planted a shape that is exactly the first V1 covariate, not the latent-tercile shape the protocol promises to reject at 5% | Applied. `STRENGTH_TERCILE_0_08` to `_0_15` (cut, coding and scaling in `strength_shape_rules`) gate at 5% each, at overdispersion 0.1 and 0.8; `STRENGTH_MEASURED_0_15` kept; (g) tightened (R-statistics-9). Reviser's check, 200 synthetic seasons per entry: (e) and (g) together held in 0 seasons for every strength plant at every overdispersion, against 33 of 200 under the draft's (g) at size 0.10 (with O5's critical value) |
| R-statistics-3 | blocker | Reliability bound used 1.96 where ROOT O5 binds 1.6449 below 100 units | Applied. `reliability_critical_value` 1.6448536269514722; thresholds 0.646 (band) and 0.788 (number); test values r = 0.4770 gives 0.50009, r = 0.6495 gives 0.70001 |
| R-statistics-4 | blocker | Every estimand and descriptor drew its own resampling world, against R12 | Applied. One `SeasonWorld` per run (`world_cluster`, `world_strata`, `world_draw`, `seed_streams.season_world`), shared by every descriptor, estimand, subset and window; its fingerprint is in provenance; per-estimand offsets removed |
| R-statistics-5 | major | The level's INCONCLUSIVE condition, its gates and its selection rung were undefined | Applied. `level_gates` (G1 to G4 and LG6); the level runs whenever its own gates pass; `level_selection_rule` (B1 deviance for kA', B2 for kD' with `context_only`); truth-table branches added |
| R-statistics-6 | major | (Lb)'s four leagues, (Le)'s +0.5, the gate's 1000 stride and code defaults lived outside config | Applied. `level_minimum_leagues_with_negative_estimate`, `log_ratio_smoothing_per_part` named for (Le), `seed_stride_per_scenario` and `seed_stride_per_overdispersion`; no signature has a default for a config value |
| R-statistics-7 | major | Holm's handling of None, ties and family size undefined; family-wise rate never measured | Applied. `holm_order_rule` (m fixed, None and NaN last and never rejected, ties by list order); `SECONDARY_FAMILY_NULL` gates the family-wise rate at 5% |
| R-statistics-8 | major | The generator's design effect (about 1.1) was far below the 4 to 9 the power sentence assumes | Applied in part. `overdispersion_grid` 0.1, 0.5, 0.8 (design effect about 1.1, 3.3, 6.1, reported by `design_effect`); every null gated at the lowest and highest value; detection rates published at all three; the power section prints the reviser's synthetic result (a 0.15 SD effect passes (e) and (g) in 200, 87 and 0 of 200 seasons). Rejected part: gating `EFFECT_STRONG` at the highest value; at a design effect of 6 no effect of that size passes (e) in 200 seasons, so the gate could never pass, and the gate tests the code, not power |
| R-statistics-9 | major | (g) departed from the house audit unstated, declared no confound kind, and could not be built two ways alike | Applied. `strength_confound_kind` NUISANCE for every descriptor (reasoning in config), CONTEXT for the level; (g) is `discriminant_validity(...).passed` with the lifecycle's 0.25 ceiling, the Spearman floor and top-12 survival, thresholds passed explicitly; departures stated |
| R-statistics-10 | major | Replication seed, replicates, events minimum, orientation failure and mirror condition undefined | Applied. `seed_streams.replication_world`, `replication.bootstrap_replicates`, an events minimum; orientation failure is `REPLICATION_INCONCLUSIVE (ORIENTATION)`; a mirror descriptor needs M1 too |
| R-statistics-11 | major | Three keys named the local-tier provider | Applied. `penalty_box_sb`, `penalty_box_wy`, `descriptor_fingerprints_sb`, vector blocks `sb` and `wy` |
| R-statistics-12 | minor | Per-league seed for England collided with the sensitivity seed | Applied through R-statistics-4: no per-estimand seed remains |
| R-statistics-13 | minor | Quantile method unfixed; interval and p-value could disagree; tie set ambiguous | Applied. `interval_quantile_method` linear; (a), (d), (La) and replication read the p-value (`p_value_rule`), as Holm does; tie set relative to the minimum |
| R-statistics-14 | minor | The truth table enumerated booleans only | Applied. `{True, False, None}` for both maps, with gate patterns, token and statement |
| R-statistics-15 | minor | "Five percentage points" overstated; "half the time" was per coordinate; the V1 sentence was false on a missing value | Applied. About four points (3.9 and 3.6); half per coordinate, a quarter for two; the V1 sentence replaced by `STRENGTH_NOT_EXCLUDED`'s, true for every failure of (g) |
| R-statistics-16 | minor | The date-alternating split is not venue-balanced | Applied with another split. Rejected part: the proposed alternation within home and within away rows; on synthetic seasons it leaves the halves facing different opponents and lowered the mean half correlation (0.435 against 0.547 for a 0.09 SD effect; about -0.14 under no effect). `reliability_split` gives each half one meeting with each opponent, home and away balanced; the generator's schedule is Berger tables (`schedule_rule`) |
| R-statistics-17 | minor | G3's events, terciles, matchup permission, gate sensitivity and gate seeds underspecified | Applied. `evaluation_events_rule`; one tercile formula with the config's count; I1 reported only, so nothing is permitted; the gate passes `sensitivity=False`; every season's world and donor maps use its own seed; the protocol says S2 and S3 counts were not looked at |

### Football-data lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-football-data-1 | blocker | "Exact fractions" in the protocol against float comparison in the pipeline | Applied. `fraction_rule` (E-11's wording); StatsBomb cases 80/120, 40/120, 102/120, 62/80 added to the edge test |
| R-football-data-2 | blocker | The S4/S5 sentence held "line height", which the copy guard refuses; "predicts" passed only by inflection | Applied. New sentence; "accounts for" throughout; every registry sentence served through `finalize` under every token (scratch check run; test specified for registration) |
| R-football-data-3 | blocker | A REPLICATED row let a LOCAL verdict unlock a hosted panel, against ADR-0018 | Applied. Row deleted; panel depends on the PUBLIC token only; the replication status stays in `analysis.md` and as a token in `results.json`, never served; old DISSENT 2 and OPEN QUESTION 2 removed |
| R-football-data-4 | blocker | Provider-named keys would fail the licence test at registration | Applied (as R-statistics-11), plus the runner's three-name rule at any depth |
| R-football-data-5 | major | The registry could not produce the frozen badges or conditional sentences; timing contradicted the registry | Applied. Records specified against `VerdictRecord` (two vocabularies, claim tokens, non-claims, not-run statement, one statement per token, figures with pointers); badges are `badge_text`'s; PENDING records at registration |
| R-football-data-6 | major | Sidecar functions that do not exist; the sanctioned join and loader ignored; a false coach-id sentence | Applied. Section 1 rewritten on `load_public`, `sidecar.load`, `attach`, `verify`, `provenance`; a failed load or join is a refusal; `sidecar_missing` removed; OPEN QUESTIONS 1 and 3 closed; coach ids exist and their count is reported |
| R-football-data-7 | major | Dismissals never checked against the sheet | Applied. `dismissals_mismatch` (`dismissal_check`, squads `red_minute`), fail closed, counted by league, tested; the second-yellow rule is checked structure-only before registration |
| R-football-data-8 | major | `match__` columns defined only by equality to Match Lab; one is a V1 input | Applied. Each defined in 2.2 (Match Lab's shot rule, set pieces included); a penalty and a direct free kick in the synthetic oracle; stale clearance note removed |
| R-football-data-9 | major | Replication mapping departed from the Wyscout arm and E-11; a second StatsBomb reader | Applied. Kick-off is an open-play pass (`sb_open_play_pass_types`); sentinels Wyscout only; frames from `sb_reader`, matches from the index only; `event_id` typed per provider; the known-differences sentence corrected |
| R-football-data-10 | major | O5 critical value | Applied (as R-statistics-3) |
| R-football-data-11 | major | Registration and results commits would fail the licence tests; vectors unguarded | Applied. Section 13 lists the `test_licensing.py` list moves, `analysis.md` on the credited list with its logo path, the vectors in `PROTOCOL` with the scratch-history edit, the firewall entries in the pipeline commit |
| R-football-data-12 | minor | Column names dropped the partition and could collide silently | Applied. The partition key is in the name, and two columns with one name and two tokens raise |
| R-football-data-13 | minor | Validity depended on the window | Applied. Decided once per match for every window (`validity_scope`) |
| R-football-data-14 | minor | No precedence for a goal row that is also an own goal; the rule differed from Match Lab unstated; clock check cannot fire | Applied. Match Lab's rule adopted through `goal_on_scoring_event`, own goal first; a goal flag on a non-shot row tested; the protocol says a missing Wyscout clock reads as 0.0 and a missing coordinate as 0 |
| R-football-data-15 | minor | Sentences said more than the numerator | Applied. "shots not taken directly from a set piece", "fouls recorded as Foul", "the opponent's right lateral third", "no shot end coordinate"; vectors regenerated, payloads and fingerprints unchanged |
| R-football-data-16 | minor | "Encodes home/away" and "verified on both providers" had no source | Applied. Both removed; StatsBomb orientation is checked before replication; for Wyscout the protocol says the convention is the provider's, undocumented here and unchecked, and that no verdict depends on it while the panel's names do |
| R-football-data-17 | minor | Token grammar left the join, the zero bound and the anchor open | Applied. `&`; `none` only for None; the anchor must be in `needs` |
| R-football-data-18 | minor | Strength ignored the sheet results of invalid matches | Applied. Points and goals from the sheet for every match |
| R-football-data-19 | minor | No confound kind declared | Applied (as R-statistics-9) |
| R-football-data-20 | minor | Composition source unstated; (Lb) in prose; an ambiguous key; code defaults | Applied. The source is recorded as not known (`league_composition_source`) and disclosed in the prior-exposure table; the (Lb) key added; `run_only_if_descriptor_verdict`; the dismissal and goal lists in the equality test |

### Constitution lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-constitution-1 | blocker | Provider-named keys, including a source path | Applied. Keys renamed; the module is `conceded_shape_sb.py`; `key_naming`; the E-10 twin of the draft checks specified for the registration commit (run now as a scratch check) |
| R-constitution-2 | blocker | "line height" in a frozen sentence | Applied (as R-football-data-2) |
| R-constitution-3 | blocker | A LOCAL verdict as the gate of a number-bearing panel; PREDICTIVE class | Applied (as R-football-data-3); no PREDICTIVE class anywhere |
| R-constitution-4 | blocker | Badges and conditional sentences the registry cannot produce | Applied (as R-football-data-5); A5 and A6 rewritten (sections 1 and 12) |
| R-constitution-5 | blocker | No registry entries in config | Applied. `verdict_vocabulary`, `verdict_precedence`, `registry_common`, `registry_non_claims`, `registry_descriptor`, `registry_level`, `registry_outcomes`, `registry_figures`, `subject_groups` |
| R-constitution-6 | blocker | Records written after the run; protocol committed with the pipeline | Applied. Section 13 in the house order: registration with PENDING records, pipeline, gate stamp, run, results |
| R-constitution-7 | blocker | `results.json` broke the registry's contract; the replication had no lawful form | Applied. `experiment`, `tier`, `verdicts {token, reasons}` at the top; the replication is tokens in `results.json` and numbers in `analysis.md` only, with no registry record. Reviser's check: a synthetic `results.json` of this shape with the seven executed records passes every checker of `tests/test_verdict_registry.py` |
| R-constitution-8 | blocker | One NOT_ESTABLISHED sentence and badge for every non-signal outcome | Applied (as R-statistics-1); the proposal sentence is "based on a record that did not pass E-10" |
| R-constitution-9 | major | O5 critical value | Applied (as R-statistics-3) |
| R-constitution-10 | major | Level gates, selection and number rule undefined; level unlocked a number with no strength criterion | Applied. Level gates and selection (R-statistics-5); the point needs the reliability figure at 0.70; the panel is EXPERIMENTAL behind the opt-in with a sentence that strength is not separated; strength declared CONTEXT for the level (DISSENT 4) |
| R-constitution-11 | major | Prior-exposure table incomplete; no prior-knowledge paragraph | Applied. Rows for E-11 as registered and as being built, Match Lab's served counts, the composition constant and the uncommitted scripts; the run order; a prior-knowledge paragraph from what the design relied on (section 4.4 of the critique is not in the repository) |
| R-constitution-12 | major | A fixed R² rejection without a confound kind; no lifecycle status | Applied (as R-statistics-9); `lifecycle_status` maps every token |
| R-constitution-13 | major | Served interval, shrink weight and figures undefined | Applied. Section 12.3 (composition, volume, shrink weights, LEAGUE_MATCHES worlds, `served_panel`), figures with pointers (12.2) |
| R-constitution-14 | major | The panel could use constants and a verdict from after the decision date | Applied. `panel_from_date` is `evaluation_start`, and the established statements say the verdict was decided on the whole season |
| R-constitution-15 | major | Registration commit under-specified | Applied. Section 0 (registered bytes, the one banner edit), section 13 (hash pin, test and page edits, firewall timing, draft pointers) |
| R-constitution-16 | major | Sidecar functions that do not exist | Applied (as R-football-data-6) |
| R-constitution-17 | major | A real-data test before the protocol commit could compute descriptor counts | Applied. The real oracle requests no descriptor column and runs only after registration |
| R-constitution-18 | major | No rule for a failed run, a determinism mismatch or an orientation failure | Applied. Failure log, no results, repair limited to the stage; a byte difference is a failed execution; replication failures keep the public results |
| R-constitution-19 | major | The no-literal test could not pass on the specified code | Applied. Strides, scale, orientation threshold and counts in config; timestamps parsed by `sb_reader`, so no time constants |
| R-constitution-20 | major | STRENGTH_ONLY defined two ways; WIDTH_ONLY mislabelled; "four" sizes against three | Applied (as R-statistics-2 and R-statistics-1); "three smaller effects" |
| R-constitution-21 | minor | Labels differ from ROOT H14-H21; "def" and "acting team" read badly; S5's key reads as an own share | Applied in part. Labels follow H14-H21 and sentences say "defending team's left" and "the opponent's right lateral third". Rejected part: renaming the key `high_zone_defensive_action_share`; E-11 registers the same `D / (D + P)` under that name, and the key is in the payload, so renaming would move the fingerprint and lose the cross-reference; its label states the definition |
| R-constitution-22 | minor | The claim did not say the primary needs side information | Applied ("including which side") |
| R-constitution-23 | minor | "Permitted" matchup features had no consequence | Applied. I1 reported only |
| R-constitution-24 | minor | Vectors held two of four StatsBomb-side entries; one dictionary's fingerprints checked | Applied. Four entries with columns; the runner checks both dictionaries |
| R-constitution-25 | minor | A None p-value's place in Holm undefined | Applied (as R-statistics-7) |
| R-constitution-26 | minor | `strength_rank_correlation_floor` carried a banned key part | Applied. `strength_spearman_floor`; no config key carries a banned part |
| R-constitution-27 | minor | A digest of a LOCAL-derived file committed | Applied. Removed |
| R-constitution-28 | minor | `analysis.md` could name or order teams; top-12 under ties | Applied. Neither; a tied twelfth place leaves the count undefined and (g) fails by name |

### Three items settled before registration

1. Keys that named the local-tier provider are renamed with an `sb` or `wy` part (E-11's
   convention), in `config.json` and `descriptor_test_vectors.json`, and the LOCAL module's path
   is `conceded_shape_sb.py`.
2. The logo. The protocol prints no figure formed from StatsBomb data and draws no logo, here
   or when registered. The one E-10 document that will draw it, `analysis.md`, uses the path
   `../../../docs/assets/statsbomb/statsbomb-logo.png` from the registered folder (PIPELINE
   12.4); the registration edits `preregistration.md`'s banner and nothing else (PIPELINE
   section 0).
3. The sidecar functions the draft named are replaced by the shipped ones
   (`galactico/ingestion/sidecar.py`: `load`, `attach`, `verify`, `provenance`,
   `SIDECAR_SCHEMA_VERSION`, `TAG_MAPPING_VERSION`).

### Checks run by the reviser (synthetic or data-free)

- Every registry sentence, figure sentence, scope and descriptor sentence passes the copy guard;
  seven records built from the config are served by `api.runtime.finalize` under `PENDING` and
  every token, and a planted "line height" is refused.
- No key at any depth of `config.json` or `descriptor_test_vectors.json` names a provider or
  carries a banned key part; the eight fingerprints recompute from the payloads and equal the
  config.
- A synthetic `results.json` in the shape of PIPELINE section 8 passes every checker of
  `tests/test_verdict_registry.py`.
- `tests/test_licensing.py` and `scripts/check_licensing.py` pass with this file on
  `NO_FIGURE_FORMED_FROM_STATSBOMB`.

Not yet done after this round: an independent audit that walks every branch of both verdict
rules (done on 16 October 2026; next section).

## 16 October 2026 — Audit, and the audit's revision

An independent audit read the revised draft in four scopes against ROOT-DECISIONS, the ADRs,
KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle and the registered E-11
protocol: A-1 measurement, frames and football data; A-2 statistics and models; A-3 claims,
product consequence and registry; A-4 pipeline, runner and reproducibility. Every claimed
blocker was given to a refuter, who rebuilt it on synthetic numbers; none was refuted, and
four of the five came back with a corrected proposal, which is the one applied. One reviser
then verified every major and minor against the draft, the shipped code and the rules and
applied it, or applied a variant with the reason stated. No file under `data/` was opened;
every number below is synthetic or arithmetic, or a structure count already pinned in a
committed test.

Scope readiness as audited: A-1, A-3 and A-4 each had at least one confirmed blocker, so none
was READY; A-2 had no blocker and three majors. After this revision every finding is applied,
but the revision itself has not been audited.

| Severity | Findings | Applied | Applied with a variant or a part changed | Rejected | Refuted |
|---|---|---|---|---|---|
| blocker | 5 | 5 | 0 (each with the refuter's corrected proposal) | 0 | 0 |
| major | 12 | 12 | 2 (A-1-2, A-3-4) | 0 | 0 |
| minor | 32 | 32 | 2 (A-2-8, A-4-15) | 0 | 0 |

Duplicates, each listed under its own id: A-3-1 = A-4-3; A-1-7 = A-2-1 = A-3-3; A-2-2 = A-4-6;
A-2-5 = A-4-15; A-2-9 = A-3-12; A-2-11 = A-3-5 = A-4-5; A-3-4 overlaps A-4-17.

### Blockers

| Id | Finding | Disposition |
|---|---|---|
| A-1-1 | (g) was not invariant to exchanging left and right: the house audit counts survivors among the `k` largest values only, so the token could be `DEFENDER_SHAPE_SIGNAL` or `STRENGTH_NOT_EXCLUDED` by the sign of a basis row. The Frames sentence "no verdict depends on it" (R-football-data-16) was false | Applied, refuter's version. (g) calls `discriminant_validity` on the coordinate and on its negation and needs both (`strength_survival_tails`); R2, R2_adj, permutation p and Spearman are reported once from the call as computed; survivors and tie counts per tail; `failures` prefixed by tail; the Frames sentence and the not-claimed line rewritten (this also revises R-football-data-16's disposition: the invariance now holds because (g) reads both tails); I8, 4.3 `strength_validity`, section 8 keys, section 11 item 18, two tests with hand-built vectors written in the test (one-tail pass and two-tail fail; a tied twelfth place in the lower tail). Reviser's rerun of the 14 October simulation on the same seeds with the two-tail rule (scratch `audit-rev/twotail_sim.py`, 200 seasons per cell): every (e)-and-(g) count is unchanged, 0 for every strength plant at 0.08 to 0.15 and for measured points, `WIDTH_ONLY` and `NULL_NOTHING`, `EFFECT_STRONG` 200 / 87 / 0, `EFFECT_0_09` 132 / 0 / 0, so the `EFFECT_STRONG` gate requirement is not made harder to meet. On the auditor's 4,000 draws the one-tail rule changed under negation in 39 and the two-tail rule in 0 (`audit-rev/twotail_invariance.py`) |
| A-3-1 | The synthetic seasons named their leagues `L0..L4` while the rule reads `leagues` and `unexposed_leagues`, so (f) was `None` in every gate season and `EFFECT_STRONG` could never reach `DEFENDER_SHAPE_SIGNAL` | Applied, refuter's version, option 1: synthetic league `i` is named `leagues[i]` with `expected_teams_per_league` teams (`synthetic_gate.league_rule`); `team_counts` removed. A synthetic season's evaluation reads `config.json` with exactly `seed` and `bootstrap_replicates` replaced, stated in section 5, section 10, `season_seed_rule` and the protocol, and asserted by `run_gate`. Tests: every league subset fed, (b), (f), (Lb) not `None`, G1 to G3 on non-empty counts, strata in `leagues` order; the end-to-end shape test now runs one five-league season |
| A-4-1 | The runner's clean-tree refusal could not be satisfied by the determinism re-run or by any run after a failure, because outputs and the failure log were untracked and not ignored | Applied, refuter's version. `output_root` = `data/licensed/research/E-10` (already ignored; E-11's form), with `output_results`, `failed_run_log`, `replication_failure_log` and `determinism_record` under it; the results commit copies `results.json` unchanged and checks it as if at its committed path. Clean tree stays the full `git status --porcelain`. A replication exception goes to `replication_failure_log`, never to `failed_run_log`; `--verify` takes a `FAILED_RUN` replication unchanged, compares `results.json` and the local artifact, writes only the determinism record, and on a difference removes the outputs and appends one `serialise` record. The failure-on-the-record rule is one sentence in 7.2, 7.4 and the protocol (committed `analysis.md` at `HEAD` holds the log's sha256); "(or a commit of its own)" dropped. Five runner tests |
| A-4-2 | `results.json` echoes the config verbatim, and the config holds `forbidden_result_substrings`, so the substring test could never pass | Applied, refuter's version: the echo is kept (`tests/test_digests.py` line 126 compares it), and the substring scan reads the exact text written with `provenance.config` removed (`forbidden_result_substrings_scope`); key-name rules and `banned_key_paths` still read the whole payload. The runner applies the checks before writing (7.4). Test cases: the full payload contains `player_id`; a `player_id` planted outside the echo is refused. Reviser's check (`audit-rev/check_results_contract.py`): the full payload holds both substrings, the scanned text neither, the planted one is caught, and the `test_digests` echo assertion holds |
| A-4-3 | As A-3-1, seen from the world and 7.5 | Applied with A-3-1, refuter's version: `season_world` takes `leagues` explicitly and asserts the league set; the replication passes `replication.leagues`; 7.5 adds `leagues` and `unexposed_leagues` to the criteria row and `leagues` to the resampling row, and keeps `exposed_leagues` in coverage only, with a refusal unless the two lists partition `leagues` |

### Majors

| Id | Finding | Disposition |
|---|---|---|
| A-1-2 | The pre-registration dismissal check stopped registration on any non-zero count, which data gaps make all but certain (pinned sidecar audit counts: England 41 card events against 39 sheet entries, France 86 against 87) | Applied with a variant. Split into an assumption test and residuals. The assumption holds when, in every league, at least `dismissal_assumption_minimum_share` (0.5) of players with a second-yellow event card have a sheet `red_minute`; otherwise `dismissal_check_fallback`, declared now, replaces the rule and the draft is re-audited. Residual mismatches are stated at registration and bounded by G1 only. Variant: a share, not the auditor's example of "more than one player in any league", because England's difference alone could already be two players from gaps; a sheet convention that drops second yellows gives a share near zero. The pinned counts are disclosed in the prior-exposure table |
| A-2-1 | The `context_only` sentence ("(a) to (d) and (f) false by definition") contradicted the criteria table, and the Holm paragraph said such a selection gives no p-value | Applied: (a), (b), (f), and (d) where mirror pairs exist, are false by computation; (c) and the rest are evaluated as defined; the p-value is the computed 1, written in the Holm paragraph, `holm` and `cluster_ratio`; a test with grid-selecting placebos |
| A-2-2 | The replication's frozen path had no gate, placebo or estimand rule, so built literally it applied G2, G4 to G6 and REPLICATED was unreachable | Applied with A-4-6: `evaluate_replication` with gates G1 and G3 from the `replication` minima only (`replication.gates`, `gate_rule`), P1 and M1 only (`estimands`, `estimand_rule`), no placebo, R1, V1, P2, T1 or I1; a test that a planted replication season reaches `REPLICATED` |
| A-2-3 | The `all_states` sensitivity could not be built from the frozen signatures | Applied: `sensitivity_rows` replaces the boolean; the `close_11v11` `kA` and `kD`, no re-selection, the same eligible rows (asserted), the shared world; R1 with the same split; a test |
| A-3-2 | Served sentences said the split "repeats across the two halves of the team's season", which reads as persistence in time; R1 interleaves the halves | Applied: the claim and every affected statement say "two halves of the team's matches that each hold one meeting with every opponent"; the protocol says T1, reported only, is the check in time, and lists in-season persistence as not shown. Copy guard clean |
| A-3-3 | As A-2-1 | Applied with A-2-1 |
| A-3-4 | The served composition must equal 4.2 but product code cannot import the engine, nothing tied the two, and the league pseudocount was neither a product constant nor a figure | Applied with a variant: a parity test in ROOT 2.7 X7's form (served `pi`, `delta_u`, `lam`, `rD_u` equal the engine's `state_at` to `1e-12`, a planted change fails it; it must pass before any panel is served), and `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` among the Opponent Lab constants tied to the config. The alternative, one product-side estimator imported by both, is left as a root choice |
| A-3-5 | Strings committed in `results.json` were frozen nowhere | Applied: `results_strings` (interpretation, uncertainty limit, product effect, identity-stress note, data licence, reuse disclosure), copied verbatim and asserted by the runner, read in 7.5, copy guard clean |
| A-3-6 | The S5 panel could carry a ratio's name over a share | Applied, option 1: the panel shows the share under its label with the share's badge; `s5_ratio_name` (ROOT H14-H21's name) is used in prose only (`s5_panel_rule`); no panel shows or labels the ratio |
| A-4-4 | The gate's frame negative control had no seed, size, effect or statistic in config, and the no-literal test forbade them in code | Applied: `synthetic_gate.frame_negative_control` holds the rule, seed, teams, side effect, statistic (team 0's side-balance coordinate minus the other teams' mean) and the pass rule; `synthetic_match_events`'s layout literals are exempt by name |
| A-4-5 | As A-3-5 | Applied with A-3-5 |
| A-4-6 | The replication status rule had no test and the frozen path was underspecified, with two `run_replication` signatures | Applied with A-2-2: one entry point `run_replication(config, tokens, frozen)`; `replication_status` and `test_replication_status_truth_table` over every reason and P1/M1 pattern, including a mirror descriptor with P1 at most `alpha` and M1 above it |

### Minors

| Id | Finding | Disposition |
|---|---|---|
| A-1-3 | Two StatsBomb edge cases were wrong or off the lattice | Applied: `80/120` is in the final third, as an exact rational also says; lateral cases on the `/80` scale at 0.1 resolution (26.6, 26.7, 53.3, 53.4); float64 and `Fraction` agree at every cut on both lattices (reviser's check `audit-rev/lattice_holm.py`) |
| A-1-4 | The protocol's S2 label and defensive-action phrase differed from the PIPELINE and vectors | Applied: the protocol's cells aligned; no payload moves |
| A-1-5 | The Wyscout y convention is already assumed by E-11, XI Lab and Match Lab | Applied in the Frames paragraph |
| A-1-6 | The prior-exposure table understated what was seen | Applied: Match Lab's served shot coordinates and passing-network nodes; E-11's public-side open-play-shot team-match count; the pinned sidecar card counts |
| A-1-7 | As A-2-1 | Applied with A-2-1 |
| A-1-8 | WP A interfaces under-specified | Applied: `match_state` returns `(state, incidents)` with named columns; `period_ends`; `match__` columns computed for every match; the oracle's extra inputs; `LevelSubject`; a team-match without a sheet row raises, and the runner refuses such a sidecar first |
| A-1-9 | "Both teams at eleven" says more than the window measures | Applied: "before any dismissal" in the window phrase, both scopes and the signal statement; the ten vector sentences regenerated (the independent generator rebuilds them byte for byte; payloads and fingerprints unchanged) |
| A-2-4 | B3 and B5 level rungs undefined; "both components for every rung" | Applied: `peers_level_rule`, `raw_persistence_level_rule` (smoothed toward the league rate, so no infinite deviance); level components for the level subject only |
| A-2-5 | The house bound took a confidence, not a critical value | Applied: `house_reliability_confidence`; a test ties it to `house_reliability_critical_value` |
| A-2-6 | The donor seed string was written two ways | Applied: one text in config and PIPELINE |
| A-2-7 | Cluster label format unfixed; "every interval and p-value" too broad | Applied: the house week label and part names; "bootstrap interval and bootstrap p-value" |
| A-2-8 | T1, I1, the implied ICC's `m` and `strength_validity`'s inputs under-specified | Applied with a part changed: I1 residualises the row's coordinates, primary only in both documents; `m` is the mean valid rows per qualifying team over both halves; `strength_validity` derives covariates from the rows, one generator per call. Changed part: T1 uses all valid rows of each part (`persistence_rule`), not eligible rows only, because T1 describes team values and eligibility is a forecasting condition that would drop each team's first matches |
| A-2-9 | The Holm test cited an example no frozen file held | Applied: two examples written into the test, one that separates the frozen reading from "m shrinks" and "None first" (reviser's check `audit-rev/lattice_holm.py`) |
| A-2-10 | `select_k` undefined on a non-finite loss | Applied: returns `None`; G6 or LG6 false; no further forward pass |
| A-2-11 | As A-3-5 | Applied with A-3-5 |
| A-3-7 | The proposal sentence said "did not pass" for untested records | Applied: keyed on `may_gate`; `proposal_sentence_not_tested` and `proposal_sentence_not_established` |
| A-3-8 | `FORECAST_NOT_SHOWN` holds a word the copy guard refuses when spelled as words | Applied: renamed `ADDED_INFORMATION_NOT_SHOWN` in both vocabularies, the precedence, outcomes, lifecycle status, prose and tests; every token spelled as words passes the guard |
| A-3-9 | Two level sentences said more than the test | Applied: "This check does not separate it from team strength."; "teams conceded" |
| A-3-10 | Replication statuses incompletely defined | Applied: `FAILED_RUN` replaces only a status that reached step 3; the level has no replication entry (`status_rule`) |
| A-3-11 | The level's figure pointer had no key to point at | Applied: the level's reliability has `split_half`'s shape with coordinate `log_rate` and `minimum_lower_bound`; the registry test builds the established tokens with figures (reviser's check: every checker of `tests/test_verdict_registry.py` passes, `figure_failures` included) |
| A-3-12 | As A-2-9 | Applied with A-2-9 |
| A-4-7 | `clock_invalid` cannot fire on the replication's files | Applied: it fires on neither provider and is kept as a guard; a malformed timestamp raises and is `FAILED_RUN`; a test |
| A-4-8 | `expected_matches` unused; `DATA_MISSING` and the valid-share denominator undefined | Applied: `inconclusive_reason_rules` |
| A-4-9 | No source for the StatsBomb `competition`; coach ids not loaded | Applied: the folder name; `home_coach_id`, `away_coach_id` in I4, coverage only |
| A-4-10 | The synthetic world's seed was ambiguous and its streams collided with the next season's | Applied: the world is `default_rng(season seed + seed_streams.season_world)`; `seed_stride_per_season` 10, per overdispersion 10,000, per scenario 100,000; `design_effect.seed` and the frame control's seed below the season range (reviser's check: 6,900 season seeds and their streams all distinct) |
| A-4-11 | The two-part generator law and the draw order were unstated | Applied: one-dimensional terms for S3 and S5; the loop order |
| A-4-12 | `WIDTH_ONLY` can pass (d) by chance | Applied in both documents |
| A-4-13 | Key order, "no path", the level's reliability shape and the LOCAL wording | Applied |
| A-4-14 | Canonical sort of sheet frames not unique | Applied: a stable sort on every read column |
| A-4-15 | As A-2-5 | Applied with A-2-5, with a variant: the confidence is the config key `house_reliability_confidence`, not a literal `0.90` in code, which `test_no_number_is_hard_coded` would refuse |
| A-4-16 | The replication's inputs were recorded nowhere | Applied: the local artifact records each folder's `folder_manifest` digest, never committed (ADR-0027) |
| A-4-17 | `source_hashes` omitted `domain/precision.py` and `domain/thesis.py`; the served pseudocount | Applied: both added; the pseudocount with A-3-4 |

Refuted claims: none.

### Checks run by the reviser (synthetic or data-free)

- The ten descriptor sentences rebuilt by the independent vector generator with the new window
  phrase equal the committed vectors byte for byte; the eight fingerprints recompute.
- The seven records built from the config are served by `finalize` under `PENDING` and every
  token with no refusal; a planted `line height` is refused; every token spelled as words, the
  scopes, statements, figure sentences, proposal sentences, `s5_ratio_name`, the
  `results_strings` and the vector sentences pass the copy guard.
- No key at any depth of `config.json` or `descriptor_test_vectors.json` names a provider or
  carries a banned key part.
- A synthetic `results.json` in the revised section 8 shape, with established tokens and their
  figures, passes every checker of `tests/test_verdict_registry.py`, and its size is within
  `results_maximum_bytes`.
- `pipeline_spec_sha256` recomputed after the last `PIPELINE.md` edit.
- `tests/test_licensing.py` passes and `scripts/check_licensing.py` is clean; the list entries
  for this folder's protocol and pipeline now name the replication's gates and statuses, the
  coordinate scale and the folder digests.

### For a root ruling

1. `output_root` is `data/licensed/research/E-10`, as E-11 does, so a PUBLIC experiment's
   results file is first written under the licensed tree and copied at the results commit. A
   PUBLIC location would need a `.gitignore` line in the registration commit.
2. The dismissal assumption threshold (`dismissal_assumption_minimum_share` 0.5) departs from
   the auditor's example; the count itself is the root's to run before registration.
3. The served computation is a second implementation of 4.2 tied by a parity test (X7's form);
   one product-side estimator imported by both is the alternative ROOT 4's "one object" rule
   might prefer.
4. The revision has not been audited. The E-11 precedent re-audited each revision before READY.

## 16 October 2026 — root rulings applied (ROOT 2.9 Z1 to Z3)

The root ruled on the four items above (ROOT-DECISIONS 2.9). The reviser applied the rulings
and nothing else; no file under `data/` was opened and no number was computed.

- **Z3 (one estimator).** The estimator of section 4.2, `state_at` and
  `LEAGUE_PRIOR_PSEUDOCOUNT_PER_PART` are now one product-side object,
  `galactico/features/team/estimator.py`, specified in `PIPELINE.md` 3.8 (owned by WP A, with
  `tests/test_team_estimator.py`): the walk-forward state (`PriorState`, `empty_state`,
  `add_rows`, `state_at`), the shape and level estimates, `unit_deviation`, `unit_level_ratio`,
  `predicted_shape`, `predicted_level`, `served_composition`, `served_volume`, and the row
  contract `descriptor_rows`, moved from the engine so that the engine and the panel read the
  same rows. Every argument the protocol fixes is passed by the caller with no default: the
  engine passes the config's `league_prior_pseudocount_per_part`, and the panel passes the
  module constant, which `test_estimator_constant_matches_the_config` ties to the config (3.7,
  7.5). The second implementation in the Opponent Lab module and its parity test are removed
  (12.3), together with `state_at` in the engine (4.3); the engine computes none of 4.2's state
  quantities itself (4.2, 4.3, `test_engine_reads_the_one_estimator`, review item 21). The
  estimator's `lf_sha256` is in `source_hashes` (7.3). The firewall keeps its direction: the
  research pipeline imports `galactico.features.team`, and no product module imports
  `galactico.validation` (section 0, the firewall test row of section 9). The hand-computed test
  of the state formulas and the own-match exclusion test moved to the estimator's tests; the
  engine's hand-computed test keeps the rung assembly. Protocol: one sentence under Models and
  baselines. The parity tolerance `1e-12`, a number that was in prose only, went with the test.
- **Z1 (output root).** Already in the draft (`output_root` `data/licensed/research/E-10`,
  every output and `replication.local_artifact` under it, `data/licensed/` ignored by git). The
  protocol's One execution paragraph and `PIPELINE.md` 7.1 now say also that it is one
  directory for both arms' files and that nothing under it is committed.
- **Z2 (dismissal pre-check).** Already in the draft (`dismissal_assumption_minimum_share` 0.5,
  `dismissal_check_fallback`). The protocol's Match validity paragraph, the
  `verified_by_root_before_registration` entry of `config.json` and the dismissal row of
  `PIPELINE.md` section 13 now each say that the root runs the structure-only count on the
  corpus before registration, that it computes no outcome, and that its counts and share per
  league are recorded in the registration commit; OPEN QUESTION 1 notes the ruling.
- **Z4.** Not an edit: the draft's banner says that neither the audit's revision nor these edits
  has been audited, and that ROOT 2.9 Z4 requires that audit before E-10 is called READY.

`pipeline_spec_sha256` was recomputed with `galactico.validation.digests.lf_sha256` after the
last `PIPELINE.md` edit. `descriptor_test_vectors.json` is unchanged; no payload or fingerprint
moved.

## 16 October 2026 — Second audit, and its revision

ROOT 2.9 Z4 required the audited revision to be audited again before E-10 is called READY. The
second audit read the draft as it then stood (the audit's revision and the edits for ROOT 2.9 Z1
to Z3) in the same four scopes, against ROOT-DECISIONS (2.9 included), the ADRs,
KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle and the registered E-11 protocol:
1 measurement, the estimator and prior exposure; 2 statistics and models; 3 claims, product
consequence and registry; 4 pipeline, runner and reproducibility. The one claimed blocker was
given to a refuter, who rebuilt it against the working tree, `HEAD` and `c8453fe` and on a
synthetic script; it was not refuted and came back with a corrected proposal, which is the one
applied. One reviser then verified every major and minor against the draft, the shipped code and
the rules and applied it, or applied a variant with the reason stated. No file under `data/` was
opened; every number below is synthetic, arithmetic, or a structure count already pinned in a
committed test.

The audit's ids are `Secondaudit16October2026-<scope>-<n>`, written here as `<scope>-<n>`; two
arrived with a typo in the prefix (`Secondaudit16OctoberOctober2026-2-7` and
`Secondaudit16OctOctober2026-4-8`) and are listed as 2-7 and 4-8.

Scope readiness as audited, by the rule of the first audit (a scope with a confirmed blocker is
not READY): scope 1 had no blocker and one major (READY); scope 2 no blocker and two majors
(READY); scope 3 no blocker and two majors (READY); scope 4 one confirmed blocker, 4-1, and two
majors (not READY). So not every scope was READY. After this revision every finding is applied,
but the revision itself has not been audited, and one question waits for a root ruling (below).

| Severity | Findings | Applied | Applied with a variant | Rejected | Refuted |
|---|---|---|---|---|---|
| blocker | 1 | 1 (the refuter's corrected proposal) | 0 | 0 | 0 |
| major | 7 | 7 | 2 (1-1, 3-2) | 0 | 0 |
| minor | 29 | 29 | 2 (3-4, 4-6) | 0 | 0 |

Duplicates, each listed under its own id: 1-1 = 2-2; 2-1 = 3-5; 1-6 = 4-8.

### Blocker

| Id | Finding | Disposition |
|---|---|---|
| 4-1 | A regression from A-4-11's edit since `c8453fe`: the frozen RNG order drew every team term, the defender shape included, before any match's goals, and each row's counts right after its match's goals. `measured_points` needs `f`, the finished season's points per match, which needs every fixture's goals, so a round-0 row's counts needed goals not yet drawn and `STRENGTH_MEASURED_0_15`, a gating scenario, could not be built as written; one `default_rng` per season forbids a second pass, and numpy's `multinomial` consumes a `p`-dependent amount of the stream, so a provisional pass would not reproduce the goals | Applied, refuter's version. This reopens A-4-11 (first audit), whose loop order it replaces. PIPELINE section 5: in every scenario, per league, the strength, then the goals of every fixture in schedule order (home, then away), then the team terms per subject (attacker shape; for the primary the defender shape's two normal components and the defender level), the `strength_shape` term added without a draw with `f` from latent strength or from the points per match of the goals already drawn (three for a win, one for a draw), then fixture by fixture the home and away rows (per subject shape noise, level noise, `N`, counts) and the row's `match__completed_passes`; `goals_for` and `goals_against` are the goals drawn first. The defender-shape row of the law table and `strength_shape_rules.measured_points` say the goals come first. A sentence under "What the reviser's simulation shows" says its table describes the generator law, not this frozen stream, and that the gate run of the implementers' code is the binding check. `test_generator_is_seeded_and_emits_the_table_schema` now asserts that two scenarios with one seed emit the same goals and that `STRENGTH_MEASURED_0_15` builds with `f` from its own goals. Reviser's check (`rev/rev_synthetic.py`, invented numbers): the order builds a measured-points season and two scenarios with one seed draw identical goals |

### Majors

| Id | Finding | Disposition |
|---|---|---|
| 1-1 | `test_engine_reads_the_one_estimator` monkeypatched `unit_deviation` to add a constant, which no shape quantity can see (it cancels in the normalisation and in `basis @ delta`); it never perturbed `shape_estimate`, `level_estimate` or `unit_level_ratio`, so a copied state formula passed | Applied with a variant: wider than proposed. With `b = log_ratio_basis(K)[0]`, one monkeypatch at a time, each asserted to move the named pooled quantity by more than `1e-6`: `unit_deviation` plus `b` (candidate loss, P2 inputs); `unit_level_ratio` times 2 (B2 deviance); `shape_estimate` returning its estimate with `context`, `nu`, `expected` or `expected_share` perturbed (B1 and B4, B1, candidate, P2 inputs); `level_estimate` with `rate_venue`, `context_ratio` or `unit_expected` doubled (B0, B1, B2). The variant adds the `expected`, `expected_share`, `nu`, `rate_venue` and `unit_expected` fields, because an engine that copied the `E` formula and passed its own `E` to the shared `unit_deviation` would have passed the proposed three. Reviser's check (`rev/rev_synthetic.py`): a constant moves the loss by 0.0; `b` on `delta`, on `A_c`, on `nu` and on `E` move it by 0.089 to 0.101 |
| 2-1 | `select_k`'s comment said "None if in the tie set" beside a return of `(None, losses)` for a non-finite loss, so a `context_only` selection could read as G6/LG6 false and `INCONCLUSIVE`; `calibration(selected: int)` could not tell that the index was `context_only` | Applied. `select_k` returns the int position of the selected candidate, the position of `None` when `context_only` is selected, and `None` as its first element only for a non-finite pooled loss; `evaluate_descriptor` and `evaluate_level` say a `context_only` selection leaves G6 and LG6 true; `calibration` takes `k_unit` (the selected value) and returns `None` when it is `None`; `test_selection_tie_set` asserts `(0, losses)` for candidates `(None, 25, 50, 100)` with losses `(1.0, 1.0 + 1e-13, 1.2, 1.3)` and G6/LG6 true |
| 2-2 | As 1-1 | Applied with 1-1 |
| 3-1 | The results commit left out the planning research sentence: once any E-10 record reads TESTED, `planning.verdict_reading()` returns `None` for it, and four test files assert the old sentence | Applied. Section 13's results commit now edits `galactico/api/planning.py` with `product_rules.planning_research_sentence` (the auditor's text, which passes the copy guard and `finalize`), following any sentence an earlier results commit wrote, and updates `tests/test_planning_api.py`, `tests/test_squad_api.py`, `tests/test_transfer_api.py`, `tests/test_planning_render.py` and the e2e specs; a planning test asserts the served sentence contains it; if every E-10 token is `INCONCLUSIVE` nothing changes. The registration row now says `REGISTERED_NOT_TESTED_STATEMENT` stays at registration, when nothing is tested |
| 3-2 | `results_strings.reuse_disclosure` said no channel composition was computed on this corpus before registration, which is false if E-11 runs first, and it cannot change after registration | Applied with a variant: "E-07 and E-08 scored a third of these evaluation rows for a conceded level of xT; before registration no descriptor of this protocol was computed by team on this corpus, except, if E-11 ran first, its per team-match counts on 36 double-coded matches, which the registration commit states." The variant says "descriptor of this protocol" and "per team-match counts" rather than "channel composition" and "entries by lateral third", because E-11 also computes box entries, defensive actions by third and S5's share per team-match, and Match Lab serves per-match wide pass-origin shares (1-4), which are not an E-10 descriptor. Copy guard and `finalize` pass. Section 13's E-11 row and OPEN QUESTION 2 say the registration commit states which case holds |
| 4-2 | G1 for the replication is valid over listed matches, but `evaluate_replication` received no listed count and `read_matches` returns only ids for absent matches, so code could compute valid over present (360 / 368 = 0.978 passes where 360 / 380 = 0.947 fails) | Applied. `load_sb_league` returns `listed_matches` (frame plus missing ids of `read_matches`); `evaluate_replication` takes `listed_matches: Mapping[str, int]`, forwarded to `sample_gates` in `audit_summary`; G1 is valid matches among the rows over `listed_matches[league]`; `gate_rule` says so; `test_absent_files_count_against_g1` uses the auditor's synthetic case |
| 4-3 | The serialise check required every `results_strings` entry at its key, but `identity_stress.note` is absent whenever a descriptor's gates fail, so an all-`INCONCLUSIVE` run (one league failing G1) could never write `results.json` | Applied. The five top-level and provenance strings must be present and equal; every `identity_stress.note` that exists must equal `identity_stress_note`, with no requirement that one exists (7.4 and the verbatim test); `test_every_subject_inconclusive_still_writes_results` |

### Minors

| Id | Finding | Disposition |
|---|---|---|
| 1-2 | The estimates carried no `team_ids`, so `served_composition(estimate, team_id)` could not map an id; `context` arguments were not said to be indices | Applied: `team_ids` on `ShapeEstimate` and `LevelEstimate`; `context` is an `int64` array of 0-based indices into `team_ids`; the served functions map an id through `team_ids` and raise for an unknown one; the hand-computed estimator test uses ids that are not `0..T-1` |
| 1-3 | The protocol's Z3 sentence ("and the level model's below") covered B5 and the peer grouping, which PIPELINE 4.2 keeps in the engine | Applied: the sentence lists the estimator's quantities (`pi` to `delta_u`; `lam_v`, `lam`, `rA_c`, `rA_c^(-u)`, `rD_u`, `rD_peers` from the peers' pooled `O` and `E`) and says B5, the peer grouping and every loss and deviance stay in the engine |
| 1-4 | The prior-exposure table missed served per-match wide and half-space pass-origin shares, most of the pinned sidecar `AUDIT` counts, and the E-07/E-08 xT surface fitted on Spain before 2017-11-01 | Applied: the Match Lab row names `width` and `half_space_share` and what the opponent's share is; the sidecar row lists the other pinned counts (goal tags, those on saves, own goals, shot totals by kind, corner starts and ends); a row for the xT surface. None is a team composition |
| 1-5 | The E-11 row said "Being built"; the Simulations row named only the 14 October scripts | Applied: "Built on synthetic data and its acceptance stamp committed (f6f9184); not run; no real value computed"; the Simulations row names the two audits' scripts of 16 October, uncommitted |
| 1-6 | The frame negative control's "basis row 1" read as a Python index is the width row, which the mirror leaves unchanged, so the control could never pass | Applied: "the first basis row, Python index 0 of `log_ratio_basis(3)`, `[s, 0, -s]`" in config and section 10, with the reason |
| 1-7 | "Calendar date (UTC)" does not describe StatsBomb's `match_date`, a local date | Applied: the provider's date as recorded (Wyscout `dateutc`; StatsBomb `match_date`), normalised to the day, in the protocol and in 4.1 |
| 2-3 | `season_label` became a criteria key read as the house bound's period, but neither `split_half` nor `level_split_half` received it | Applied: a keyword-only `period: str` on both, passed from `season_label`; I9 and 7.5 say so |
| 2-4 | `k` meant both the covariate count (noise floor, `R2_adj`) and `strength_top_k` | Applied: `q = len(strength_covariates)` in both documents (4/93 = 0.043 is unchanged) |
| 2-5 | 4.2 said every rung's shape but B0's comes from `predicted_shape`; B2's shape is `pi_v` | Applied: B0 and B2 read `pi_v` from `pi_venue`, B0 reads `lam_v`; `predicted_shape` gives B1, B3, B4, B6, B7 and the candidate, `predicted_level` B1, B2 and B3 |
| 2-6 | The level's V1 had no frozen function and no defined team value | Applied: `level_strength_validity`, team value `ln((sum y + s) / sum e)` over all valid rows, league-centred, its own fresh permutation generator, reported only, in both documents |
| 2-7 | "Placeholder" counts were defined nowhere | Applied: the word is deleted |
| 3-3 | The registration tests row missed `tests/test_shell_payloads.py::test_verdict_payload_is_the_registry_payload` (it asks for the level subject's id and expects `NOT_REGISTERED`) and listed an unaffected test | Applied: the first added with what it must assert; `test_payload_is_json_ready_and_carries_no_hash_or_pointer` named as needing no change |
| 3-4 | The served `INCONCLUSIVE` sentence ("a frozen sample gate failed. Nothing was compared.") misdescribed G6 and LG6, which follow a development selection | Applied with a variant: "E-10 could not test this descriptor: a frozen gate failed before any evaluation loss was aggregated. No evaluation result was compared." (and "this volume" for the level). The variant says "evaluation loss was aggregated" rather than "evaluation match was scored", because the forward pass that selects `kD` may already have scored evaluation rows when G6 is known; the protocol's own words are "before any evaluation loss is aggregated". The protocol's gate paragraph and verdict table say the same. Copy guard and `finalize` pass under every token |
| 3-5 | As 2-1 | Applied with 2-1 |
| 3-6 | The level shares E-07/E-08's kind of exposure, yet nothing reported it on the unexposed leagues | Applied: `level.l1.unexposed` (pooled L1 over `unexposed_leagues`, shared world, gating nothing) in the protocol, section 8, `evaluate_level` and the league-subset test; the prior-exposure row says the level shares the exposure and that (Lb) needs at least two of the three unexposed leagues below zero |
| 3-7 | Before registration the registry supplies no `non_claim` (`_unregistered` gives `""`), yet the panel prints it in every state | Applied, second option: Opponent Lab holds `registry_non_claims` as constants a test ties to the config and, once registered, to the record, and prints its group's sentence in every state |
| 3-8 | Nothing covered a proposal citing several records in different states | Applied, second option: one qualifier per cited record whose `may_gate` is false, beside its label, in `subject_groups` order, none merged or dropped (config rule, 12.3, protocol); the panel test covers a mixed citation. One qualifier per record keeps both "not tested" and "did not pass" visible, which a single weakest-record qualifier would not |
| 3-9 | "Prior league game ids" did not say whether invalid matches take world draws | Applied: the ids of the league's valid matches dated before `D`; the panel test plants an invalid match and a match on `D` |
| 3-10 | ROOT 2.5 O1 says a replication status "sits beside" a hosted panel as a label; E-10 creates no record for one, and ROOT 2.9 does not rule OPEN QUESTION 3 | Applied as far as a reviser can: a row in section 13's "Before registration" asks for the root ruling, or that the registration commit state the question open; OPEN QUESTION 3 says so. The ruling is the root's (below) |
| 4-4 | The level block had no absence rule, so an LG6 failure would serialise non-finite deviances | Applied: when `gates_passed` is false only `token`, `reasons` and `lifecycle_status` remain below it, for the level and, in the same words, for descriptors |
| 4-5 | The local artifact recorded every folder's `folder_manifest` digest, which raises on an absent folder, so `DATA_MISSING` became `FAILED_RUN`; it was written when only S4 or S5 reached the signal | Applied: digests for folders whose index exists, `null` otherwise; the artifact exists only when a comparable descriptor reached step 3; a test |
| 4-6 | Section 6 stops at the first failing check while the test's name said the listed count is checked before any read | Applied with a variant: section 6's order is `inconclusive_reasons` order, so stopping at the first failure already records the first reason that holds; the text says so, rather than evaluating every reason (an absent folder cannot be read). The test is renamed `test_data_missing_before_any_read_and_reasons_in_their_order` and a folder with an unknown pass type and a wrong count must give `VOCABULARY` |
| 4-7 | `run_replication` wrote the artifact itself (overwritten under `--verify`); a serialise failure left the artifact and replication log; "only exit-3 executions" was false; no rule for an exception during `--verify` | Applied: `run_replication` returns `ReplicationRun(statuses, artifact)` and writes nothing; every output is written by the runner in stage `serialise` after the checks, and an exception while writing removes all of them; `--verify` reads the first run's bytes and compares in memory; `failed_run_log` holds exit-3 executions and `--verify` failures; an exception in `--verify` outside the replication is a failed execution like a byte difference, the first run's outputs (the replication log included) are removed, and there is no second re-run. Three tests |
| 4-8 | As 1-6 | Applied with 1-6 |
| 4-9 | `synthetic_gate.json` held one design effect though it differs by overdispersion | Applied: `design_effect` keyed by overdispersion, and each run carries its own |
| 4-10 | `test_results_shape_is_strict_json_aggregate_and_small` could not run `run_real`'s load and tables stages on `synthetic_season`'s output | Applied: the injection is written out (stub frames, merged tables per window, an audit built from them, a fixed sidecar provenance, which frames are hashed) |
| 4-11 | "S4 and S5 written to the unit's `for__` columns" is wrong for S5's second part; `settings` was undefined | Applied: each secondary's columns named (S5's `against__own_60_pass` included); `settings` is the season configuration of `season_seed_rule`, and the keys `synthetic_season` reads are listed |
| 4-12 | "A failed gate is repaired ... before registration" cannot occur (the gate runs after registration), and the post-registration rule was open | Applied: code may be corrected where it departs from the frozen text, the section 11 review repeated for changed files and the stamp regenerated; no constant, scenario, requirement, threshold or rule changes; an unsound rule means a new experiment id |
| 4-13 | `read_events` builds one dict per event for every requested match; a whole league likely exceeds ROOT 4's ~1.5 GB | Applied: one folder at a time, `read_events` in batches of the new `replication.sb_events_batch_matches` (40), only the needed columns kept; a test that the frames do not depend on the batch size. The batch size is a resource constant in config because the no-literal test forbids it in code; no result depends on it |

Refuted claims: none.

### Checks run by the reviser (synthetic or data-free)

- `rev/rev_synthetic.py` (invented numbers): the revised draw order builds a measured-points
  season, and two scenarios with one seed draw the same goals; the 1-1 perturbations move the
  loss and a constant on `delta` does not.
- The seven records built from the config are served by `finalize` under `PENDING` and every
  token with no refusal (the audit's `registry_guard.py`); every `product_rules` string (the new
  `planning_research_sentence` included), every `results_strings` entry (the new
  `reuse_disclosure` included), every outcome statement and every non-claim pass the copy guard
  and `finalize` (`rev/checks.py`).
- No key at any depth of `config.json` or `descriptor_test_vectors.json` names a provider, starts
  with `SB_` or is refused by `banned_key_paths`; the eight fingerprints recompute from the
  payloads and equal the config. `descriptor_test_vectors.json` is unchanged.
- `pipeline_spec_sha256` recomputed with `galactico.validation.digests.lf_sha256` after the last
  `PIPELINE.md` edit.
- `tests/test_licensing.py` passes and `scripts/check_licensing.py` is clean; the list entries for
  this folder's protocol, pipeline and record now also name the date field, the batched reader
  and the second audit's findings.

### For a root ruling

1. ROOT 2.5 O1 and OPEN QUESTION 3: whether O1's "a second-provider replication status sits
   beside them as a label" is read as ADR-0018's permission, which E-10 does not use, or requires
   a LOCAL record of its own. Until it is ruled, the registration commit states it open
   (section 13).
2. ROOT 2.9 Z4 and the E-11 precedent: this third revision has not been audited. An audit that
   confirms no blocker is still needed before E-10 is called READY.
