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
