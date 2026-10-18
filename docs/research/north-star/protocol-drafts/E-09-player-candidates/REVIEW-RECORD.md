# E-09 review record

What each round of review found in the E-09 draft and what was done with it. The draft
(`preregistration.md`, `config.json`, `PIPELINE.md`) is not registered and nothing in it has
been run. Every number below was computed on synthetic data or is arithmetic; no file under
`data/` was opened in any round.

## 14 October 2026 — first review, three lenses, and the revision

Three adversarial reviewers read the draft against ROOT-DECISIONS (R1 to R13, 2.2, 2.4, 2.5,
2.6, 3b), ADR-0001 to ADR-0029, KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle
and the registered E-11 protocol: a statistician (22 findings), a reader of the football data
(24) and a reader for the constitution (33). One reviser verified each finding against the
draft, the shipped code and the rules, and applied it or rejected it. Every finding held in
substance. All 79 are applied; three have a part rejected, with the reason in the table. Four
items the north-star README and the root had already named before registration are settled
in the same revision (last table).

| Severity | Findings | Applied | Rejected in full | Applied with a part rejected |
|---|---|---|---|---|
| blocker | 23 | 23 | 0 | 1 |
| major | 29 | 29 | 0 | 2 |
| minor | 27 | 27 | 0 | 0 |

Several findings are one defect seen by two or three lenses; each is listed under its own id.

### What the revision changed, in short

- **Rule inputs.** The baseline and nuisance statistics are the larger of the raw and the
  position-centred value over the audit set, so a near-copy within every position is caught
  and a pure position effect still is; the declared presence column holds no candidate's own
  rows; the reliability gate is the half-r bound with `n - 2 - g`, so a strongly negative
  half correlation rejects instead of going missing; E is the leagues `decide()` graded.
- **Self-check.** Four planted worlds (a new one plants a defensive candidate that is a fixed
  share of all defensive activity within every position), five instrument scenarios with the
  generator fully specified, and rates written as one predicate. The reviser simulated the
  exact generator, gauntlet, rule and instrument gates at event level, 40 replicates each:
  every predicate held (`selfcheck_feasibility`); the minimums were set from those rates.
- **Registry and product.** Two closed vocabularies with composite tokens, each with a
  frozen, digit-free statement and registry move consistent with rules V1 to V7; five PUBLIC
  records `PENDING` at registration; `product_admissible` held false by an empty promotion set
  the registration must add (ARCH D1); no requirement dimension in this release; the external
  leg is a label that gates nothing (ADR-0018).
- **Data.** The shipped sidecar API with version pins and shot-family pins; E-11's
  definitions of `shot_volume` and `opp_half_defensive_actions` imported unchanged, with its
  regulation minutes; the model domain is the opponent-half zone, sentinels excluded; the
  external box on the unit square.
- **Freezing.** `decide` pinned by its source hash and constants, not by its file;
  `PIPELINE.md` pinned by `pipeline_spec_sha256`; no key names a provider; the order of
  operations and every shared-file request of the registration commit (PIPELINE section 13).

