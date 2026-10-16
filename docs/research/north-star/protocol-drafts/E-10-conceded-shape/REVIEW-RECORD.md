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

Not yet done: an independent audit that walks every branch of both verdict rules.