### Statistics lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-statistics-1 | blocker | The planted NULL world required `shot_volume` UNRELIABLE, but the uncentred baseline made it REDUNDANT in every league, so the self-check could never pass | Applied. Baseline at the larger of raw and position-centred (R-statistics-4); presence column without candidate rows (R-statistics-2); NULL now expects any `NOT_ESTABLISHED_*` closure and never `ESTABLISHED_*`, with league assertions that keep its purpose (raw pooled reliability above 0.70 and centred bound below the band). Reviser's event-level run, 40 replicates: `shot_volume` `NOT_ESTABLISHED_REDUNDANT` 40 of 40; raw pooled reliability 0.913 to 0.948, centred bound at most 0.192 in 200 leagues |
| R-statistics-2 | blocker | `opp_half_on_ball_per_90` counted shot rows (and interception-flagged rows), so the candidate's own rows sat in its battery and EFFECT failed its rate | Applied. `opp_half_on_ball_rule`: passes and touches without the interception flag only. EFFECT, 40 replicates: every candidate `ESTABLISHED_NUMBER` 40 of 40; `shot_volume`'s closest baseline is now `mean_x` with gating correlation at most 0.541 |
| R-statistics-3 | blocker | NUISANCE's own unattributed-share gate made every league INCONCLUSIVE before the confound audit ran | Applied. Opponent-half rate 12 for everyone, team attribution 0 to 0.30, interception ratio 0.25: union share 0.115 to 0.125, nuisance R-squared 0.639 to 0.797, `NOT_ESTABLISHED_CONFOUNDED` 40 of 40; INCONCLUSIVE added to its never list; latent team share 0.72 against a bound of 0.65 |
| R-statistics-4 | blocker | Reliability was centred and the redundancy ceiling was not, so a within-position near-copy passed; 6.1's "can only make survival harder" was false | Applied. `baseline_centring` and `nuisance_centring`: the larger of raw and centred; new world `REDUNDANT_WITHIN_POSITION` (shared multiplier, log sd 0.6) expects `NOT_ESTABLISHED_REDUNDANT`: 40 of 40 (193 of 200 leagues REDUNDANT); 6.1 rewritten with a direction per departure |
| R-statistics-5 | blocker | E (evaluable leagues) was undefined, and the section 8 sentence let a degenerate league make the candidate INCONCLUSIVE | Applied. E = leagues whose status came from `decide()` (`evaluable_statuses`); guard and gate failures are outside E and count in neither s nor j; the sentence rewritten; the reviewer's two cases and the constitution lens's two are required truth-table cases |
| R-statistics-6 | blocker | No frozen vocabulary; section 10 could not be encoded as `VerdictRecord`s without breaking V6 or opening `product_admissible` against ARCH D1 | Applied. `verdict_vocabulary` (candidate and instrument), `registry_outcomes` with status, limits, statement and registry move (NONE for every ESTABLISHED token), `registry_*` sentences; `product_admissible` kept false by a promotion set, empty in this release, which the registration commit must add (an open question for the root names the alternative) |
| R-statistics-7 | blocker | A LOCAL external label could gate a hosted requirement dimension (ROOT O1) and a survivor was offered in this release (ARCH D1) | Applied. Every consequence rests on the PUBLIC token; no requirement dimension, planning number or player-row value in this release; the external token is a label beside a later promotion |
| R-statistics-8 | blocker | The pinned file hash of `experiments/run_replication.py` was stale (two commits since), so phase 1 would refuse to run | Applied. `frozen_rule_decide_source_sha256` (hash of `decide`'s source) and `frozen_rule_constants` gate; the file hash is recorded only; ADR-0026 and ADR-0027 named as having changed the file and not the rule |
| R-statistics-9 | major | Gate S mixed a count check with "every fit converged" and named no fits | Applied. S-count before the fits, S-fit after (`gate_s_fit_models`: MD and M1 in every fold); a non-converged challenger is not selectable and fails nothing; a non-converged calibration fit is None and fails its gate |
| R-statistics-10 | major | `min(house_low, half_low)` was undefined when the house interval is None, so a strongly negative half correlation gave INCONCLUSIVE | Applied. `reliability_low = half_low`; house interval reported only; `r_half = -0.4` and `-1/3` required to give REJECT, UNRELIABLE. Reviser's grid check: the half-r bound is never above the house bound (largest difference -2.3e-06 over 392,730 cells) |
| R-statistics-11 | major | The external rule left outcomes without a token, its mean shift had no estimator, and section 10 sent it to section 11 with no consequence | Applied. `sb_verdict_vocabulary` with `INSTRUMENT_NOT_ACCEPTED` first, then `INCONCLUSIVE`, `REPLICATED`, `NOT_REPLICATED`, `MIXED`; the shift defined exactly (`sb_level_shift_rule`) and reported only; consequence of every token: none |
| R-statistics-12 | major | The instrument scenarios' distance scale, lateral side, duel start_y and seed stream were unspecified, and the planted classification depended on them | Applied. `synthetic_instrument_distance_scale_m` 17, `synthetic_lateral_left_probability`, `synthetic_coordinate_decimals`, `synthetic_instrument_match_rule`, duel start rules, scenario stream `100 + scenario_position`. 40 replicates: PLANTED `ACCEPTED` 38, `ACCEPTED_WITHIN_LEAGUE` 2; NO_SIGNAL, TOO_SHARP (R5 failed in all), SLOPE_SHIFT (R3 failed in all) `NOT_ESTABLISHED` 40; LEVEL_SHIFT `ACCEPTED_WITHIN_LEAGUE` 39, `NOT_ESTABLISHED` 1 |
| R-statistics-13 | major | `PIPELINE.md` was not frozen with the protocol | Applied. `pipeline_spec_sha256`, verified in phase 1 and before registration |
| R-statistics-14 | major | Gating numbers and definitions lived only in prose | Applied. `context_limit_rule` and `context_limit_leagues` (an uncomputed estimate counts as not established), `synthetic_generator_sanity` with `generator_sanity_rules`, `irls_max_halvings`, `ece_weighting`, `mce_rule`, `interval_quantile_method`, `rank_ties`, `gate_r2_gain` (relative), `auroc_rule` (concatenated) |
| R-statistics-15 | major | "Every departure can only make survival harder" was false (goalkeeper exclusion is lenient; centring is not monotone), and its test could not pass | Applied. 6.1 states each departure's direction; goalkeeper exclusion, the identity column, the presence column and T23 are flagged lenient (`departures_active`); centring is "neither"; the test requires the stated direction and the flag |
| R-statistics-16 | major | The draft contradicted the registered E-11: same subject ids, other definitions, and a declared NOT_COMPARABLE where E-11 defines an estimator | Applied. `shot_volume` and `opp_half_defensive_actions` import E-11's definitions unchanged, regulation minutes included (`e11_definition`, `e11_config_sha256`, `minutes_rule`); the other two are "not graded" by E-11; the declared label is gone; a test ties the masks to E-11's flags |
| R-statistics-17 | major | The draft named `read_sidecar`, which does not exist | Applied. I1 against `verify`, `manifest`, `load`, `attach`, `provenance`; versions pinned; sidecar provenance in results |
| R-statistics-18 | minor | The Fisher-z standard error ignored the degrees of freedom spent by centring | Applied. `1/sqrt(n - 2 - g)` |
| R-statistics-19 | minor | No multiplicity policy, no power statement, two interval levels unexplained | Applied. Preregistration 4.4 and 9.2; `power_planning` (reviser's arithmetic: band or better with probability 0.011 at a true 0.55 and 0.948 at 0.65 with 300 players; 0.846 at 0.75 with 66) |
| R-statistics-20 | minor | Self-check rate semantics inconsistent (LEVEL_SHIFT, PLANTED, per subject or joint) | Applied. `selfcheck_predicate` per subject with `minimum_replicates_matching`, `never` and `also`; minimums set so each subject passes with at least 0.98 probability at (observed misses + 1) / 40; never lists hold only opposite classifications |
| R-statistics-21 | minor | Copy placeholders were per-league quantities with no fill rule | Applied. No served statement holds a placeholder; the Player Lab headline names a baseline by `baseline_fill_rule` through `baseline_prose`, with a tie headline, and a nuisance set by `nuisance_prose` |
| R-statistics-22 | minor | The external rule compared levels of `shot_location_value` that the instrument's scope forbids comparing | Applied. No token rests on a level shift, and none is computed for `shot_location_value` |

### Football-data lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-football-data-1 | blocker | The pinned runner digest was the file before two later commits; a function pin must also cover the module constants `decide` reads | Applied. Source hash of `decide` plus `frozen_rule_constants`; the literal 0.60 tied to `nuisance_r2_ceiling` by the truth table (`frozen_rule_nuisance_literal`); file hash recorded only |
| R-football-data-2 | blocker | The sidecar interface E-09 built against does not exist, and nothing pinned the sidecar's provenance | Applied. I1 rewritten; `sidecar_schema_version`, `sidecar_tag_mapping_version`, `sidecar_requires_actions_event_ids_equal`; `sidecar.provenance` in results; `shot_family_pins` with `expected_shot_family_disagreements` 0 |
| R-football-data-3 | blocker | The product gate was not reconciled with the shipped verdict registry | Applied with R-statistics-6 and R-constitution-3/4 |
| R-football-data-4 | blocker | The external penalty area was in raw provider units against a unit-square reader | Applied. `penalty_area_sb` {0.85, 0.225, 0.775}, E-11's quotients; lattice edge test |
| R-football-data-5 | blocker | The refitted instrument needed 5 of 5 leagues with only four available, and its failure had no external token | Applied. `sb_gate_leagues_required` 4, `sb_gate_s_count` with held-out minima; row 1 `INSTRUMENT_NOT_ACCEPTED` before any gauntlet statistic |
| R-football-data-6 | major | The model domain kept a (1,1) placeholder shot; the in-domain pins had two readings | Applied. Domain = zone `opponent_half` (no sentinel); `shot_frame` takes that mask; sentinel and behind-halfway shot counts pinned; the in-domain pins are recounted by the root before registration (null until then) |
| R-football-data-7 | major | The external leg's frames were unspecified where the providers differ | Applied in part. Frozen: position map and tie rule, period map, minutes rule (E-11 rule 2), battery rule, string `event_id`, `sb_root`, folder digests (La_Liga is E-11's; three counted by the root), forbidden roots, closed vocabularies. Rejected part: extending `sb_reader` with body part. Its hash is in E-11's committed acceptance stamp, and an edit before E-11's run would invalidate the stamp; `candidate_sb.py` reads body part and spell positions from the raw lists `sb_reader.iter_events` and the lineup files yield, and imports `sb_reader` unchanged |
| R-football-data-8 | major | The quantity separating the two shift labels was undefined | Applied. `sb_level_shift_rule` defines it exactly; it separates no token (R-constitution-13), so no boundary test is needed |
| R-football-data-9 | major | The declared NOT_COMPARABLE contradicted E-11, and E-09 never said whether it imports E-11's definitions | Applied. Label deleted; the leg does not run for `opp_half_defensive_actions`, whose cross-provider status is E-11's token; definitions imported; flagged clearance stated; masks tied to E-11's flags by a test |
| R-football-data-10 | major | ROOT 2.2's "non-penalty shots" was narrowed to open play with no DISSENT | Applied as DISSENT 6 with the evidence (E-11's registered `shot_volume`, the house baseline's identity, the origin and conversion of a direct free kick); display name "Open-play shots per 90 (no penalties, no direct free kicks)"; open question 6 for the root |
| R-football-data-11 | major | The degenerate guard did not say which vector it tests | Applied. `degenerate_vectors`: season over A and each match set over R, separately, the failing vector named; 0.50 / 0.5001 edge test |
| R-football-data-12 | major | No tie policy for the confound audit; a tied twelfth place undefined | Applied. `ties=rank_ties` ("average") passed explicitly; `top_k_kept` null with the two tied counts and `top_k_tied_statement`; never gates; permutation test |
| R-football-data-13 | major | A requirement dimension gated on a LOCAL label, and a survivor offered in this release | Applied (as R-statistics-7) |
| R-football-data-14 | minor | "Own-half shots" with four goals points to location anomalies | Applied. "Shot rows recorded at or behind the halfway line"; their location is not trusted; sentinel count pinned separately |
| R-football-data-15 | minor | C was called "metres from the centre line" | Applied. "lateral distance from the goal-to-goal axis" |
| R-football-data-16 | minor | "Half" named both periods and match sets | Applied. "match set 0 / 1"; `match_set_minutes_floor`, `share_floor_match_set_shots` |
| R-football-data-17 | minor | Display names did not follow ROOT H14 or the numerator | Applied. "Location-only conversion value of open-play shots per 90 (not provider xG)"; "Opponent-half ground defending duels and interception-flagged events per 90" |
| R-football-data-18 | minor | Battery column `defensive_actions_per_90` collided with E-11's subject of that name | Applied. `duel_or_interception_per_90` |
| R-football-data-19 | minor | The leakage sentence was false for winter movers | Applied. Section 4.2 |
| R-football-data-20 | minor | Stale code references | Applied. Split at `run_replication.py` lines 219 to 223; `lower_bound` returns NaN; `UNTESTED` at `profiles/build.py` line 111; Match Lab labels at line 153; I7 states E-11 defines its own inputs; per-league sidecar skip in the pins test |
| R-football-data-21 | minor | The runner bypassed `load_public` and did not pin the adapter | Applied. I6; `providers/pappalardo.py`, `storage/public.py` and `ingestion/sidecar.py` in `source_hashes` |
| R-football-data-22 | minor | Sentence grammar given only by examples; fingerprint of the house form differs | Applied. `describe_nouns` and the rules of section 3; a verdict attaches to the `CandidateSpec` fingerprint; a later `SPECS` entry carries a cross-reference |
| R-football-data-23 | minor | Local output path off convention; cited scripts not in the repository | Applied. `sb_output_root` `data/licensed/research/E-09-player-candidates`; the scripts are described as working notes not kept, and the pinned counts are recounted by a committed script |
| R-football-data-24 | minor | The share floor did not say which shots it counts | Applied. `share_floor_counts`: denominator rows |

### Constitution lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-constitution-1 | blocker | Any ESTABLISHED token would make `product_admissible` true, against ARCH D1; a survivor was offered "tonight" | Applied. Promotion-set change required at registration, test over every subject and token; the "tonight" rows and the requirement-dimension bullet deleted |
| R-constitution-2 | blocker | The LOCAL token gated hosted offers and registry exits; the "owner's pending decision" was already ADR-0018 | Applied. Every consequence is a function of PUBLIC tokens; ADR-0018 cited; the contingency removed |
| R-constitution-3 | blocker | The consequence table could not be encoded as `Outcome`s | Applied in part. Closed vocabularies with composite tokens, fixed digit-free statements, NONE for every ESTABLISHED token, the `UNTESTED` edit a declared hand edit tied by a test. Rejected part: LOCAL records for the external leg. A LOCAL record with E-09's directory makes `tests/test_verdict_registry.py::local_estimate_failures` refuse every float in E-09's PUBLIC `results.json` and require the logo in its `analysis.md`; the leg's token stays a label in its credited note (DISSENT 7) |
| R-constitution-4 | blocker | The assumed registry interface does not exist; records written after the run; no `results.json` contract | Applied. `registry_*` keys; PENDING records in the registration commit; top-level `experiment`, `version`, `tier`, `verdicts`; a data-free tie test is a shared-file request (tests outside the draft folder are the root's) |
| R-constitution-5 | blocker | "probability", "chance" and "pressing intensity" in fixed labels fail the copy guard | Applied. Measure "sum of location-only conversion value", fingerprint re-pinned `537cef62eb4e`; non-claims rewritten; every fixed label, statement and prose map checked with `scan_labels` and `runtime.finalize` (41 records under every token) |
| R-constitution-6 | blocker | Served headlines would hold digits and raw column keys | Applied. `player_lab_text` digit-free, baselines through `baseline_prose`; league ranges stay in `results.json` and `analysis.md` |
| R-constitution-7 | blocker | Stale frozen-rule hash | Applied (as R-statistics-8) |
| R-constitution-8 | blocker | Sidecar interface does not exist | Applied (as R-statistics-17); `sidecar.py` in `source_hashes` |
| R-constitution-9 | blocker | E undefined for a league made INCONCLUSIVE by the guard | Applied (as R-statistics-5); the two instances are truth-table cases |
| R-constitution-10 | blocker | A strongly negative half correlation gave INCONCLUSIVE | Applied (as R-statistics-10) |
| R-constitution-11 | major | Same subject ids as E-11 with other definitions; NOT_COMPARABLE with opposite meanings; I6 false | Applied (as R-statistics-16); I7 corrected |
| R-constitution-12 | major | External vocabulary open, "ROBUST" fails the copy guard, shift undefined, no LOCAL file | Applied in part. Closed copy-guard-safe vocabulary and sentences, shift defined, LOCAL file named. Rejected part: LOCAL records, for the reason given under R-constitution-3 |
| R-constitution-13 | major | A constant chosen between two StatsBomb-derived shifts would sit in a committed config, unrecorded in LICENSING | Applied by deletion. No token rests on a level shift, so no boundary is chosen and the two figures are no longer quoted; the protocol now prints no figure formed from StatsBomb data and moves to `NO_FIGURE_FORMED_FROM_STATSBOMB` |
| R-constitution-14 | major | Prior exposure incomplete; cited sources not auditable | Applied. Rows for E-11's box split, Match Lab's served shot coordinates and team-match counts, the sidecar build, Stage 1C; the working notes are declared not kept; the pinned counts are recounted by a committed script before registration |
| R-constitution-15 | major | The registration commit was not specified | Applied. PIPELINE section 13: banner and logo path, licence lists, PENDING records, verdicts docstring and promotion set, registry and draft tie tests, planning sentence, prose, firewall tuple in the pipeline commit |
| R-constitution-16 | major | `shot_volume` departs from ROOT 2.2 without DISSENT; display name not ROOT H14's | Applied. Name per H14; definition kept under DISSENT 6 |
| R-constitution-17 | major | Registry edits change frozen Player Lab output, and the draft said no verdict changes a test | Applied. ROOT 2.2's authority stated; the served outputs and tests that change named; ADR note requested; the false sentence corrected; references updated |
| R-constitution-18 | major | MIXED let a partly redundant `shot_location_value` stay research-only against ROOT 2.2 | Applied. Row 6 (`redundancy_closes_first`) |
| R-constitution-19 | major | Gate S evaluated before the fits yet required convergence | Applied (as R-statistics-9) |
| R-constitution-20 | major | No tie policy; equal-mass bins split tied predictions by event id | Applied. `rank_ties`; bins cut at value boundaries (`ece_binning_rule`); row-order and event-id invariance tested. Reviser's PLANTED runs: largest league ECE 0.0157 and MCE 0.0445 against 0.020 and 0.07 |
| R-constitution-21 | major | Self-check rates never checked at event level; order of registration and stamp unclear | Applied. Event-level feasibility of every world and scenario; the house order (audit, registration, pipeline, stamp, run) with the consequence of a failed stamp (supersession, ADR-0029) |
| R-constitution-22 | major | `pd.Series` passed to `split_half_reliability` returns NaN | Applied. `.to_dict()` keyed by player id, stated in sections 2 and 6, tested |
| R-constitution-23 | minor | "Centring can only lower r" false as a universal | Applied (as R-statistics-15) |
| R-constitution-24 | minor | One model id covered two specifications | Applied. `shot_location_v1/M1` or `/MFLEX` in results and on the card |
| R-constitution-25 | minor | The pinned commit was defined two ways; PIPELINE not hash-verified | Applied. The first-adding commit, as `VerdictRecord` defines it; `pipeline_spec_sha256` verified |
| R-constitution-26 | minor | `invalid_contexts` consequence had no target; None estimates uncounted | Applied. Context limits in `results.json` and the record's scope; `invalid_contexts` deferred to promotion; an uncomputed estimate counts as not established |
| R-constitution-27 | minor | A tie for the closest baseline was resolved silently | Applied. `closest_baselines` lists every tied column; the tie headline |
| R-constitution-28 | minor | Gates not mapped onto lifecycle stages; exploratory status unstated | Applied. Table 1.1 (construct validity: not tested); exploratory in the non-claim |
| R-constitution-29 | minor | The model-card template typed counts | Applied. Counts read from `results.json` |
| R-constitution-30 | minor | The `shot_location_value` requirement row lacked the same-league restriction | Applied. Section 11.3 (no dimension in this release; same-league only under `ACCEPTED_WITHIN_LEAGUE` for any later one) |
| R-constitution-31 | minor | LOCAL output root off convention | Applied (as R-football-data-23) |
| R-constitution-32 | minor | Config and PIPELINE disagreed on NULL's defensive expectation | Applied. Both read any `NOT_ESTABLISHED_*` closure |
| R-constitution-33 | minor | `shot_volume` defined twice, against ROOT 4 and Z3 | Applied. One `CandidateSpec`; a `ConstructSpec` form is generated at promotion, never written beside it |

### Items settled before this round

| Item | Disposition |
|---|---|
| 1. The pinned digest of `experiments/run_replication.py` (README, "Three things to settle") and how a tied twelfth place is reported | Applied (R-statistics-8, R-football-data-1, R-football-data-12) |
| 2. The logo path must resolve from the draft folder now and from `experiments/preregistered/E-09-player-candidates/` at registration | Applied. It resolves from the draft folder (`tests/test_licensing.py` checks every drawn logo); the registration-time path is recorded in PIPELINE section 0 |
| 3. Keys naming the local-tier provider carry an `sb` part and never contain the name | Applied. Every `external_*` key is now `sb_*` or `penalty_area_sb`; `key_naming`; no key of the config names a provider (checked) |
| 4. The draft names sidecar functions it does not have | Applied (R-statistics-17, R-football-data-2) |

The revision has not been audited. The house order requires an independent audit that walks
every branch of the verdict rules before E-09 is called READY.

## 18 October 2026 — Audit, and the audit's revision

An independent audit read the revised draft in four scopes against ROOT-DECISIONS (R1 to R13,
2.2, 2.4 to 2.9, 3b), ADR-0001 to ADR-0029, KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house
lifecycle and the registered E-11 protocol: A-1 measurement, frames and football data; A-2
statistics and the instrument; A-3 claims, product consequence and registry; A-4 pipeline,
runner and reproducibility. Every claimed blocker was given to a refuter, who rebuilt it on
synthetic numbers or on the shipped code; none was refuted, and every one came back with a
corrected proposal, which is the one applied. One reviser then verified every major and
minor against the draft, the shipped code and the rules and applied it, or applied a variant
with the reason stated. No file under `data/` was opened; every number below is synthetic or
arithmetic, a hash of code, or a structure count already disclosed.

Scope readiness as audited: none was READY. Each scope had at least one confirmed blocker
(A-1: A-1-1 to A-1-4; A-2: A-2-1; A-3: A-3-1 to A-3-3; A-4: A-4-1 to A-4-5). A-2's one blocker
is the runner defect the other three scopes also found; its auditor found no blocker in the
instrument rules themselves. After this revision every finding is applied, but the revision
has not itself been audited, and E-09 now waits for three root rulings before the next audit
(PIPELINE section 13).

| Severity | Findings | Applied | Applied with a variant or a part changed | Rejected | Refuted |
|---|---|---|---|---|---|
| blocker | 13 | 13 | 2 (A-4-1, A-4-5), each within its refuter's corrected proposal | 0 | 0 |
| major | 10 | 10 | 3 (A-2-2, A-4-7, A-4-9) | 0 | 0 |
| minor | 35 | 35 | 3 (A-1-13, A-2-9, A-2-11) | 0 | 0 |

Duplicates, each listed under its own id: A-1-1 = A-2-1 = A-3-1 = A-4-1 (the config echo
against phase 7); A-1-3 = A-4-5 (ROOT 2.2), with A-1-10 and A-4-18 on the same ruling row;
A-1-4 overlaps A-4-2 (where `run_selfcheck` lives); A-1-11 (c) = A-2-5; A-2-6 = A-3-13;
A-2-7 is part of A-1-6; A-3-14 overlaps A-4-17; A-4-8 overlaps A-4-3 (when `candidate_sb.py`
is built).

### Blockers

| Id | Finding | Disposition |
|---|---|---|
| A-1-1 | `results.json` echoes the config verbatim, and phase 7 refuses its 15 denylisted keys (`candidates[*].id`, `zones[*].name`, `synthetic_worlds[*].name`, `synthetic_instrument_scenarios[*].name`) and `rank_ties` (part `rank`), so no run could write a file | Applied, refuter's version. Keys renamed `candidate_id`, `zone`, `world`, `scenario`, `tie_policy` (the house term, `_TIE_POLICIES`; value `average` unchanged); prose references updated (preregistration 6 step 8, PIPELINE 2 and 6); the loader reads by the new keys (PIPELINE 3 and 8); phase 7 also stops on a provider-named key; 7.1 says the walk covers `provenance.config` with no exemption; the draft guard of PIPELINE 13 runs the three walks on `{"provenance": {"config": config}}` and on a 7.1 skeleton, and on planted copies (M-06). The fingerprints hash `candidate_id` values, not key names, so all four are unchanged. Reviser's check (scratch `audit-rev/full_check.py`): the three walks find nothing on the config echo, on a skeleton of the full 7.1 shape, on the stamp and on the LOCAL file shape, and find the planted `id`, `rank_ties` and `wyscout_x` |
| A-1-2 | `source_hashes` held `galactico/providers/pappalardo.py` as a key, against section 0's key rule and its own runner test | Applied, refuter's form (a): `source_hashes` is a list of `{"path", "lf_sha256"}` objects sorted by `path`, the `models/shots` glob expanded and sorted; the same form in the stamp and the LOCAL file; section 0's `candidate_sb.py` sentence reworded; three runner checks (no name at any depth; the adapter's path and true hash present; the list sorted with one entry per file) |
| A-1-3 | The shot candidates depart from ROOT 2.2's "non-penalty shots", the compliant design was one sentence, and registration did not wait for a ruling | Applied, refuter's version, in both branches: the ROOT 2.2 design is written in full in `root_2_2_design` (clauses, fingerprints `57ed7aea86d9` and `fcc26575bdf8`, or `18f3a5bb9e89` under the id `non_penalty_shot_volume`; sentences; display names; E-11's `non_penalty_shot_volume` imported and named as its label; the house open-play column out of the volume's battery as an identity-family column; the non-penalty volume in every other battery, so ROOT 2.2's redundancy test is against it; model domain, descriptive free-kick subgroup, box denominator kept on open play with its nuisance named, structure pins, leg shot types, traps and tests), and DISSENT 6 summarises it; the root's ruling on DISSENT 6 / OQ6 and the subject id is a condition of registration (`root_rulings_required_before_registration`, PIPELINE 13), recorded as a new ROOT section; OQ2 and DISSENT 5 stand unless ruled, "council" removed; DISSENT 2 and the E-11 duplicate are on the same row |
| A-1-4 | `candidate_gauntlet.py` must use `_safe_abs_corr` but may not import `experiments`, and no signature carried the helper | Applied, refuter's version: `Correlation` type; `correlation` beside `rule` in `evaluate_league`, `run_gauntlet` and `run_external` (which also gains `rule`); `run_selfcheck` moved to the runner (option (a)); the reuse row "injected, never copied"; `frozen_correlation_function` and `frozen_correlation_source_sha256` (`f19c0a86...`, recomputed from the shipped source), verified by the root, gating in phase 1, recorded in `provenance.frozen_rule`; tests (spy, no other Pearson in the module, T24 and the pure position effect with the house helper); checklist item 4. The import alternative is rejected: `pyproject.toml` packages only `galactico` |
| A-2-1 | As A-1-1, seen from the instrument verdict that could never be written | Applied with A-1-1. The precedent sentence is corrected: E-11 passed the denylist walk and called `banned_key_paths` without `parts`; E-09 keeps the stricter call by choice |
| A-3-1 | As A-1-1, seen from the registry tokens that could never reach the records | Applied with A-1-1; the echo is kept (`tests/test_digests.py` compares it) and nothing is exempted |
| A-3-2 | An established candidate fell out of every served count and list: proposed 9 and tested 8 where the protocol said 13 and 12, in 2,800 of 4,096 token assignments | Applied, refuter's version. Registry move stays NONE (V6 unchanged); `tested_not_promoted_edit` writes `TESTED_NOT_PROMOTED` in `profiles/build.py` whatever the tokens; frozen digit-free `player_lab_text.ESTABLISHED_NUMBER` and `ESTABLISHED_BAND`; the consumers named in 11.1 (Player Lab route and counts, the docs generator's counts and table, `renderWhy`, the fixtures and the five tests, the disjointness test that keeps the new list out of `assert all(...)`); section 10's table and its "and nothing else" sentence widened; counts restated for every token class (`player_lab_counts_after_run`). Reviser's check: over all 4,096 assignments proposed is 13 and tested 13 minus the untested ids |
| A-3-3 | The frozen model card printed tag audit counts that no output holds | Applied, refuter's deletion option: item 4 names the excluded tags (the counter-attack tag added) and the enforcing check; `structure`, `sidecar_columns`, I1 and the hashes unchanged. Adding a `tags` column is rejected: `frame_digest` cannot hash a list column, and accuracy and blocked counts per league would be avoidable exposure |
| A-4-1 | As A-1-1, with the determinism and schema tests that could not pass | Applied with A-1-1, with a variant inside the refuter's options: the key names are A-1-1's and A-3-1's (`candidate_id`, `zone`, `world`, `scenario`, `tie_policy`), not this refuter's `candidate`, `key` and `tie_method`, which would also pass; `candidate_id` matches the `CandidateSpec` field and `tie_policy` the house term. The subtree exemption is rejected (thesis `allow` does not cover keys beneath a path) |
| A-4-2 | `run_selfcheck` had to run the pipeline from a module that may import none of it | Applied, refuter's preferred option: `run_selfcheck` and the league assertions move to `experiments/run_candidate_gauntlet.py`; `candidate_synthetic.py` keeps the generators and `generator_sanity`, under an `ast` scan written as the house firewall scan (whole tree, `import_module` and `__import__` with a string); 8.4 calls it from the runner |
| A-4-3 | The external leg's frames could not compute the battery, so its REDUNDANT branch and token were fixed in advance; the box zone, team-sheet arguments and spell minutes were missing | Applied, refuter's version: `sb_event_row_rule`, `sb_kind_type_map`, `sb_frame_columns_rule` (success, goal, counter-attack, E-11's interception family, body part, shot family, renamed ids, string event ids, sentinels counted), `sb_frame_refusal` for a shots-only or pass-less frame; `penalty_area_sb` as the third entry of `zones` with its fingerprint and phrase, read only by the leg-only `sb_box_spec` (fingerprint `23bf9214db9b`); `sb_goalkeeper_position`, `sb_dismissal_card_types_exclude` and `sb_spell_end_reason_contains` copied from E-11; goalkeepers the GK group; spell minutes from `sb_reader._spell` under a pin (Z3); the five tests. The shipped `StatsBombProvider` mapping is not used |
| A-4-4 | On the leg, an unconverged selected `MFLEX` was judged anyway | Applied, refuter's version: one rule, `gate_s_fit_rule` checks `gate_s_fit_models` and the instrument, evaluated in `instrument_report` where the instrument is known; identical on the public run; text in preregistration 4.4 and 11 and PIPELINE 5 and 10; the two tests |
| A-4-5 | As A-1-3 | Applied with A-1-3, with a variant: this refuter preferred the ROOT 2.2 design as the primary text. It is written in full (part A) and the ruling row is added (part B), as required, but the open-play design stays the primary text, because the reviser's event-level feasibility of the self-check was simulated on it; if the ruling selects the ROOT 2.2 design, that simulation is repeated on it and the revision is audited again. Nothing can be frozen against the root, since registration waits for the ruling |

### Majors

| Id | Finding | Disposition |
|---|---|---|
| A-1-5 | `CLAIMS` was "text of section 5", whose negative-control bullet fails the copy guard | Applied: `candidates[*].claim` holds construct, observable implication, negative control and incremental claim; `CLAIMS` is built from it by a stated mapping; the "Algebra says ... prediction" sentence moved to the section 12 reason (`predictions`); the draft guard scans the claims. Reviser's check: every claim passes `scan_labels` |
| A-2-2 | The symbol test had no word list and, read plainly, refused the required `predict` and `predict_probability` and the required docstring | Applied with a variant: renamed `conversion_values` and `logistic_values`; the test defined (identifiers the package defines, split on `_` and case, against the one-word `BANNED_LABEL_TOKENS` and `xg`; docstrings, comments and library attributes such as `reset_index` not read). The variant: the reviser found that `fit` is also a banned token, so `fit_logistic`, `LogisticFit` and `fit_shot_model` became `estimate_logistic`, `LogisticEstimate` and `estimate_shot_model`; the required names were checked against the list |
| A-3-4 | Row 2 gave `NOT_ESTABLISHED` to a candidate of which nothing was computed | Applied: token `INCONCLUSIVE_INSTRUMENT` (status INCONCLUSIVE, move NONE, untested edit, reason `INSTRUMENT_NOT_ACCEPTED`), its statement, the 9.1 definitions, DISSENT 5, section 10 and 11.1 |
| A-3-5 | The REDUNDANT language called two new battery columns "a statistic the project already has", and section 14 assumed shot weighting | Applied: "a declared baseline statistic" in the statement, the detail and `headline_tied`; section 14 has one sentence for `shot_location_value` closed against `shot_volume` and one for every other closure (`interpretation_language`) |
| A-3-6 | The served planning sentences after the run were not frozen | Applied: `planning_after_run` freezes the research sentence and two `shots` entries (tested or untested), copy-guard clean and digit-free, with their rules; `planning.py` and the four planning test files are in 11.1 |
| A-3-7 | A listed candidate was served under an id-derived label, not its H14 display name | Applied: `display_name_edit` (`DISPLAY_NAMES` in `profiles/build.py`, served by `/api/constructs`), covered by the copy-guard test |
| A-4-6 | The self-check stamp was tied to nothing | Applied: `--selfcheck` writes `selfcheck.json` with `passed` and the three hashes; phase 1 refuses an untracked, failed or stale stamp; phase 3 must reproduce its block; `selfcheck_hash` in provenance; checklist item 17; runner tests |
| A-4-7 | A failed execution after outcomes were computed had no rule | Applied with a variant: E-11's failed-execution rule (record without the message, exit 3, written files removed, repair limited to the failing phase, re-review and re-stamp, disclosure in `analysis.md` before the next start, a phase-1 refusal otherwise); the variant is where the log lives: `run_output_root` = `data/public/research/E-09-player-candidates`, gitignored by `data/public/*`, a public location for a PUBLIC experiment (E-10 used the licensed tree and asked the root) |
| A-4-8 | The external leg had no build, pin, review or run lifecycle | Applied: `candidate_sb.py` built and pinned in the pipeline commit; it and `sb_reader.py` in `source_hashes`; the LOCAL file's keys and provenance; `--external` refusals, overwrite refusal, determinism re-run, output-root check, failed-run log; checklist item 18 |
| A-4-9 | The runner tests could not pass phases 1 and 2 on a synthetic corpus | Applied with a variant: the seam is `evaluate` (phases 4 to 6) and `serialise` (phase 7), with `verify` and `run_selfcheck` separate; a test may override `selfcheck_replicates` only, in `run_selfcheck`. The variant: phase 3 is outside `evaluate`, because a smoke override of the replicate count cannot meet the predicate's minimums |

### Minors

| Id | Finding | Disposition |
|---|---|---|
| A-1-6 | The two out-of-domain sets overlapped, and most structural pins were not recounted | Applied: behind-halfway counts non-sentinel rows only; `structure_identity` asserted in phase 2; every pin, coverage, overlap and family disagreement in `counted_by_root_before_registration`, with `counted_by_root_rule` |
| A-1-7 | Match Lab's prior exposure was understated | Applied: per player-match and per team-match counts of shots and tagged interceptions (verified in `match_lab/model.py`) |
| A-1-8 | `MetricEvaluation.exploratory` is never built | Applied: the sentence now rests on the non-claim and `interpretation_limits` |
| A-1-9 | A disjointness test was falsified by the results commit | Applied: disjoint from `SPECS` and `CONSTRUCTS` only; list membership tied to the token |
| A-1-10 | DISSENT 2 and the E-11 duplicate were not in the root ruling | Applied: both on the ruling row; DISSENT 2 states the duplicate |
| A-1-11 | Split wording, display name, prose-only planning figures | Applied: "parity of a match's position among sorted game ids"; "from the opponent half" in the display name; `planning_figures` with their bases, and the opening rule names the three kinds of figure allowed in prose |
| A-1-12 | `describe` and `Zone.fingerprint` underspecified | Applied: `Zone.fingerprint` read from config; zone-less unions worded without a comma; `describe_refusals` |
| A-1-13 | The disclosure of the opponent-half quantiles did not say what they informed | Applied with a variant: the eligibility and share-set sizes set `power_planning` and the share floor's reach, every sample gate sits below them, and `degenerate_sd` is the helper's tolerance; for `maximum_zero_share` the record of the design pass does not show what informed it, so it is disclosed as frozen after the quantiles were seen, and its zero shares are reported, rather than asserted not to be set from them |
| A-1-14 | Manifest entries, a draft config pointer, LICENSING.md | Applied: `raw_manifest_entries` (events.zip, matches.zip, players.json); the draft config is deleted at registration; the LICENSING.md sentence is a section 13 request (outside the draft folder) |
| A-2-3 | Positions, ECE cuts and `n_matches` underspecified | Applied: `position_indexing` (0-based; LEVEL_SHIFT's 2 is Italy), the cut formula, `n_matches` from the held-out in-domain shot frame |
| A-2-4 | L3 is not purely a level statistic | Applied, reword option: the two instrument statements and 4.4 say "level or calibration across value bins"; no gate moves, so no rate changes |
| A-2-5 | Prose-only figures, one understated | Applied with A-1-11: `planning_figures`; R3's planning spread corrected to about 0.05 |
| A-2-6 | The card typed numbers | Applied: season from config; the literature range in words |
| A-2-7 | Body-part coverage not recounted | Applied with A-1-6 |
| A-2-8 | INCONCLUSIVE paths underspecified | Applied: `instrument_inconclusive_rule` (null fields, `["S_count"]` or `["S_fit"]`, reasons, precedence), "not fitted" on the card, tests |
| A-2-9 | `predict` can return exactly 0 or 1 | Applied in part: a stable logistic that may return 0.0 or 1.0, clipped where a logit or log is taken; no test asserts the open interval. The optional rule (a fit with an exact 0 or 1 is not converged) is not adopted: it changes which TOO_SHARP folds converge, and the simulated rates were taken without it |
| A-2-10 | The scenario generator was not fully written | Applied: `synthetic_shot_coordinate_rule`, `synthetic_logit_median_rule`, `synthetic_instrument_frame_rule` |
| A-2-11 | The gap-matrix edit called the instrument xG under every token | Applied with a variant: under `ACCEPTED` and `ACCEPTED_WITHIN_LEAGUE` only, a note beside the xG / xA row naming a location-only conversion model and no provider xG; the cell is not relabelled; section 10 states the exception |
| A-3-8 | Established statements ignored a redundant league | Applied: "and, in those leagues, not a near-copy"; `analysis.md` names the league |
| A-3-9 | An established token could carry an empty scope | Applied, second option: context limits are reported beside the claim and do not narrow it; the scope sentence and section 10 changed |
| A-3-10 | "Neither" and the flags overlapped | Applied: "neither" is either direction; `position_centred_reliability` is flagged, T22 and the minutes rule are not, with the reason |
| A-3-11 | Section 6 underspecified | Applied: `Status.name`; the `LeagueResult` construction; `np.column_stack`; uncomputed leagues `INCONCLUSIVE` with `league_not_computed_reasons`; "all four instrument tokens" |
| A-3-12 | `half_low` can underflow to NaN | Applied, qualify option: the sentence names the 1e-12 band where the guard makes the league INCONCLUSIVE |
| A-3-13 | As A-2-6 | Applied with A-2-6 |
| A-3-14 | Loose later-use licences | Applied: the licensing tokens named; the follow-up's criterion frozen in its own protocol; a label only from a LOCAL record (Z5) |
| A-3-15 | An established E-09 record still serves `may_gate` true | Applied: the `verdicts.py` docstring amendment and a route test in the registration commit. Reviser's check: `derive` gives `may_gate` true for established candidate records |
| A-4-10 | Predictions and interpretation limits had no config source | Applied: `predictions`, `predictions_matched_rule`, `interpretation_limits`; the team clause moved into the reason |
| A-4-11 | Two leg sentences false in reachable branches | Applied: both reworded, copy-guard clean |
| A-4-12 | Hash and run discipline gaps | Applied: `raw_file_sha256` in 7.1; `thesis.py`, `providers/base.py`, `domain/provenance.py` pinned; all three protocol files first added in `<sha>`, an ancestor of `HEAD`; BLAS and machine recorded; the re-run's comparison file and the card's output path named |
| A-4-13 | The level shift's public input unobtainable | Applied: `LeagueEvaluation.mean` over A wherever the count gates passed; the shift null when any of the eight means is null; `Mapping[str, float \| None]` |
| A-4-14 | Byte for byte against the counted pins | Applied: the root writes the counted keys into the draft, the only post-audit edits, then registers byte for byte |
| A-4-15 | Joint pass probability unstated, the adjustment window empty, the smoke assertion undefined | Applied, raise-the-margins option: minimums 9 of 12 and 8 of 12 for `PLANTED`'s `also`, joint 0.9941 against 0.9296 at the conservative rates (scratch `audit-rev/joint.py`; never lists unchanged and not bounded by this arithmetic); the window applies to the reviser's simulation only; `selfcheck_smoke_rule` |
| A-4-16 | The `sb_reader` pin could not fail once an edit is committed | Applied: the test compares with E-11's `acceptance.json` entry, which equals the file's `lf_sha256` today (`ce0bc5cb...`, `sb_reader_source_sha256_in_e11_acceptance`) |
| A-4-17 | Label permission and licence lists against Z5 | Applied: Z5's wording in section 10 and DISSENT 7; `sb_report` and `analysis.md` list rules in section 11 and PIPELINE 13 |
| A-4-18 | Council questions had no step | Applied with A-1-3: on the ruling row; frozen values stand unless ruled |

Refuted claims: none.

### Checks run by the reviser (synthetic or data-free)

Scratch scripts under the session scratchpad, `E-09-review/audit-rev/`:

- `full_check.py`: a reference implementation of PIPELINE 3 recomputes the four fingerprints
  and sentences from the config's clauses, the three of `root_2_2_design` (and
  `18f3a5bb9e89` under the id `non_penalty_shot_volume`) and the leg's box spec, all equal;
  the five records built from the config are served by `runtime.finalize` under `PENDING`
  and every token (41 records); the Player Lab counts hold over all 4,096 assignments; the
  denylist, `banned_key_paths(..., parts=BANNED_KEY_PARTS)` and provider-name walks find
  nothing on the config echo, a skeleton of the full 7.1 shape, the stamp and the LOCAL
  file shape, and find planted keys.
- `keys_and_copy.py`: every display name, sentence, claim, statement, Player Lab text,
  prose map, planning sentence, leg sentence, interpretation sentence and token spelled as
  words passes `scan_labels` (three statements failed it on "overall" and "fit" in a first
  draft and were reworded); no served statement holds a digit.
- `fp_rev.py`, `joint.py`: the fingerprints and the self-check pass probabilities above.
- The `decide` and `_safe_abs_corr` source hashes and the `sb_reader` and E-11 config hashes
  recomputed from the tracked files.
- `pipeline_spec_sha256` recomputed after the last `PIPELINE.md` edit.
- `tests/test_licensing.py` passes and `scripts/check_licensing.py` is clean; the list
  entries for this folder's three files now name the leg's frame rules, refusals and pinned
  reader hash.

### For a root ruling (PIPELINE section 13; E-09 is not registered without the first three)

1. OPEN QUESTION 1, ARCH D1 against `product_admissible`: the empty promotion set, or another
   form.
2. DISSENT 6 and OPEN QUESTION 6: open-play shots (the primary text) or ROOT 2.2's
   non-penalty shots (`root_2_2_design`), and under the second the subject id
   (`shot_volume`, ROOT 2.2's, or `non_penalty_shot_volume`, E-11's). The reviser then moves
   the selected design into the main keys and deletes the other.
3. DISSENT 2 and the E-11 duplicate: `CandidateSpec` against ROOT 3b's "candidate
   ConstructSpecs", and a second implementation of E-11's two definitions tied by a parity
   test, which Z3 refused for E-10 and which cannot be removed while E-11's code is pinned.
4. Optional (frozen values stand): OPEN QUESTION 2 (R1 thresholds) and DISSENT 5 (two tiers).
5. Product edits the results commit makes under any token: `TESTED_NOT_PROMOTED` and
   `DISPLAY_NAMES` in Player Lab, the frozen planning sentences, and the gap-matrix note under
   an accepted instrument; each overrides R13 and ADR-0011 for named output and needs the
   root's ADR note.
6. `run_output_root` for the failed-run log and the re-run file is
   `data/public/research/E-09-player-candidates` (gitignored, public tier), where E-10 used
   the licensed tree.
7. The draft guard checks of PIPELINE 13 (key walks, copy guard, records, pipeline hash) can
   be added to `tests/test_protocol_drafts.py` now, as E-11's were; that file is the root's.
8. The revision has not been audited. After the rulings, the house order audits it again
   (ROOT 2.9 Z4).

## 18 October 2026 — The root's rulings applied (ROOT-DECISIONS 2.10)

The root ruled W1 to W10 on the audit's revision (ROOT-DECISIONS 2.10). This revision applies
W1 to W9 and nothing else, and no question in the draft waits for a root ruling. By W10 it is
audited again before E-09 is called READY. No file under `data/` was opened and nothing here
is an outcome.

| Ruling | Applied where |
|---|---|
| W1 (OPEN QUESTION 1): an explicit, empty promotion set for `product_admissible` | preregistration 10 (a `product_admissible` column in the product-consequence table; the paragraph names the form); PIPELINE 11.1 (at registration, and the `ESTABLISHED_*` row), 11.2 row 15, 13 (the rulings row and the `verdicts.py` row); OPEN QUESTION 1 closed. The config already held `promotion_set_in_this_release` `[]` and `product_admissible_in_this_release` false |
| W2 (DISSENT 6, OPEN QUESTION 6): open-play shots | `root_2_2_design` deleted from `config.json`; preregistration 1 and 15 lose the alternative; PIPELINE 6 (`departures_active` loses `identity_family_column`) and 13; DISSENT 6 and OPEN QUESTION 6 closed. The open-play keys and fingerprints, and the feasibility simulated on them, are unchanged. The design not chosen is summarised below |
| W3 (DISSENT 2): `CandidateSpec`; the tie to E-11 exhaustive | PIPELINE 3: the E-11 tie test now imports `galactico.validation.provider_inputs` and asserts equal masks on every row type, subtype and flag combination of the public adapter's closed vocabulary, with the frame's row count asserted; PIPELINE 7.2: `provider_inputs.py` in `source_hashes` (its `lf_sha256` today, `94844119...`, equals its entry in E-11's `acceptance.json`); PIPELINE 2 and 13; DISSENT 2 closed; preregistration 5 and 15 |
| W4 (DISSENT 3) | DISSENT 3 closed; PIPELINE 11.2 row 14 |
| W5 (DISSENT 5, OPEN QUESTION 2) | both closed; frozen values unchanged |
| W6 (DISSENT 7) | DISSENT 7 closed; preregistration 11 cites W6 |
| W7 | PIPELINE 7 (failed executions): the log under `run_output_root`, gitignored by `data/public/*` (checked with `git check-ignore`, which reads `.gitignore` only) |
| W8 | preregistration 10, PIPELINE 11.1 and 13: the results commit carries an ADR naming the post-run product edits, overriding R13 and ADR-0011 for exactly those edits, as ADR-0025 and ADR-0027 did |
| W9 | `tests/test_protocol_drafts.py` gains the E-09 draft guard: the pinned pipeline hash; the five records under `PENDING` and every token through `runtime.finalize`; the served texts through `labels.scan_labels`, digit-free where required; the denylist, banned-key (with parts) and provider-name walks over the config echo and over a skeleton of every key PIPELINE 7.1 and the section 6 dataclasses name. Each check also runs on a planted copy and finds the defect. PIPELINE 13's row says the guard is in place |
| W10 | the DRAFT banner and PIPELINE 13: this revision is audited again |

Also changed: the config keys `root_rulings_required_before_registration` and
`root_rulings_optional_frozen_values_stand` are replaced by `root_rulings_applied` and
`root_rulings_rule`; the DRAFT banner no longer says registration waits for a ruling; and
`pipeline_spec_sha256` is recomputed with `lf_sha256` after the last `PIPELINE.md` edit
(`51ab5d5c...`). The other pinned hashes (`e11_config_sha256`, the `decide` and
`_safe_abs_corr` source hashes, the `sb_reader` hash) were recomputed from the tracked files
and are unchanged. `tests/test_protocol_drafts.py` and `tests/test_licensing.py` pass, and
`scripts/check_licensing.py` is clean.

For the next audit, not changed here because it lies outside this folder: ROOT 2.2's
parenthesis for `shot_location_value` still reads "non-penalty shots per 90". W2 amended
only `shot_volume`'s parenthesis, although it removes the non-penalty design for both shot
candidates.

### The design not chosen (W2)

`root_2_2_design`, removed from `config.json`. The full block is in commit 8e4f4cf. Both
shot candidates counted open-play and direct free-kick shots, through a second clause
(`set_piece` with subtype `free_kick_shot`). The fingerprints were `57ed7aea86d9` for
`shot_volume` (`18f3a5bb9e89` under the id `non_penalty_shot_volume`) and `fcc26575bdf8` for
`shot_location_value`. `shot_volume` imported E-11's `non_penalty_shot_volume` definition,
whose record would have been its label. The house open-play `shots_per_90` left its battery
as an identity-family column, lenient and flagged. The non-penalty volume joined every other
battery, so ROOT 2.2's redundancy test was against it. The model domain became non-penalty
shots in the opponent half, location-only, with a descriptive direct free-kick subgroup.
`box_shot_share` stayed on open-play shots, with the open-play column as its nuisance. Two
structure pins (free-kick shot rows and their goals) joined the root's count. The leg read
the Open Play and Free Kick shot types for the two shot candidates, and the planted trap and
the tests changed to match. Its self-check feasibility was never simulated.

## Second audit, 18 October 2026

An independent audit read the revision that applies ROOT 2.10 W1 to W9 (commit c74c676), as W10
requires, in four scopes against ROOT-DECISIONS (all of it, 2.10 included), ADR-0001 to
ADR-0029, KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle and the registered E-11
protocol: 1, measurement, frames and football data; 2, statistics and the instrument; 3,
claims, product consequence and registry; 4, pipeline, runner, reproducibility and the
external leg. Every claimed blocker went to a refuter, who rebuilt it on the shipped code or on
synthetic numbers; neither was refuted, and each came back with a corrected proposal, which is
the one applied. One reviser verified every major and minor against the draft, the shipped
code and the rules, and applied it or applied a variant with the reason stated. No file under
`data/` was opened; every number below is synthetic, arithmetic or a hash of code.

Scope readiness as audited: scopes 2 and 3 had no blocker and were READY; scope 1 (finding
1-1) and scope 4 (finding 4-1) were not. After this revision every finding is applied, but the
revision has not itself been audited, and by W10 it is audited again before E-09 is called
READY. One step waits for the root (below).

| Severity | Findings | Applied | Applied with a variant | Rejected | Refuted |
|---|---|---|---|---|---|
| blocker | 2 | 2, each as its refuter's corrected proposal | 0 | 0 | 0 |
| major | 10 | 10 | 0 | 0 | 0 |
| minor | 25 | 25 | 2 (1-7, 3-3) | 0 | 0 |

Duplicates, each listed under its own id: 1-2 = 4-1 (ROOT 2.2's `shot_location_value`
parenthesis); 1-3 = 2-5 = 4-3 (the assumption pins of the root's recount); 2-6 is part of 4-2
(the leg's position index). Ids are written without the audit prefix
`Secondaudit18October2026-`.

### Blockers

| Id | Finding | Disposition |
|---|---|---|
| 1-1 | `galactico/features/candidates.py` is a product module (`features` is in the firewall's `PRODUCT` tuple), yet the draft had it build `ZONES`, `SENTINEL_STARTS`, `CANDIDATES`, `CLAIMS` and the describe nouns from the experiment's `config.json` when imported: product code reading research, against ROOT 3b, and a read that fails outside a checkout (`pyproject.toml` packages only `galactico`); the firewall parses imports only and would not catch it, and the zone-fingerprint test compared the config with itself | Applied, refuter's corrected proposal (E-10 PIPELINE 3.7). PIPELINE 3: the three `Zone` records, `SENTINEL_STARTS`, `DESCRIBE_NOUNS`, the four `CandidateSpec`s and the `CLAIMS` texts are module literals written once; the module opens no file and names no experiment path; it holds no display name (the results commit's `DISPLAY_NAMES` stay in `profiles/build.py`, now tied to the registered config by a test, 11.1). The code-block comments read "literal; equals config ... (test)"; the `loading` row is replaced by a `literals` row that keeps "never formatted from the bounds" and "a config key `id` or `name` anywhere is a defect"; the `CLAIMS` and `Clause.noun` rows name the tie. `tests/test_candidates.py` gains the config tie (zones with bounds, fingerprint strings and phrases; sentinels; describe nouns; per candidate the clauses, measure, scaling, denominator, instrument, family, evidence class and every claim field), so the fingerprint, sentence and zone-fingerprint tests compare two sources; and the no-file scan, written as the firewall's and run on the real file and on a planted copy: imports from an allowlist checked with the firewall's own `imports()`, no call whose terminal name is `open`, `load` or `loads` or starts with `read_`, no string constant but the docstring holding `experiments` or `config.json`. PIPELINE 0 says WP-A holds constants tied by test, WP-B receives parameters and WP-C to F read the config; checklist item 3 names the tie and the scan; preregistration 5 no longer says the claim record "is built from the config". A-1-12's "`Zone.fingerprint` read from config" of the first audit is superseded |
| 4-1 | ROOT 2.2 still defines `shot_location_value` as conversion-model-weighted non-penalty shots; W2's text amended only `shot_volume`'s parenthesis; DISSENT 6 and OPEN QUESTION 6 were closed for `shot_volume` only, and the draft said no question waits for the root, so the protocol would be registered against the letter of a binding root rule | Applied, refuter's corrected proposal. PIPELINE 13 gains a "Root amendment" row before the audit: the root amends ROOT 2.2's `shot_location_value` parenthesis to match the config (location-only conversion-model-weighted open-play shots starting in the opponent half per 90, no penalties, no direct free kicks; amended by 2.10 W2), or records in 2.10 that W2 covers both shot candidates, and E-09 is not registered while 2.2 says non-penalty shots for it; the registration commit's prose rows list ROOT 2.2 beside ROOT 2.6 in case the amendment has not been made before; the order of operations names the step. New config key `root_amendment_before_registration`; `root_rulings_rule`, the PIPELINE 13 rulings row and the DRAFT banner qualify "no question waits for a root ruling" with this one exception. DISSENT 6 is retitled for both shot candidates and says W2 ruled the design for `shot_location_value` by removing `root_2_2_design`, while its text amended only the first parenthesis; OPEN QUESTION 6 and preregistration 1 say the same ("the three shot candidates", 1-2). No fingerprint, numerator or other value changes, since the design does not. The partial amendment was the root's edit of 8e4f4cf; c74c676 closed DISSENT 6 and OPEN QUESTION 6 without routing the second parenthesis to the root. This closes the "For the next audit" note of the previous section |

### Majors

| Id | Finding | Disposition |
|---|---|---|
| 1-2 | As 4-1, from preregistration 1; "both shot candidates" is ambiguous beside `box_shot_share` | Applied with 4-1; preregistration 1 says "the three shot candidates" and how W2 rules each |
| 1-3 | The recount rule replaced every differing pin, including two the frozen text depends on: body-part coverage 1.0 (`shot_frame` raises on a null body part, so a replaced pin gives a pipeline that can never yield an instrument verdict) and clause overlap 0 (preregistration 5.4 states the clauses do not overlap) | Applied with 4-3 and 2-5: `counted_by_root_assumption_pins` (body-part coverage, clause overlap, shot-family disagreements) and `counted_by_root_assumption_rule`: counted by the same script and never written; a count that departs stops registration, and the draft returns to a revision that freezes a rule for those rows, then to an audit. `counted_by_root_rule` now covers the other keys only. Preregistration 3, PIPELINE 0, 4 (`shot_frame`) and 13 ("Structure counts") say so. The alternative, freezing a treatment for a shot with no body part now, is not taken: no count shows such a shot exists, and ADR-0028 reports none with two |
| 2-1 | Written literally, the IRLS halves a Newton step whose log-likelihood changes only at the last bit, then stops on the halved step, so the frozen gradient test fails on some seeds and the permutation test depends on summation order | Applied. PIPELINE 4: the log-likelihood is `sum(y * eta - logaddexp(0, eta))`; the stop is judged on the full Newton step, which is then taken unhalved; a step is halved only when the log-likelihood falls by more than `irls_halving_relative_tolerance` (new key, 1e-12) times its absolute value; when the halvings run out the fit stops non-converged at the iterate before the step. The gradient test is kept (below 1e-6) and joined by one on the scale the stop controls (one more unhalved Newton step moves no standardised coefficient by more than `irls_tolerance`) and by a planted last-bit step; the permutation test runs through `shot_frame`'s `event_id` sort (byte-identical) or, on design rows passed directly, within 1e-9; the calibration fits take the same key. Reviser's check (scratch `irls.py`, `irls_flex.py`, synthetic shots from the 8.3 generator): as written, 5 of 60 `M1` fits and 2 of 40 `MFLEX` fits ended with a gradient above 1e-6 (worst 5.3e-6 and 9.9e-6); under the revised rule the worst was 2.4e-11 and 2.9e-11, every fit converged, a permutation moved no coefficient by more than 4.3e-15, and the separable toy still returns `converged=False` with finite coefficients. Coefficients agree to about 1e-9 either way, so no simulated self-check rate moves |
| 2-2 | Pooled over the five leave-one-league-out folds, the observed-over-expected ratio of a subgroup that is a model term is 1 by construction, so R4's footed and head-or-body conditions cannot fail for an instrument with an intercept and an `H` term, and the stated planning standard errors described no statistic of R4 | Applied, second option: R4 is kept as frozen; preregistration 4.4 gains "What R4 can see" (the footed and head-or-body ratios are 1 up to second-order terms on any data, between-league differences cancel in the distance bands as well, R4 checks only a misfit of functional form shared by all leagues; a league-specific misfit is R3's and L1 to L3's business), PIPELINE 5 and the model card's item 8 say the same, and `planning_figures.r4_subgroup_o_e_se_range` is replaced by `r4_subgroup_o_e_sd_synthetic_planted` with `r4_basis` (the audit's simulated spreads). The first option, R4 per held-out league relative to that league's level, is not taken: it changes a gate after the self-check feasibility was simulated and would need that simulation repeated. Reviser's check (scratch `r4.py`, `PLANTED`, `M1`, 12 replicates): footed sd 0.0001, head-or-body 0.0004, distance bands 0.009, 0.010 and 0.037 |
| 3-1 | The frozen texts gave opposite instructions for the planning `shots` entry when no E-09 record reads TESTED: the protocol and `research_sentence_rule` left planning untouched, while `shots_entry_rule` and PIPELINE 11.1 replaced the entry under every token | Applied: preregistration 10 says the `shots` entry is replaced after the run whatever the tokens, and the research sentence is written only once a record reads TESTED; `research_sentence_rule` ends "while no E-09 record reads TESTED the research sentence is not written"; the PIPELINE 11.1 row says "whether or not any E-09 record reads TESTED". Reviser's enumeration: 16 of the 16,384 assignments of the four instrument tokens and the shot and defensive candidate tokens have no record reading TESTED |
| 3-2 | Both ESTABLISHED statements ended "it is not promoted and is not shown beside players in this release", which a later promotion would make false while the registered statement cannot change | Applied: both now end "This experiment itself promotes nothing: a statistic is shown beside players only after a separate promotion with its own decision record." The proposal's "E-09 itself ..." failed the draft guard, which keeps registry statements digit-free, so the experiment is named in words. "In this release" stays only in texts a later commit can edit (Player Lab texts, planning sentences); preregistration 10 says why |
| 4-2 | The leg reuses the public functions, but which config values they read on four folders was not written: `league_position` indexed `leagues`, and the 5-of-5 league gates and `minimum_evaluable_leagues` were left to the implementer, so a forgotten substitution gives `INSTRUMENT_NOT_ACCEPTED` every time with every listed test passing | Applied: `sb_leg_config_rule` and `sb_leg_config(config)` write out the leg's view (`leagues` becomes `sb_folders`, so `league_position` is the index in `sb_folders` for `bootstrap_rule` and the null-ECE seed; `gate_s_count` becomes `sb_gate_s_count`; the R1, R3 and L league counts become `sb_gate_leagues_required`; `minimum_evaluable_leagues` becomes `sb_minimum_evaluable_leagues`; `context_limit_rule` and every pooled statistic count over four folders; nothing else changes); `position_indexing` and PIPELINE 5's resampling and null-ECE rows name the leg's index (2-6); `tests/test_candidate_sb.py` asserts the view differs in exactly those keys and that four synthetic `PLANTED` folders give an accepted refit that lets `shot_location_value` reach leg rows 3 to 5, while one folder failing R1 gives `INSTRUMENT_NOT_ACCEPTED` |
| 4-3 | As 1-3, from the runner: phase 2 stops on a missing body part and on a shot-family disagreement whatever the pin says, so a replaced pin registers a protocol whose phase 2 always stops | Applied with 1-3 |
| 4-4 | `--external` refused unless `sb_results_file` did not exist, while `--external --determinism-rerun` must compare against it, so the leg's re-run was always refused; its file name was a literal outside the config | Applied: the refusal is written per mode (the plain leg needs `sb_results_file` absent; the re-run needs it present and the re-run file absent; every other refusal holds in both); new key `sb_determinism_rerun_file`; both modes in the leg's refusal test |
| 4-5 | The leg re-implemented E-11's open-play shot and interception flags on the second provider, outside W3's recorded exception and against Z3, although `candidate_sb.py` is research code and may import `provider_inputs` | Applied, first option: the kept shots and the `interception` flag come from `provider_inputs._statsbomb_flags(rows, e11_config, "open_play")`, imported as a private member as `sb_reader._spell` is, under the existing pins (`provider_inputs.py` in `source_hashes`; E-11's config checked against `e11_config_sha256`, a new leg refusal); `sb_flags_rule`; `sb_event_row_rule` and `sb_frame_columns_rule` cite it; `sb_open_play_shot_types`, `sb_interception_kinds` and `sb_interception_pass_types` restate E-11's keys and are asserted equal; `sb_frames` and `run_external` take `e11_config`; a spy test. DISSENT 2 states both providers' sides: the one recorded duplicate is on the public provider, and the leg has none |

### Minors

| Id | Finding | Disposition |
|---|---|---|
| 1-4 | `PER_90` computed `(c * 90) / m` and `compute_baselines` `c * (90 / m)`, which differ in the last bit in about a quarter of integer cases, so a plain "equals" test fails | Applied, second option: `PER_90` is `numerator * (90.0 / minutes.replace(0, nan))`, the house expression, and the tie is exact (PIPELINE 3, preregistration 15). Reviser's check (scratch `check.py`): the revised expression equals `compute_baselines` bit for bit on 400 synthetic players; the earlier one differed for 88 |
| 1-5 | The W3 tie asserted the input's row count only, while `harmonise_wyscout` drops unlinked or out-of-period rows silently and sorts; the alignment key was not named | Applied: the harmonised frame has as many rows as the input, its `event_order` is a permutation of `range(n)`, and rows are compared aligned on `event_order` |
| 1-6 | "Imported unchanged" is false for E-11's unit rule, which drops a player-match with no regulation minute, while E-09's season sum keeps its rows | Applied: preregistration 1 and 3 ("Known and uncorrected") disclose it; the optional count is taken as two reported structure fields, `shot_rows_without_regulation_minutes` and `union_rows_without_regulation_minutes` (PIPELINE 7.1), never gating |
| 1-7 | The 0.25 of `ConfoundFinding.damaging` appeared only in prose, outside the three permitted kinds of figure; section 6 step 3's 1e-12 likewise | Applied with a variant: the threshold is cited by name, and the opening rule gains a fourth kind (constants of shipped code, cited by the code that holds them); the 1e-12 is not permitted but removed, step 3 now saying "so close to -1 that the transform underflows to NaN in floating point" |
| 1-8 | The instrument's verdict is exploratory too, but its non-claim did not say so | Applied: `registry_instrument.non_claim` ends "The data were seen before the protocol was written, so the result is exploratory."; preregistration 1 says every record's non-claim carries it |
| 2-3 | What a non-converged estimate holds was unspecified; a NaN would make phase 7 refuse the file and turn a recorded non-convergence into a failed execution | Applied: a non-converged estimate keeps its last iterate (finite), `standard_errors` is `None` when `X'WX` is singular there (both dataclasses typed so), and any statistic that is not finite is `None`; tests for a singular challenger and for a synthetic corpus with `M1` singular in one fold serialised to `INCONCLUSIVE` / `S_FIT` with no NaN |
| 2-4 | `instrument_report` needed a `str` instrument on an S-count failure, where none exists | Applied: `instrument: str \| None`, `None` returning the null block |
| 2-5 | As 1-3 | Applied with 1-3 |
| 2-6 | The leg's bootstrap and null-ECE seed index was undefined | Applied with 4-2 |
| 2-7 | The model card called AUROC "for comparability only" although R5 gates on it | Applied: "gated by R5 only as a leak check; not a skill criterion" |
| 3-3 | `shots_entry_tested` fired when only the instrument read TESTED, yet said shot statistics were tested | Applied with a variant: a third sentence, `shots_entry_instrument_only`, and `shots_entry_rule` in three branches; and `shots_entry_tested` no longer says the conversion model was tested, since it also fires when the instrument is `INCONCLUSIVE` and a shot candidate is tested, the converse case. Over the 16,384 assignments: tested 16,128, instrument only 192, untested 64 |
| 3-4 | The CONFOUNDED texts said "a declared nuisance variable", while `box_shot_share`'s gated R-squared is joint over two columns | Applied: the statement and the Player Lab detail say the declared nuisance variables "taken together" |
| 3-5 | The volume sentence covered the whole corpus though row 6 fires on one league; "instrument not accepted" was not tied to a token | Applied: the sentence is limited to the leagues where the frozen rule closed it; `instrument_not_accepted_rule` limits the sentence to `NOT_ESTABLISHED` (an `INCONCLUSIVE` instrument uses its registry statement) and says the league code covers both |
| 3-6 | The badge "E-09 · TESTED · SURVIVES" clashes with Player Lab's "surviving" count, which an established, unpromoted candidate never enters | Applied: `claim_token` `REPEATABLE` (passes the copy guard) |
| 3-7 | `house_replication_label` was typed `str` against a tuple-returning function; the team-and-position centring cells and the precedence of the two not-computed reasons were unstated | Applied: `classify_replication(...)[0].value`; `team_and_position_centring` (cells of `player_team` and position); `league_not_computed_precedence` (the instrument reason first, as rows 1 and 2 precede row 3) |
| 3-8 | The shared scope did not mention the share floor; "holds no digit" was false for the not-run statement | Applied: the scope adds the share candidate's shot counts; preregistration 10 says outcome statements are digit-free and the not-run statement and non-claims hold no digit but the experiment id's, as V7 words it |
| 3-9 | The model card had no rule for items 5, 7 and 8 under S-count | Applied: items 7 and 8 print "not fitted"; item 5 reads goals and shots by held-out league from `sample_gate.folds`, filled under every token |
| 4-6 | The LOCAL candidate block carried public-rule fields with no value on the leg, `sb_verdict` returned only a string, and `--external` with no established leg candidate was undefined | Applied: `sb_verdict` returns (row, token); the block holds `sb_token`, `sb_rule_row` and `sb_sentence` and the leg's counts, without `token` or `rule_row`; `candidate_verdict` is not called on the leg; `--external` refuses when no leg candidate is `ESTABLISHED_*` |
| 4-7 | The self-check block could not show whether a `failing_gate` condition held | Applied: `with_<gate>_failed` per scenario with a `failing_gate`, defined as the count the predicate compares |
| 4-8 | "Expected about 70 KB" understated the results file; the config echo alone is about 68 KB | Applied: about 250 KB, under the 512 KB of `results_maximum_bytes` and `scripts/check_licensing.py` |
| 4-9 | Preregistration 15 could be read as counting a failed execution against R5's single run | Applied: a failed execution counts against neither R5's run nor its re-run |
| 4-10 | After a repair of `sb_reader.py` under E-11's failed-execution rule, the leg is refused for good and its test fails for good, with nothing said | Applied: a "pin after registration" row (no leg, no label, `analysis.md` says so, not a failed execution of E-09); the test asserts the refusal in that case |
| 4-11 | "lognormal(0, s) with unit mean" contradicts itself | Applied: every multiplier is `exp(N(-s^2/2, s))`, of unit mean, so the position mean is the mean rate. The reading used by the 14 October feasibility script is not recorded; the binding check is the pipeline's own self-check on the frozen generator |
| 4-12 | Preflight was said to run before the protocol commit, when no runner exists | Applied: after the pipeline commit; `preflight(config)` takes no protocol commit; the root's pre-registration counts use their own script |
| 4-13 | The failure-log test needed a seam that section 7 did not name | Applied, first option: `guarded(step, *, config, log)` holds the failure-log, removal and exit-3 logic and is tested directly with synthetic steps; `run` returns its code |

Refuted claims: none.

### Checks run by the reviser (synthetic or data-free)

Scratch scripts under the session scratchpad, `E-09-Second-audit-18-October-2026/`:

- `irls.py`, `irls_flex.py`: the IRLS of PIPELINE 4 as written and as revised, on synthetic
  shots drawn as 8.3 draws them (numbers under 2-1).
- `r4.py`: pooled out-of-league ratios by R4 subgroup under `PLANTED` (numbers under 2-2).
- `check.py`: the five fingerprints recomputed from the config's clauses, all unchanged; every
  sentence the revision touched or added passes `scan_labels`, and the registry statements and
  Player Lab texts hold no digit; no config key is refused by the denylist, the banned-part
  walk or the provider-name rule; the planning `shots` entry over every token assignment; the
  `PER_90` equality.
- `config_edits.py`: the config edits, applied as exact text replacements and parsed as JSON.
- `pipeline_spec_sha256` recomputed with `lf_sha256` after the last `PIPELINE.md` edit
  (`1c036517...`); `tests/test_protocol_drafts.py`, `tests/test_licensing.py`,
  `tests/test_verdict_registry.py`, `tests/test_research_firewall.py` and
  `tests/test_preregistration_order.py` pass, and `scripts/check_licensing.py` is clean. The
  `tests/test_licensing.py` entries of this folder's `PIPELINE.md` and `REVIEW-RECORD.md` now
  name the leg's imported flag code, its config view and its refusal modes.

### For the root (PIPELINE section 13)

1. Before the registration commit: amend ROOT 2.2's `shot_location_value` parenthesis to match
   the config, or record in 2.10 that W2 covers both shot candidates
   (`root_amendment_before_registration`). E-09 is not registered before then. This is a text
   of ROOT-DECISIONS, which only the root edits; no design question is open.
2. The revision has not been audited. By W10 it is audited again before E-09 is called READY.

## Third audit, 18 October 2026

An independent audit read the second audit's revision (commit 58be68b, the commit in which the
root also extended ROOT 2.10 W2 to `shot_location_value` and amended ROOT 2.2's parenthesis for
it), as W10 requires, in the same four scopes, against ROOT-DECISIONS (all of it, 2.10
included), ADR-0001 to ADR-0029, KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle
and the registered E-11 protocol: 1, measurement, frames and football data; 2, statistics and
the instrument; 3, claims, product consequence and registry; 4, pipeline, runner,
reproducibility and the external leg. It claimed no blocker, so no refuter was called. One
reviser verified every major and minor against the draft, the shipped code
(`galactico/providers/pappalardo.py`, `galactico/validation/provider_inputs.py`,
`galactico/domain/verdicts.py`, `galactico/domain/labels.py`, `experiments/run_replication.py`)
and the rules, reran the auditors' synthetic scripts, and applied each finding, or applied a
variant with the reason stated. No file under `data/` was opened; every number below is
synthetic, arithmetic or a hash of code.

The audit's ids are `Thirdaudit18October2026-<scope>-<n>`, written here as `<scope>-<n>`; one
arrived with a typo in the prefix (`Thirdaudit18OctoberE2026-1-4`) and is listed as 1-4.

Scope readiness as audited, by the rule of the first audit (a scope with a confirmed blocker is
not READY): scope 1 had no blocker and one major (1-1; READY); scope 2 no blocker and one major
(2-1; READY); scope 3 no blocker and one major (3-1; READY); scope 4 no blocker and three majors
(4-1, 4-2, 4-3; READY). So every scope was READY as audited. After this revision every finding
is applied, but the revision itself has not been audited: by W10 and the E-10 precedent (its
"Verification of the fourth revision"), an audit of this revision, or a verification of its
edits, that confirms no blocker is needed before E-09 is called READY.

| Severity | Findings | Applied | Applied with a variant | Rejected | Refuted |
|---|---|---|---|---|---|
| blocker | 0 | 0 | 0 | 0 | 0 |
| major | 6 | 6 | 0 | 0 | 0 |
| minor | 22 | 22 | 3 (3-2, 3-7, 4-6) | 0 | 0 |

Duplicates, each listed under its own id: 1-1 = 2-5 = 3-3 = 4-1 (the amendment of ROOT 2.2 is
made, and the draft still called it pending).

### Majors

| Id | Finding | Disposition |
|---|---|---|
| 1-1 | Commit 58be68b amended ROOT 2.2's `shot_location_value` parenthesis ("open-play shots from the opponent half per 90, amended by 2.10 W2") and extended W2 to cover it, but the draft still said the parenthesis "still reads non-penalty shots" and that the amendment was pending; the registration path cannot correct it (PIPELINE 0 allows two edits to `preregistration.md`, registers `PIPELINE.md` byte for byte, and lets the root write only the counted keys into `config.json`) | Applied. Checked with `git show 58be68b -- docs/research/north-star/ROOT-DECISIONS.md`: 2.2 and W2 read as the finding says. The DRAFT banner, preregistration 1 and `root_rulings_rule` lose the exception and say that W2, as extended on 18 October 2026, rules the open-play design for all three shot candidates and that ROOT 2.2's two parentheses are amended to match (the first in 8e4f4cf, the second in 58be68b). `root_amendment_before_registration` is deleted (no branch read it). PIPELINE 13: the amendment step leaves the order sentence, the "Root amendment" row and the registration commit's "ROOT-DECISIONS 2.2" row are deleted, and the rulings row says the amendment is made. DISSENT 6 and OPEN QUESTION 6 are closed outright. The second audit's "For the root" item 1 is thereby done. `pipeline_spec_sha256` recomputed |
| 2-1 | The required test "a challenger with a singular information matrix in one fold gives `None`, never NaN, for its `pooled_gain` and its statistics" contradicts PIPELINE 4 and 5: a non-converged estimate keeps its finite last iterate, `LoloResult.predictions` holds `p_MFLEX` in every league, and a statistic is `None` only when not finite, so a correct implementation fails the test | Applied. The clause now reads: such a challenger has `converged=False` and `standard_errors` `None` in that fold; its predictions are those of its last iterate; its `pooled_gain` and statistics are finite or `None` and never NaN (its calibration fits on a constant logit return `None`); `challenger_converged` is false and the instrument is `M1`. The "undefined statistic" row says the predictions are the last iterate's. No verdict depends on it: a non-converged challenger is never selected and its statistics gate nothing. Corrected by the verification below (V2-2): on that constant logit only the calibration slope is `None`; the intercept fit converges and is finite. The audit's walk of every other branch (instrument scenarios, the 2^10 mapping, gradients, the separable toy, S-count and S-fit) found nothing else |
| 3-1 | Both frozen ESTABLISHED statements counted leagues by the reliability bound alone, while a league closed as REDUNDANT or CONFOUNDED (or made INCONCLUSIVE by the guard) can have a bound at or above 0.70: with three `SHIP`, one `SHIP_WITH_BAND` and one REDUNDANT league at a bound of 0.90, row 5 gives `ESTABLISHED_BAND`, yet the bound reaches the number threshold in four leagues, so the served sentence is false while `results.json` publishes the numbers | Applied, the audit's wording. Reviser's check: `band.py` through the shipped `decide()` gives `SHIP, SHIP, SHIP, SHIP_WITH_BAND, REJECT`, n 3, s 4, row 5, and four bounds at or above 0.70. `registry_outcomes.candidate.ESTABLISHED_NUMBER`: "...: in at least four of the five leagues it passed the frozen rule at the number threshold, each such league with a reliability lower bound at or above that threshold and no declared baseline statistic correlated with it above the ceiling. ..."; `ESTABLISHED_BAND`: "...: in at least four of the five leagues it passed the frozen rule, with a reliability lower bound at or above the band threshold and not a near-copy of any declared baseline statistic, and in fewer than four it passed at the number threshold. ..."; `player_lab_text.ESTABLISHED_BAND.detail`: "...: it passed at the band threshold in enough leagues and at the number threshold in too few, and was not a near-copy of a declared baseline statistic in the leagues where it passed. ...". Preregistration 9.1 now says the established statements count only the leagues where the candidate passed the frozen rule. All three pass `scan_labels` and hold no digit; the draft guard passes |
| 4-1 | As 1-1, from scope 4: the frozen files would misstate a binding root rule for good, and `counted_by_root_rule` allows no later edit to those keys | Applied with 1-1 |
| 4-2 | The leg's gauntlet orchestration was not written: `run_gauntlet` took no specs and ran "all count_gates for all candidates", so a natural implementation evaluates the public `box_shot_share` (zone `penalty_area`) and `opp_half_defensive_actions` on the leg and passes every listed test; the LOCAL candidate block carries `context_limits` and `house_replication_label`, which only `candidate_verdict` produced, while `candidate_verdict` is not called on the leg | Applied. `run_gauntlet(frames, specs, shot_values, instrument_token, rule, correlation, config)` returns `{candidate_id: {league: LeagueEvaluation}}` and never calls `candidate_verdict`; a new `specs` row: `tuple(CANDIDATES.values())` on the public run, and on the leg the members of `sb_leg_candidates` holding an `ESTABLISHED_*` token in the committed `results.json`, with `sb_box_spec(config)` in place of `CANDIDATES["box_shot_share"]`; no count gate for a candidate outside `specs`; the order row speaks of specs, the instrument dependency by `spec.instrument`, and states that on the leg the token is the refit's and the config `sb_leg_config(config)`. New `replication_context(spec, evaluations, config)` returns `context_limits` and `house_replication_label`, the one source of both for `candidate_verdict` and the leg's candidate block. PIPELINE 10's gauntlet and output rows say so (for `box_shot_share` the block's definition and fingerprint are `sb_box_spec`'s). `tests/test_candidate_sb.py` gains a planted shot at x = 101/120, y = 0.5 (0.8417: inside `penalty_area`, outside `penalty_area_sb`) counted in the public box share and not in the leg's, the leg's box evaluations carrying `sb_box_spec`'s fingerprint, and a spy showing the leg's `specs`, no call of `candidate_verdict` and no count gate for `opp_half_defensive_actions` |
| 4-3 | The leg runs after the public results are committed, tied to the pre-outcome code only by the self-check stamp's `source_hashes`, while any change to a pinned file may be re-stamped; so `candidate_sb.py`, `provider_inputs.py` (which now defines the leg's kept shots and interception flag) or a gauntlet module could be edited after the public outcome and run, against section 10's own "fixed before any public outcome is known"; only `sb_reader.py` had a refusal for good | Applied, first option. New `sb_code_pin_rule`: `--external`, in both modes, refuses unless the current `source_hashes` (the list of 7.2, which holds `candidate_sb.py`, `provider_inputs.py`, `sb_reader.py` and every gauntlet and instrument module) equal `provenance.source_hashes` of the committed `results.json`; a stamp made after the results commit does not unlock it; the leg runs from a checkout whose pinned files are those of the results commit. Since section 7's repair clause changes a pinned file, the failed-execution row now says that a leg failure needing a code repair ends the leg with no label (`analysis.md` says so) and one needing none may start again once disclosed, from a checkout with unchanged pinned files; neither is a failed execution of the public run. The "pin after registration" row names the rule for every pinned file other than `sb_reader.py`; preregistration 11, PIPELINE 10's refusals and checklist item 18 cite it; `tests/test_candidate_sb.py` changes `candidate_sb.py`, `provider_inputs.py` and `candidate_gauntlet.py` in turn after a synthetic results commit, re-stamps, and sees `--external` refused in both modes. The alternative (extending `sb_reader_pin_rule` file by file) would leave the shared gauntlet modules unbound |

### Minors

| Id | Finding | Disposition |
|---|---|---|
| 1-2 | The disclosure of E-11's dropped player-matches and its two structure counts covered only player-matches with 0 capped minutes; rows of an eligible player in a player-match with no `lineups` row (a player absent from the match's records, or any substitute of a match whose `substitutions` field is not a list, for which the adapter writes no substitute row) also enter E-09's numerator with no minute, and E-11's unit drops them | Applied. Checked in `pappalardo.py` `lineups()`: `subs = subs if isinstance(subs, list) else []`, and a bench player gets a row only if he came on. PIPELINE 7.1 defines both fields over player-matches whose capped minutes are 0 or which have no `lineups` row; preregistration 1 says E-11's unit "drops a player-match with no regulation minute or no team-sheet row", and section 3's "Known and uncorrected" names both cases |
| 1-3 | The minutes caveats named stoppage time but not dismissals, which KNOWN_LIMITATIONS records (starters sent off before the 90th minute credited 90 minutes or more) and which E-11's rule ignores | Applied: "a starter sent off before the 90th minute is credited minutes to the 90th (KNOWN_LIMITATIONS), as E-11's rule does, where a dismissal changes nothing, which lowers his per-90 values" |
| 1-4 | "The leagues contain no other period; the filter is asserted to drop zero rows" is a frozen assumption, and phase 2 stops whenever the period filter drops a row, yet the root did not count it before registration, so a false assumption would fail every run | Applied: `expected_rows_outside_periods` (0 per league) and `rows_outside_periods_rule` in the config, the key added to `counted_by_root_before_registration` and `counted_by_root_assumption_pins`, and `counted_by_root_assumption_rule` names it; preregistration 3 (the Periods row and "four assumption pins"), PIPELINE 0, phase 2 and 13 ("Structure counts") follow; the runner test plants a period filter that drops a row. The adapter writes `matchPeriod` verbatim (`pappalardo.py`), so the count is a structure count of the root's script |
| 1-5 | The W3 tie compared E-09's opponent-half mask with the test's own copy of E-11's zone predicate, not with E-11's quantity, so a change of E-11's `>` to `>=` would leave the test passing | Applied: the test compares with `provider_inputs._quantities(harmonised, None, e11_config)["open_play_shots"] > 0` and `["opp_half_duel_or_interception"] > 0`, imported as a private member as the leg imports `_statsbomb_flags`, and restates neither predicate; preregistration 15 says so. Reviser's rerun of the audit's `w3_tie.py`: 304,128 rows, both ties hold through `_quantities`, and the planted defects fail |
| 2-2 | `standard_errors` was `None` only when `X'WX` is singular; under quasi-separation `inv` can succeed with a negative diagonal entry, giving NaN, which phase 7's `allow_nan=False` refuses in the `fits` block | Applied: `None` also when any diagonal entry of the inverse is not finite and positive (PIPELINE 4's row and both dataclass comments; the "undefined statistic" row says the `fits` block echoes no NaN); the separable-toy test covers 200, 2,000 and 20,000 rows over several seeds and a planted matrix whose inverse has a negative diagonal entry. Reviser's check (`reviser_sep.py`, PIPELINE 4's IRLS written literally, separable toys, 60 seeds): standard errors came out NaN in 7 of 20 fits at 200 rows, singular in 27 and finite in 26 overall, so the case is reachable whatever the size |
| 2-3 | "The rule there equals the earlier one" referred to a rule of a previous draft that the registered texts do not state | Applied: "equals convergence of every model of `gate_s_fit_models` in every fold, because `MFLEX` is selected only when it converged in every fold" (preregistration 4.4, PIPELINE 5, `gate_s_fit_rule`) |
| 2-4 | `shot_frame` compared `body_part` with `head_or_body_value`, which no parameter carried, although WP-B receives every value as a parameter | Applied: `head_or_body_value: str` is a keyword parameter of `shot_frame`, passed from `config["head_or_body_value"]`; the comment names what `geometry` holds |
| 2-5 | As 1-1, from scope 2 | Applied with 1-1 |
| 3-2 | The research sentence ("E-09 tested whether four player statistics and a location-only shot conversion model meet frozen criteria") is written once any record reads TESTED, including when only the instrument does; the audit's enumeration: 3 of 4,116 reachable assignments write it with no statistic tested, and 2,315 with fewer than four | Applied with a variant of wording: "E-09 held four player statistics and a location-only shot conversion model to frozen criteria on public event data; each verdict says whether its subject was judged or left untested. That is not validity and not decision use, and no E-09 statistic is shown beside players." ("Put ... to frozen criteria" was replaced by plainer English.) It passes `scan_labels`; the reviser's rerun of `planning.py` reproduced both counts |
| 3-3 | As 1-1, from scope 3 | Applied with 1-1 |
| 3-4 | NaN handling of the battery maximum was unspecified (pandas skips NaN, Python's `max` depends on order, `np.max` propagates it, and an empty maximum raises), so the required all-NaN battery test admitted a crash | Applied: a column whose sd over A is not finite or is below `degenerate_sd` is dropped and recorded; `baseline_r` is `np.max` over the remaining columns' gating values, NaN-propagating, and NaN when none remains; the guard reports `NON_FINITE:baseline_r`; `closest_baselines` is then empty (preregistration 6 step 4, PIPELINE 6). The test now expects `NON_FINITE:baseline_r`, never an exception |
| 3-5 | Section 6 still asserted `shot_volume` equal to `shots_per_90` "to 1e-12", against the exact tie of section 3 | Applied: "exactly: same frame, same minutes, the `PER_90` expression of section 3" |
| 3-6 | The share floor departs from the house's minutes-only eligibility with no row; the goalkeeper exclusion is lenient on baselines only and stricter on the reliability bound (goalkeepers would form one more near-centroid group, raising n - 2 - g by about their number and so `half_low`) | Applied: a "Share floor" row (departs; neither; not flagged), goalkeepers relabelled "neither: lenient on baseline correlations, stricter on the reliability bound; flagged; a planted case shows both"; the 6.1 opening paragraph says why the goalkeeper exclusion stays flagged and that the share floor is not; the required test shows both directions of a "neither" departure; PIPELINE 6 `departures_active` follows |
| 3-7 | The redundant sentence was chosen per candidate, so `shot_location_value` closed against `shot_volume` in one league and `mean_x` in another would carry the volume sentence for the `mean_x` league | Applied with a variant: `redundant_rule` applies league by league; the volume sentence ends "in the leagues where the frozen rule closed it against open-play shot volume, in this corpus", and `redundant_other` gains "against that statistic", so each sentence is limited to its own leagues (preregistration 14). Both pass `scan_labels` |
| 3-8 | Under an S-count failure every selection field is null, yet model card items 1 and 14 print the specification and the suffixed id | Applied: both print "no specification selected (S-count failed)", never a null suffix |
| 3-9 | No check enforces that the not-run statement and the two non-claims hold no digit but the experiment id's: V7 binds LOCAL records, and the draft guard's digit check omits them | Applied: PIPELINE 13's guard row says the root adds that check, with a planted case, before the registration commit; preregistration 10 says V7 binds LOCAL records only and the guard checks it for these PUBLIC ones. Today all three texts hold no digit but "E-09"'s. The guard file is the root's (below) |
| 4-4 | `verify` was declared as phases 1 and 2 while `run` guarded phases 2 to 7, so the failed-execution boundary fell inside `verify`; `Phase` was undefined and `guarded` was not told which files `step` wrote | Applied: `refusals(config, *, protocol_commit)` (phase 1, outside `guarded`, appends no record) and `structural_pins(config, phase)` (phase 2, inside `guarded`, a stop is a failed execution); `Phase` is the one mutable dataclass (`reached`, `written`); a runner test drives `run` across the boundary: a phase-2 stop appends one record with phase 2 and returns 3, a phase-1 refusal appends none |
| 4-5 | Phase 3 compares the recomputed self-check block byte for byte, while the stamp recorded no packages or machine and `generator_sanity` drew from no named stream | Applied: the stamp records `packages` (the fields of `provenance.packages`, `machine` included) and phase 1 refuses a stamp made under other packages or on another machine (`selfcheck_stamp_rule`, phase 1, 7.3, the runner test); `selfcheck_seed_rule` names the generator-sanity stream `default_rng([selfcheck_seed, 200, world_position])`, and `generator_sanity_rules.draws` with `synthetic_generator_sanity_players` (6,000) and `synthetic_generator_sanity_shots_per_player` (2,000) fix its draws and their order; NUISANCE's share needs none. Reviser's check (`reviser_sanity.py`, synthetic): EFFECT's latent rate-value correlation at those counts is between 0.62 and 0.63 over six streams, against the bound 0.75 and the feasibility figure 0.620 |
| 4-6 | After the second audit's 4-11 the record admits the multiplier reading of the 14 October feasibility script is not recorded, yet three frozen texts still said it simulated "this exact generator" | Applied with a variant: the second option, rewording preregistration 15, PIPELINE 8.3 and `selfcheck_feasibility.by` (the script ran the generator and estimator as they then stood, its multiplier reading is not recorded and the IRLS was revised after it; the binding check is the pipeline's self-check), and recording the audit's check of both readings in `selfcheck_feasibility.third_audit_multiplier_check`. Reviser's rerun of the audit's `effect_rel.py` (a simplified player-level simulation, 25 synthetic leagues per reading): smallest bounds 0.832, 0.939 and 0.885 (`shot_volume`, `opp_half_defensive_actions`, `box_shot_share`) under the unit-mean reading and 0.832, 0.958 and 0.895 under the other, far above 0.70. The 40-replicate event-level rerun was not done: it needs the pipeline, which is built after registration |
| 4-7 | The threshold scan matched four literal spellings (0.7 escaped it), most thresholds were not scanned, and `candidate_sb.py` (WP-F) was outside the scan and the section 0 rule | Applied: an `ast` scan of `shot_model_evaluation.py`, `candidate_gauntlet.py`, `candidate_sb.py` and the runner for any numeric constant equal to a numeric leaf of the frozen config, with an explicit exclusion list (0, 1, 2, 90), each entry naming its non-threshold use; a planted 0.7 is caught; section 0 and checklist item 4 name WP-F. Corrected by the verification below (V1-3, a confirmed blocker): as written, the scan refused constants the frozen text itself requires (the exit code 3, the null-ECE percentiles, the minutes-share quantiles); those are now config keys (`failed_execution_exit_code`, `ece_null_percentiles`, `match_set_minutes_share_quantiles`), phase numbers and rule rows are counted, the list stays closed at 0, 1, 2 and 90, and a planted league-count literal 3 is caught as well |
| 4-8 | Checklist item 9 asked for no goals-minus-model quantity anywhere, while ECE, MCE and R4 are such differences at bin or subgroup level | Applied: "No goals-minus-model quantity is grouped by player or team (`grep` ... per `player_id` or `team_id`); the bin-level calibration differences of section 5 and R4's pooled subgroup ratios are the only comparisons of observed goals with the model, and none is per player or team". Corrected by the verification below (V2-4 = V3-8): every comparison of observed goals with the model in section 5 is per league, per bin or pooled, Brier, log loss, L1's ratios and the calibration fits included |
| 4-9 | The stated size of the config echo (about 68 KB) understated it | Applied, measured after this revision's additions: `json.dumps(config, indent=2, sort_keys=True)` is 77,334 bytes, and 84,198 nested under `provenance.config`; PIPELINE 7.1 says "about 84,000 bytes at indent 2 under `provenance.config`, about 77,000 on its own" and keeps the 250 KB estimate, under the 524,288 bytes of `results_maximum_bytes` |

Refuted claims: none.

### Checks run by the reviser (synthetic or data-free)

Scratch scripts under the session scratchpad, `E-09-Third-audit-18-October-2026/` (the
auditors' scripts, rerun, and two of the reviser's, named `reviser_*`):

- `band.py` (3-1), `planning.py` (3-2), `w3_tie.py` (1-5) and `effect_rel.py` (4-6), rerun; the
  numbers above reproduce.
- `reviser_sep.py`: PIPELINE 4's IRLS written literally on separable toys (2-2).
- `reviser_sanity.py`: the EFFECT generator-sanity correlation on the named stream at the
  frozen counts (4-5).
- `git show 58be68b -- docs/research/north-star/ROOT-DECISIONS.md` (1-1); `pappalardo.py`
  `lineups()` (1-2); KNOWN_LIMITATIONS on dismissals (1-3); `provider_inputs._quantities`
  (1-5); the V7 branch of `verdicts.py` (3-9).
- The five fingerprints recomputed from the config's clauses, all unchanged; the
  `e11_config_sha256`, `decide` and `_safe_abs_corr` source hashes and the `sb_reader` hash
  recomputed from the tracked files, all unchanged; no key of the config is refused by
  `banned_key_paths(..., parts=BANNED_KEY_PARTS)`; every new served sentence passes
  `scan_labels`, and the registry statements and Player Lab texts hold no digit.
- `pipeline_spec_sha256` recomputed with `lf_sha256` after the last `PIPELINE.md` edit
  (`14f45d57...`); `tests/test_protocol_drafts.py` and `tests/test_licensing.py` pass, and
  `scripts/check_licensing.py` is clean. The `tests/test_licensing.py` entries of this folder's
  `PIPELINE.md` and `REVIEW-RECORD.md` now name the leg's specs and its pin to the public run's
  code.

### For the root (PIPELINE section 13)

1. No question waits for a root ruling. The second audit's item 1 is done: ROOT 2.2 and W2 were
   amended in 58be68b, and the draft now says so.
2. Before the registration commit, add to the E-09 draft guard in `tests/test_protocol_drafts.py`
   the check of 3-9, with a planted case: `registry_common.not_run_statement`,
   `registry_candidate.non_claim` and `registry_instrument.non_claim` hold no digit other than
   those of the experiment id. That file is the root's.
3. The root's structure-only count before registration gains one assumption pin,
   `expected_rows_outside_periods` (0 per league, `rows_outside_periods_rule`); like the other
   three, a departing count stops registration and is never written.
4. Two procedural consequences, no ruling needed: the self-check stamp is made on the machine
   and packages of the real run (phase 1 refuses one made under others), and the external leg
   runs from a checkout whose pinned files are those of the results commit
   (`sb_code_pin_rule`), so a leg failure that needs a code repair ends the leg with no label.
5. This revision has not been audited. By W10 and the E-10 precedent an audit of it, or a
   verification of its edits, that confirms no blocker is needed before E-09 is called READY.

## Verification of the third audit's revision, 18 October 2026

The third audit found the second audit's revision (commit `58be68b`) READY in every scope, and
commit `0d252eb` applied its majors and minors (the third audit's revision, above). This round
asked one question: did the edits of `0d252eb` add a blocker? Three verifiers (V1, V2, V3) each
read `git diff 58be68b 0d252eb` over this folder in full, the third audit's findings and
dispositions above, and as much of the draft and the shipped code as they needed, against
ROOT-DECISIONS (2.9, whose Z4 set the E-10 precedent, and 2.10 included), DECISIONS.md, the copy
guard (`galactico/domain/labels.py`, `api/runtime.finalize`) and `galactico/domain/verdicts.py`.
A blocker is a verdict that could be wrong or undefined, a frozen sentence that fails the copy
guard, a broken rule, a pipeline that cannot be built as written, or a required test that
cannot fail. Every claimed blocker went to a refuter. No file under `data/` was opened. The
verifiers' scripts (`ast_scan.py`, `ast_scan_v2.py`, `scan_v2.py`, `leaves.py`, `leaves_v2.py`,
`calib_constant_logit_v2.py`, `pin_bypass.sh`, `fingerprints.py`, `checks.py`,
`w3_quantities.py`), the refuter's (`refute_V1_3.py`) and the applier's (`scan_revised.py`,
`reader_all_refs.sh`, `config_edits.py`, `pipeline_edits.py`) use synthetic snippets,
repositories and numbers only (the scans read the draft config's numeric leaves, nothing else)
and are not committed.

**Result.** One blocker was claimed (V1-3), and the refuter confirmed it, narrower than claimed
and with a corrected proposal, which is the one applied. V2-1 and V3-1 report the same defect;
their verifiers graded it consistency (a correct implementation fails a required test, the kind
the third audit rated major in 2-1), and they are listed under it. So the edits of `0d252eb`
added a blocker, and E-09 was not READY at `0d252eb`. Besides it, the verifiers reported
nineteen consistency findings, thirteen distinct: V1-1 = V3-11 (the paraphrase of W10),
V1-2 = V2-3 = V3-10 (lenient and flagged departures), V2-4 = V3-8 (checklist item 9),
V2-5 = V3-9 (the leg's box fingerprint) and V2-8 = V3-6 (the mutable `Phase`). The applier
checked each against the draft, the code, the rules or a synthetic script; every one holds,
none moves a verdict, and each is applied, V2-6 and V3-2 with stated variants and V3-5 by both
of its options. This revision applies the blocker and every consistency finding, but it has
not itself been audited or verified: by W10 and the E-10 precedent, an audit of it, or a
verification of its edits, that confirms no blocker is needed before E-09 is called READY.

What each verifier found:

- V1 (the root rulings, the departures, and the scan, reported for scope 4's verifier): three
  findings, V1-1 and V1-2 (consistency) and V1-3 (blocker).
- V2 (the scan, the instrument's clauses, the dataclasses, the leg's token and tests, the
  checklist): eight consistency findings, V2-1 to V2-8.
- V3 (the scan, the leg's pins and refusals, the runner's seams, the feasibility record, the
  checklist and the config's rule sentences): eleven consistency findings, V3-1 to V3-11.

### Blocker

| Id | Claim | Refutation | Disposition |
|---|---|---|---|
| V1-3 = V2-1 = V3-1 | The 4-7 `ast` scan refuses, in `shot_model_evaluation.py`, `candidate_gauntlet.py`, `candidate_sb.py` and the runner, any numeric constant equal to one of the config's 159 distinct numeric leaves, except 0, 1, 2 and 90; constants the frozen text itself requires collide with leaves (3, 4, 5, 50, 95, 0.5 among them): the runner's `return 3`, phase numbers 3 to 7, rule rows 1 to 8 and leg rows 1 to 5, and the null-ECE percentiles 50, 95 and 99, which are no config key. Before `0d252eb` the scan matched four literal spellings and had no such conflict. The claim proposed widening the exclusion list by value | Not refuted, narrower than claimed. The exit code is a collision no honest code avoids: PIPELINE 7 makes `guarded` return 3, the config has no exit-code key, 3 is the value of four threshold keys (`context_limit_leagues`, `sb_minimum_evaluable_leagues`, `sb_survival_leagues`, `sb_rejection_leagues`), and only obfuscation (`1 + 2`) or an open reading of a list the record calls closed would pass (`refute_V1_3.py`: `return 3` is flagged). Phase numbers and rule rows need no literal (`+= 1`, `enumerate(..., start=1)`); the percentiles pass only by contortion (`np.median`, quantiles 0.95 and 0.99), while section 0 says lists are read from the config. The proposal is wrong: an exclusion by value cannot tell 3 as an exit code from 3 as a threshold, excluding 3 to 8 would hide nine league-count keys, and restricting the compared leaves to threshold keys leaves 3 flagged. Corrected proposal: keep the closed list and take the forced constants out of the scanned code | Applied, the refuter's corrected proposal, plus two points the applier verified. Config: `failed_execution_exit_code` 3 and `ece_null_percentiles` [50, 95, 99], and, from V2-1, `match_set_minutes_share_quantiles` [0.05, 0.95]: the WP-D field `match_set_minutes_share_p05_p95` needs 0.05 (a leaf, `planning_figures.r3_league_calibration_slope_sd`) or 5 and 95 (both leaves), a second collision no honest code avoids; it gets a section 6 row (T20's exposure imbalance, reported only), which it lacked. PIPELINE 5 reports the null percentiles from `ece_null_percentiles`; PIPELINE 7: `guarded` returns `failed_execution_exit_code` (3), the runner exits with it, `step` and `evaluate` advance `Phase.reached` by one as each phase after the second begins, and `evaluate` takes the `Phase` (without it, `step` would have to write 7, or add 3, to reach phase 7 after `evaluate` covers 4 to 6, both refused), and `candidate_verdict` and `sb_verdict` count their rows by `enumerate`; PIPELINE 6 and 10 say the same in their rows. PIPELINE 8.4: the list is 0, 1, 2 and 90 and nothing else, each entry naming its use; the forced values are read from the config or counted; a planted 0.7 and a planted league-count literal 3 in `candidate_gauntlet.py` are each caught; `guarded` returns `config["failed_execution_exit_code"]`, which equals 3. The 4-7 disposition above is corrected. Applier's check (`scan_revised.py`): snippets of the four modules written to the revised text are not flagged; `return 3`, `np.quantile(s, [0.05, 0.95])`, `np.percentile(x, [50, 95, 99])`, a planted 0.7 and `evaluable >= 3` are. V3-1's alternative, module-level `ROW_*`, `PHASE_*` and `EXIT_FAILED` names whose assignments the scan skips, is not taken: a skipped assignment would admit `MINIMUM_LEAGUES = 3` unless the names were policed too |

### Consistency findings

| Id | Finding | Verified | Disposition |
|---|---|---|---|
| V1-1 = V3-11 | `root_rulings_rule`, frozen at registration, said "W10 requires each revision to be audited", while W10 reads "The revision applying W1 to W9 is audited again before E-09 is called READY"; the extension to every revision is the E-10 precedent's | Holds: ROOT-DECISIONS 2.10, W10. Stricter, never laxer, so no rule is broken | Applied: "W10 required the revision applying W1 to W9 to be audited again, and by the E-10 precedent each later revision is audited, or its edits verified, before E-09 is called READY". The banner now says "an audit of it, or a verification of its edits", as this record does. Config only |
| V1-2 = V2-3 = V3-10 | After 3-6 the goalkeeper exclusion is a "neither" departure that stays flagged, and preregistration 6.1 and the `departures_active` row speak of flagged departures and both directions; the dataclass comment, checklist item 11 and preregistration 15 still said lenient and one direction | Holds | Applied: the comment reads "the flagged departures of preregistration 6.1 in force"; item 11 "its direction (both for a two-sided one); flagged ones are listed in `departures_active`"; preregistration 15 "shown in its stated direction (both directions for a "neither" departure) and each flagged one listed" |
| V2-2 | The 2-1 rewording said the singular challenger's "calibration fits on a constant logit return `None`"; only the slope fit does: the intercept fit on a constant logit is intercept-only with a zero offset and converges | Holds: `calib_constant_logit_v2.py` rerun (synthetic labels, the IRLS of PIPELINE 4): slope not converged, so `None`; intercept converged at -2.1389, the logit of the mean label | Applied: in that example the fit stops at zero coefficients, so its held-out logit is constant; its calibration slope is `None` and its calibration intercept is finite. The 2-1 disposition above is corrected. No verdict depends on it |
| V2-4 = V3-8 | The 4-8 rewording of checklist item 9 called ECE, MCE and R4's ratios the only comparisons of observed goals with the model, while L1's per-league observed over expected, the calibration fits, Brier, log loss and the descriptive counter-attack ratio are such comparisons too | Holds (PIPELINE 5 and 7.1) | Applied: "every comparison of observed goals with the model in section 5 (Brier and log loss, observed over expected per held-out league, pooled and per R4 subgroup, the descriptive counter-attack ratio, the calibration fits and bins, ECE and MCE) is per league, per bin or pooled, and none is per player or team". The 4-8 disposition above is corrected |
| V2-5 = V3-9 | The 4-2 test said the leg's `box_shot_share` evaluations carry `sb_box_spec`'s fingerprint; `LeagueEvaluation` and `GateCount` have no such field, and the LOCAL block's fingerprint is copied from `sb_box_spec` by the output rule, so it proves nothing | Holds (section 6 dataclasses; section 10 output row) | Applied, V3-9's wording: the spec the spy sees passed to `run_gauntlet` for `box_shot_share` has `sb_box_spec`'s fingerprint `23bf9214db9b`. The planted shot at x = 101/120 stays |
| V2-6 | `run_gauntlet` typed `instrument_token: str` while the leg passes `refit_token: str \| None`, and no refit was defined when the public run selected no specification (a public S-count failure, with an established `shot_volume` or `box_shot_share` still sending the leg to run) | Holds: `instrument_inconclusive_rule` nulls every selection field; rows 1 and 2 of 9.1 apply only to `shot_location_value`, so it is then not in `specs` and the token is read for no spec | Applied with a variant: `instrument_token: str \| None`, read only for a spec with an instrument; section 10's instrument row says that when the public run selected no specification nothing is refitted, `refit_token` is `None` and the LOCAL `instrument` block is null. Variant: the proposal refitted only when `shot_location_value` is in `specs`; the applier keeps the refit, a reported block, whenever a specification was selected, and fills only the case that was undefined |
| V2-7 | The 2-4 edit split the `shot_frame` table row of PIPELINE 4 over two lines | Holds (`awk`: one row line not ending in a pipe) | Applied: the lines are joined |
| V2-8 = V3-6 | Section 0 and checklist item 16 required frozen dataclasses, while 4-4 added `Phase`, "the one mutable dataclass" | Holds | Applied: "frozen dataclasses, except the runner's `Phase` (section 7)" in both |
| V3-2 | The leg is told to run from a checkout whose pinned files are those of the results commit; after an E-11 repair of `sb_reader.py` and a re-stamped `acceptance.json` made after E-09's results commit, such a checkout holds the old reader and the old stamp, so `sb_reader_pin_rule` and `sb_code_pin_rule` both pass, and the frozen "refuses it for good" is not enforced on the route the text endorses | Holds: `pin_bypass.sh` rerun (synthetic repository): at the tip both pins refuse, on a checkout of the results commit both pass | Applied with a variant of the first option: `sb_reader_pin_rule` gains a clause read on every ref, `git log --all --format=%H ^<protocol_commit> -- galactico/validation/sb_reader.py` prints nothing (refused when git is unavailable), so no checkout reopens the leg after a later repair; `sb_code_pin_rule`, the leg's refusals, the "pin after registration" row and preregistration 11 say so; `tests/test_candidate_sb.py` gains the case. Variant: every ref instead of the default branch's tip, which no config key names. Applier's check (`reader_all_refs.sh`, synthetic repository): after a later repair the clause refuses at the tip and at the results commit; without one it passes at both |
| V3-3 | The leg inherited phase 1's refusal of a stamp made under other packages or on another machine, which serves only phase 3's byte-for-byte comparison, while the leg runs no self-check: a leg run after an OS update on the same machine would be refused on that ground alone | Holds: section 10 cites no phase 3; `platform.platform()` is part of `machine` (7.2) | Applied, first option: the leg's refusals exempt the output check and the check of the stamp's `packages`; `tests/test_candidate_sb.py` shows a stamp with other packages does not refuse the leg. The stamp's three hashes are still checked |
| V3-4 | After the 4-4 split, `refusals` was said to return the provenance block, yet `frame_hashes`, the sidecar and the raw-manifest hashes need data that `structural_pins` loads in phase 2; loading it in `refusals` would put a load error outside `guarded` | Holds (7.1 provenance, 7.2 `frame_hashes`) | Applied: `refusals` returns the phase-1 part of the provenance block, read from code, the config and git; `step` adds `frame_hashes`, `sidecar`, `raw_manifest_sha256` and `raw_file_sha256` after `structural_pins`, inside `guarded` |
| V3-5 | The new run-level test needed seams the text did not give: `run` took no log path, so the record went to the real `run_output_root/failed_run_log`, and the real `refusals` refuses everything before a stamp exists | Holds (config `run_output_root`, `failed_run_log`; phase 1) | Applied, both options: `run(config, *, protocol_commit, out, log)`, `main` passing `ROOT / run_output_root / failed_run_log`; the run-level test puts `out` and `log` under `tmp_path`, stubs `load_league` and, on the phase-2 side, stubs `refusals` to pass |
| V3-7 | PIPELINE 8.3 and `selfcheck_feasibility.by` said the third audit's check left "every" planted or EFFECT candidate's smallest bound far above `reliability_number`, and 8.3 that the reading "barely moves the rates"; the check covered three candidates (not `shot_location_value`) and measured bounds in a player-level simulation, not replicate rates | Holds (`third_audit_multiplier_check` lists three candidates) | Applied: "the smallest league bound in `EFFECT` of each of the three candidates it checked ... (`shot_location_value` was not checked)", and "barely moves those bounds" |

Refuted claims: none.

### What the applier changed

- `config.json`: `root_rulings_rule` (V1-1); `failed_execution_exit_code`, `ece_null_percentiles`
  and `match_set_minutes_share_quantiles` (V1-3); `sb_reader_pin_rule` and `sb_code_pin_rule`
  (V3-2); `selfcheck_feasibility.by` (V3-7); `pipeline_spec_sha256`, recomputed with
  `galactico.validation.digests.lf_sha256` after the last `PIPELINE.md` edit (`34fd0116...`).
  No served string, registry sentence, fingerprint or threshold changed; no new key is refused
  by the denylist, `banned_key_paths(..., parts=BANNED_KEY_PARTS)` or the provider-name rule.
- `PIPELINE.md`: section 0, Engineering (V3-6); section 4, the `shot_frame` row (V2-7);
  section 5, the null-ECE row (V1-3) and the singular-challenger test (V2-2); section 6, the
  `departures_active` comment (V1-2), the `run_gauntlet` signature (V2-6), a
  `match_set_minutes_share_p05_p95` row (V1-3, V2-1) and the `candidate_verdict` row (V1-3);
  section 7, the `refusals`, `evaluate` and `run` signatures and the paragraph on the seams
  (V1-3, V3-4, V3-5) and the failed-execution paragraph (V1-3); 8.3, the feasibility paragraph
  (V3-7); 8.4, the runner test row (V1-3, V3-5); section 9, items 9 (V2-4), 11 (V1-2) and 16
  (V3-6); section 10, the instrument row (V2-6), the token row (V1-3), the refusals row (V3-2,
  V3-3), the "pin after registration" row (V3-2) and `tests/test_candidate_sb.py` (V2-5, V3-2,
  V3-3).
- `preregistration.md`: the DRAFT banner's history (this round, and the wording of V1-1);
  section 11, the reader pin on any checkout (V3-2); section 15, the departures (V1-2).
- This record: the 2-1, 4-7 and 4-8 dispositions of the third audit are corrected (V2-2, V1-3,
  V2-4), and this section.
- `tests/test_licensing.py`: the list entries for this folder's `PIPELINE.md` and
  `REVIEW-RECORD.md` also name the reader pin read on every ref. The draft guard
  (`tests/test_protocol_drafts.py`) and `tests/test_licensing.py` pass, and
  `scripts/check_licensing.py` is clean.

### For the root (PIPELINE section 13)

1. No question waits for a root ruling.
2. Items 2 and 3 of the third audit's list stand (the digit check of 3-9 in the draft guard; the
   assumption pin `expected_rows_outside_periods`). Item 4 stands with two changes: the leg's
   refusal no longer checks the stamp's `packages` (V3-3), and a change to `sb_reader.py` after
   registration bars the leg on any checkout, the results commit's included (V3-2).
3. This revision has not been audited or verified. By W10 and the E-10 precedent an audit of
   it, or a verification of its edits, that confirms no blocker is needed before E-09 is called
   READY.
