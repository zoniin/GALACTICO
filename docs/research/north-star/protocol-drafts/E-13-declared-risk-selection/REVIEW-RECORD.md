# E-13 review record

What each round of review found in the E-13 draft and what was done with it. The draft
(`preregistration.md`, `config.json`, `PIPELINE.md`) is not registered and nothing in it has
been run. Every number below was computed on synthetic data or is arithmetic; no file under
`data/` was opened in any round.

## 18 October 2026 — first review, three lenses, and the revision

The root ruled the six reconciliation items of OR-XI-SPEC section 13 before the review
(ROOT-DECISIONS 2.11, T1 to T8). Three adversarial reviewers then read the draft against
ROOT-DECISIONS (R1 to R13, 2.2, 2.4 to 2.8, 2.11, 3b, with 2.9 and 2.10 as precedent),
ADR-0001 to ADR-0030, KNOWN_LIMITATIONS, LICENSING, VALIDATION, the house lifecycle, the
registered E-11 protocol, the READY E-10 draft and the audited E-09 draft, and the built risk
solver (`galactico/optimization/xi/risk.py`, its oracle, the router): a statistician (30
findings), a reader of the football data (27) and a reader for the constitution (29). One
reviser verified each finding against the draft, the shipped code and the rules, and applied it
or rejected it. Every finding held in substance. All 86 are applied; three have a part
rejected, with the reason in the table. The three items the task named as known before
registration (T1 to T7 item by item, the names of shipped code, the copy guard) are settled in
the same revision (last tables).

| Severity | Findings | Applied | Rejected in full | Applied with a part rejected |
|---|---|---|---|---|
| blocker | 24 | 24 | 0 | 2 |
| major | 36 | 36 | 0 | 1 |
| minor | 26 | 26 | 0 | 0 |

Several findings are one defect seen by two or three lenses (the badge word, the discard rule,
the audit interface, the planted structure check, the split-mean denominator, the registry
fields, the pipeline pin, the token scope, the two T4 and T7 consequences); each is listed under
its own id. Five findings ask for a draft guard in `tests/test_protocol_drafts.py`. This
revision edits only the draft folder, so the guard is a request to the root for the
registration commit (PIPELINE section 11), as W9 was for E-09; its checks were run here by a
scratch script of the same form (below).

### What the revision changed, in short

- **Order.** The house order: audit, registration with six `PENDING` records, the pipeline,
  the planted gate stamped in a commit of its own (`acceptance.json`), the run. Nothing of the
  pipeline runs before registration; a planted run evaluates BALANCE, references and
  pseudo-rules only; the rehearsal runs on its own `rehearsal_design` cells, disjoint from every
  frozen cell. A rule the gate shows unsound supersedes E-13 (the E-10 precedent).
- **Built solver (T1 to T3).** The audit calls `declared_risk_selection` with the built
  keywords through two adapters; certified means `CERTIFIED` with `EXACT` completeness; every
  audited item must be certified and match the enumeration on the XI, the per-world pairs, the
  used and discarded world ids and the optimum; the oracle gate runs both oracle files on POSIX
  and requires the frozen counts (9 passed, 0 skipped); `kernel.py`, `tradeoffs.py`,
  `ceilings.py`, `xi/__init__.py` and `snapshots.py` are pinned.
- **One discard rule (T2).** The shipped rule in its own words in both parts; Part B's used
  directions and worlds read needed candidates only; a goalkeeper never discards a world.
- **Decision rules.** A cost is read first in the selection verdict, both aggregations and the
  token table, so no measured cost sits under a positive or an inconclusive token; the cost
  side is Bonferroni over the subject's valid cells with a normal bound on the bootstrap SE;
  the cost row reads every valid cell; the reporting verdict has a non-zero gate; diagnostic
  validity requires the held-out cost to track the true cost; split means count identical
  directions as zero; the planted structure check runs on both snapshots together with a cost
  arm whose sign holds by construction.
- **Design.** `GATED_MINUTES` (minutes-equivalents, root-counted) replaces the appearance
  counts as primary and A2 profile; both geometries at 4,000 trials so that a cell's half-width
  is at most a third of the margin at per-trial SD 0.05; stress cells have a tier; every
  derivation of a count or a level is stated.
- **Registry and product.** Badge "LESS OPTIMISTIC, COST BOUNDED" and tokens renamed; full
  `VerdictRecord` fields in config (scope, not-run statement, status, limits, statement), every
  text through the response boundary under every token; token scope with the requirement set,
  the declared minima and no lock or exclusion (T5); `risk_report` conditional on the results
  commit under an ADR (T4); no product split-sample tool (T7); statements that say what the
  criteria test.

### Statistics lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-statistics-1 | blocker | The pipeline, its rehearsal and the planted suite ran before registration; for Part A that computes the outcome before commit P | Applied. House order (protocol intro; PIPELINE 0, 9, 11); "before commit P" deleted from the review checklist and the open question replaced by the supersede rule; `rehearsal_design` (latent SD 0.25, its own noise grid, levels, trial divisor and Part B gates) disjoint from every frozen cell, tested; planted runs pass `rules=("BALANCE",)` |
| R-statistics-2 | blocker | The planted structure check could never pass: 200 directions per snapshot against a gate of 450, four blocks against eight | Applied. One check over both snapshots (eight blocks), `planted_split_random_splits` 250, `split_expected_blocks` a parameter of `decide_split`, `diagnostic_valid=True` stated; the gate reachability asserted in `test_config_contract`; feasibility simulated (below) |
| R-statistics-3 | blocker | The split means had no defined denominator; the two readings can give different verdicts | Applied. `split_mean_denominator`: every used direction, zero where identical (as A1); shares over informative used directions; a truth-table case where the two readings disagree |
| R-statistics-4 | blocker | T2 not applied: "any candidate has zero exposure" kept beside the shipped rule | Applied. T2's words in Fixed definitions, Part A as a consequence, Part B's used rule and worlds, PIPELINE `world_valid` and `weighted_rates`; parity test with `world_losses` |
| R-statistics-5 | blocker | T1 not applied; certification read as `OPTIMAL`; no minimum certified count, so the audit could pass checking nothing | Applied. Built signature through `_risk_call` / `_risk_world_pairs`; certified = `CERTIFIED` and `EXACT`; `solver_audit_minimum_certified_share` 1.0 and no-audited-item failure; world seed rule and version string of E-13's own; `analyze_ties` false with the reason |
| R-statistics-6 | blocker | T3 not applied: the brute-force oracle and the kernel and tradeoffs modules not pinned | Applied, with `ceilings.py`, `xi/__init__.py` and `snapshots.py` too |
| R-statistics-7 | blocker | T4 not applied: the `risk_report` sentence printed as a figure note before any run | Applied. Conditional consequence (`risk_report_after_run`): no payload or note before the results commit; the mean added only then under an ADR, never beside the tail sum |
| R-statistics-8 | blocker | T5 not applied: the scope lacks the requirement set and names "club" where the router keys on scenarios | Applied. `token_scope` names formation, tiers, tail counts, scenarios, requirement set, declared minima, no lock or exclusion; the default progression-only request is outside |
| R-statistics-9 | blocker | T7 not applied: a product split tool committed and `product_split_rule` defined | Applied. Tool commitment, `product_split_rule` and interface 7 deleted; ALTERNATING a research family; `split_sample_after_run` |
| R-statistics-10 | major | The split aggregation ranks INCONCLUSIVE and UNVALIDATED above LARGER, so a held-out cost can sit under an ESTABLISHED token | Applied. LARGER first in `aggregate_split`, and a cost first in the selection aggregation and the table too (DISSENT 4 reverses the draft's DISSENT 6); walk: 0 of 400 two-component combinations with a cost give a positive or INCONCLUSIVE token (draft: 4 and 95); the four combinations in the truth-table test |
| R-statistics-11 | major | COSTS is a union of up to 216 one-sided tests with no multiplicity control | Applied. `cost_multiplicity_rule` (Bonferroni at `cost_family_alpha` 0.05 over the subject's valid primary cells, normal bound on the bootstrap SE) and the stated family-wise rate; frozen-shape planted array at cost = margin: 191 of 4,000 at 216 cells (below) |
| R-statistics-12 | major | The informative gate removes a valid cell with a resolved cost from the COSTS check | Applied. The cost row reads every valid primary cell; the informative gate applies to the positive row only; a truth-table case |
| R-statistics-13 | major | Power and size checked on one cell at the cheap boundary; no power at the frozen shape; trial counts without a precision target | Applied. Four frozen-shape arrays at 216 and 72 cells (`planted_arrays`), the positive boundary planted in its least favourable form (one cell at the margin, stricter than every cell), plus coverage; `precision_target_*`; the simulation showed the draft's 2,000 trials for `GROUPED_14C10` gave the positive token in about half the runs, so both geometries have 4,000 |
| R-statistics-14 | major | Diagnostic validity follows the mechanical optimism pair and never checks that the held-out cost tracks the true cost | Applied. `TRACKS` / `DIVERGES` on the interval of `delta_out - delta_true` with `diagnostic_cost_tolerance`, `diagnostic_minimum_tracking_fraction`; the reviewer's case is invalid by the truth table; planted held-out shift must invalidate |
| R-statistics-15 | major | The reporting verdict has no gate, no planted effect and no planted null; a `[0, 0]` interval passes | Applied. `reporting_minimum_nonzero_trials` and `reporting_minimum_compared_cell_fraction`; planted PLUS, MINUS and ZERO arms through the engine |
| R-statistics-16 | major | A frozen sentence claims any non-minimising rule narrows the gap; false, and tie-break cells make the criterion a strict reduction | Applied. Statement and Claim corrected ("narrows unless its true shortfall rises as much"); tie-break cells recorded per cell and in DISSENT 3. The example wording "tends to" was not used: the copy guard bans it |
| R-statistics-17 | major | The positive statements claim more than the criteria test | Applied. "on average", "in each compared cell", "by more than 0.005 normalised units on average" in both statements |
| R-statistics-18 | major | Config cannot produce the registry records; the pending sentence and experiment vocabulary live in prose | Applied. `registry_*`, `registry_outcomes` with status, limits and statement, `registry_common.not_run_statement`, `experiment_verdict_vocabulary`, `component_vocabulary`; records built from config pass V1 to V7 |
| R-statistics-19 | major | PIPELINE.md neither registered nor pinned | Applied. Registered with the protocol (`protocol_files`), `pipeline_spec_sha256` recomputed after the last edit; the draft guard requested of the root (section 11) |
| R-statistics-20 | major | Stress cells have no world tier; `cost_cells` undefined | Applied. `stress_worlds` 40; `cost_cells` = valid SENSITIVITY and STRESS cells that show a cost under the same rule, `m` their count |
| R-statistics-21 | major | The planted magnitude check is an algebraic identity and SE is undefined | Applied. Called an identity and checked to `planted_identity_tolerance`; a coverage test of a planted mean; SE = bootstrap SD (`standard_error_rule`) |
| R-statistics-22 | minor | Quantile interpolation method not declared | Applied. `interval_quantile_method` "linear" |
| R-statistics-23 | minor | Open or closed recovery interval; non-positive replicate denominators undefined | Applied. Closed; a resolved cell with a non-positive replicate denominator does not recover |
| R-statistics-24 | minor | Unusable trials in the bootstrap undefined | Applied. `unusable_trial_rule`: excluded for the rule and its pair, counts restricted, per-replicate divisor; tested |
| R-statistics-25 | minor | The bridge does not name the arm of M-05's shrinkage columns | Applied. `ORACLE_SHRINKAGE_FIRST` with every `n_i = G`; `bridge_columns` maps each column to its arm |
| R-statistics-26 | minor | `BIG` from the batch's world T only; "(>= 2)" false at zero | Applied. `encoding_base_rule`: the bound over point, world and reference T (and at least the target sum), `max(2, ...)`, X3's form; synthetic values can be negative, so a target-only bound would not do |
| R-statistics-27 | minor | Fixed-selection antisymmetry needs both directions used | Applied. Stated for splits with both directions used; the reference arm's used flag reads no world, so it is the same for both directions |
| R-statistics-28 | minor | Planted seeds not in config; cell set of the A2 planted tests open; one geometry and one tier planted | Applied. `planted_seed`, `planted_seed_rule`, `planted_tests`; cell sets named; `planted_geometries` both, `planted_tiers` both |
| R-statistics-29 | minor | Informative trial undefined in A2 | Applied. At least one informative direction; reported, gates nothing |
| R-statistics-30 | minor | The halves share the xT fit undisclosed; two table rows numbered 2 | Applied. Disclosed as a channel in Part B and "cannot show"; rows renumbered 1 to 6 |

### Football-data lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-football-data-1 | blocker | The badge word contains "worse", which the copy guard bans: every risk reply and the verdicts endpoint would be refused under every token | Applied with a part rejected. Badge "LESS OPTIMISTIC, COST BOUNDED" and tokens renamed; the banned-word test replaced by `scan_labels` and the boundary under every token; guard requested of the root. The proposed "NO LARGER TRUE SHORTFALL" is not used: the criterion admits a cost up to the margin, so it would overclaim |
| R-football-data-2 | blocker | The protocol's discard and unused-direction rules count goalkeepers and excluded players, against T2 and the pipeline | Applied (as R-statistics-4); the audit's "skipped for a discarded world" branch dropped |
| R-football-data-3 | blocker | The audit is written against an interface the solver does not have and would pass with nothing compared | Applied (as R-statistics-5) |
| R-football-data-4 | blocker | The planted structure check cannot pass (four blocks against eight); `diagnostic_valid` undefined; RANDOM_MIX's held-out excess not guaranteed | Applied (as R-statistics-2). RANDOM_MIX is replaced in the split check by `REFERENCE_WORST_MIX`, whose held-out excess is non-negative on every coined direction by construction, instead of a run-time precondition that could stop the run |
| R-football-data-5 | blocker | The scope omits the requirement set and says nothing of minima, locks or exclusions, which the router accepts | Applied. `token_scope` and the `risk_rule` scope sentence; the router change (`E13_SCOPE`, `_in_e13_scope`) is a registration-commit request (PIPELINE 11, OPEN QUESTION 2) |
| R-football-data-6 | blocker | T4 and T7 not applied; the split statements describe a display that does not exist | Applied (as R-statistics-7 and -9); the split statements now speak of E-13's research check |
| R-football-data-7 | blocker | T3 not applied | Applied with a part rejected. Both oracle files are in `risk_solver_oracle_tests` and hashed, as T3 rules; the proposal to keep a separate list of files passed to pytest is not taken: pytest collects nothing from `tests/xi_exact_oracle.py`, and both paths together collect the nine tests (checked) |
| R-football-data-8 | major | GATED_SQUAD treats appearances as whole matches, understating the noise the minutes-weighted estimator gives; "appear" undefined | Applied. `GATED_MINUTES` (round(minutes / 90), root-counted) is primary and the A2 profile; `GATED_APPEARANCES` a sensitivity variant; appearance = positive reconstructed minutes |
| R-football-data-9 | major | The COSTS statement says "declared shortfall", a tautology that misstates the criterion | Applied. "a larger average largest normalised shortfall than Balance's, by more than 0.005, against known values ... or on held-out halves" |
| R-football-data-10 | major | Neither synthetic design has the positional structure of the side requirements | Applied with a part rejected. The reviewer's second form: the positive statements say "no positional structure", the noise table and "cannot show" name the real structure. A structured geometry is not added: its side means would be new declared constants with no basis, and the primary design would move on a guess |
| R-football-data-11 | major | ALTERNATING likely splits the season by venue | Applied. Home matches per half reported (structure); venue confound stated; no product split (T7) |
| R-football-data-12 | major | One set of structural counts for both snapshots; 480 is not S | Applied. Per-snapshot `expected_*` and `expected_selection_count`, root-counted; S in the cost estimate |
| R-football-data-13 | major | VerdictRecord fields missing from config | Applied (as R-statistics-18) |
| R-football-data-14 | major | The pipeline depends on documents not in the repository and is not pinned | Applied. Every ARCH-SPEC, PRODUCT-MATCHDAY, HARDENING, INTERFACES and maps citation replaced by the shipped module (PIPELINE 1); pinned; guard requested |
| R-football-data-15 | major | Split-mean denominator undefined | Applied (as R-statistics-3) |
| R-football-data-16 | major | The run order put the audit on real numerators before the structure check the checklist requires first | Applied. Load, oracle gate, structure check, audit, Part B, in both files; "evaluated" defined |
| R-football-data-17 | minor | The shipped `dataset_hash` covers every column, against ROOT 4's column lists | Applied. Whole-file read as the named exception (`data_read_rule`), peak memory printed |
| R-football-data-18 | minor | The reliability bracket compares unlike quantities | Applied. Reliability ranges over each exposure range; "brackets the band" dropped |
| R-football-data-19 | minor | Independent exposure not listed as an assumption | Applied. A row in the noise table |
| R-football-data-20 | minor | `team_id` reaches the artifact through the config echo, against the identifier rule | Applied. `results_allowed_identifiers` |
| R-football-data-21 | minor | Exposure not defined against the minute reconstruction | Applied. Positive reconstructed minutes; the reconstruction's properties declared |
| R-football-data-22 | minor | "overstates shortfall for a fixed XI" holds on average only | Applied |
| R-football-data-23 | minor | Antisymmetry needs both directions used | Applied (as R-statistics-27) |
| R-football-data-24 | minor | The held-out half shares the xT fit and the minima | Applied (as R-statistics-30) |
| R-football-data-25 | minor | Two config values without derivation | Applied. `exposure_subset_rule` (positions round(i × 13 / 7)) and `minimum_level_rule`, checked to reproduce every vector and level |
| R-football-data-26 | minor | The bridge does not name its shrinkage arm | Applied (as R-statistics-25) |
| R-football-data-27 | minor | The default progression-only request is always outside the scope, unsaid | Applied. Claim, Product consequence and "cannot show" |

### Constitution lens

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| R-constitution-1 | blocker | The badge word is banned; the refusal holds under every token, PENDING included | Applied. Badge exactly as proposed, tokens renamed, NOT_WORSE gone from the prose; the test replaced; guard requested of the root; the reviser's scratch guard finds 0 refusals and refuses a planted "NOT WORSE" under 6 of 6 tokens |
| R-constitution-2 | blocker | The planted structure check can never pass | Applied (as R-statistics-2) |
| R-constitution-3 | blocker | The audit reads `OPTIMAL`, lacks required arguments and a minimum, and skips discarded worlds | Applied (as R-statistics-5); used and discarded world ids compared; DISSENT 3 and OPEN QUESTION 1 of the draft closed |
| R-constitution-4 | blocker | The withdrawn discard rule kept | Applied (as R-statistics-4) |
| R-constitution-5 | blocker | T3 pins missing | Applied (as R-statistics-6); the gate hashes both files and pytest collects the tests from one |
| R-constitution-6 | blocker | An unconditional figure-note consequence for `risk_report` | Applied (as R-statistics-7); the results commit's figure is labelled as the mean largest shortfall over the k tail worlds |
| R-constitution-7 | blocker | The scope lacks the requirement set; the default request unsaid | Applied (as R-statistics-8 and R-football-data-27) |
| R-constitution-8 | blocker | A product consequence for a split tool T7 forbids, unlocking numbers on execution | Applied (as R-statistics-9); only a `may_gate` verdict may unlock a number, in a later change set |
| R-constitution-9 | major | VerdictRecord fields missing; PENDING asked as an outcome, against V2 | Applied (as R-statistics-18); `limits` true for the four ESTABLISHED tokens |
| R-constitution-10 | major | PIPELINE.md neither registered nor pinned; no draft guard | Applied (as R-statistics-19) |
| R-constitution-11 | major | No registration-commit plan; README declared untouched | Applied. PIPELINE 11 in E-11's form: before registration, the registration commit (records, router, tests, prose, README row), the pipeline commit, the stamp, after the run |
| R-constitution-12 | major | Per-match components re-implemented beside a parity-tested product implementation | Applied. `snapshots.prior_frames` and `rate_components` imported; `snapshots.py` pinned; interface 8 gone |
| R-constitution-13 | major | The prior-exposure table predates the built solver and router | Applied. Rows for the oracle suite, the slow Madrid test, the timing script, the risk panels, the first review's and this revision's synthetic checks; the root confirms in the registration commit |
| R-constitution-14 | major | The oracle gate is vacuous on Windows | Applied. JUnit counts must equal `risk_solver_oracle_expected` (9 passed, 0 skipped, checked on Linux); POSIX required; POSIX commands |
| R-constitution-15 | major | Real numerators read by the audit before the structure check; the guard does not cover the audit | Applied. Order fixed; the hash demand moved into `load_split_inputs`, checked again by the two accessors |
| R-constitution-16 | major | The oracle summary carries a wall-clock value | Applied. Counts and file hashes only; byte-equality test |
| R-constitution-17 | major | Split-mean denominator undefined | Applied (as R-statistics-3) |
| R-constitution-18 | major | Diagnostic validity does not test the cost pair | Applied (as R-statistics-14); the reviewer's case is invalid by the truth table |
| R-constitution-19 | major | The scope says nothing of minima, locks or exclusions | Applied. The first option: the scope sentence states the tested minima (exact integer targets at the four multipliers) and no lock or exclusion, and the router change is requested; "cannot show" extended |
| R-constitution-20 | major | Structural stops shared by both snapshots | Applied (as R-football-data-12) |
| R-constitution-21 | major | The statements misname their numerator | Applied (as R-football-data-9); "average largest normalised shortfall" in every risk statement |
| R-constitution-22 | major | No planted check of the reporting verdict or of diagnostic validity | Applied (as R-statistics-14 and -15) |
| R-constitution-23 | major | Unusable trials and one-direction A2 trials undefined | Applied (as R-statistics-24 and -29) |
| R-constitution-24 | minor | "Narrows the gap" stated as a fact | Applied (as R-statistics-16) |
| R-constitution-25 | minor | Overclaims being M-05's named next experiment | Applied. E-13 does the "selection and reporting separately" part; no out-of-sample shrinkage |
| R-constitution-26 | minor | Two rows numbered 2; experiment vocabulary in prose; one sentence for two `risk_report` tokens; a pending sentence false after the run | Applied. Rows 1 to 6; `experiment_verdict_vocabulary`; an INCONCLUSIVE statement of its own; not-run statement "No E-13 result applies here: E-13 has not run, or the request lies outside what it tests." |
| R-constitution-27 | minor | The TRUTH_MIX magnitude is an identity; scalar `pvals` raise in numpy 2.5 | Applied (as R-statistics-21); `np.full(h, 1 / h)` everywhere (numpy 2.5.4 raises on a scalar, checked) |
| R-constitution-28 | minor | Antisymmetry, `team_id` and the GROUPED minima | Applied (as R-statistics-27, R-football-data-20 and -25) |
| R-constitution-29 | minor | Bridge arm, unreachable rehearsal gates, undisclosed shared inputs, stale interfaces 4 and 10 | Applied. Bridge arm named; `rehearsal_design` gates; shared inputs disclosed; interfaces settled (PIPELINE "Interfaces resolved") |

### Items settled before registration (ROOT-DECISIONS 2.11 and the task's three items)

| Item | Where it is applied |
|---|---|
| T1 built signatures | PIPELINE 1 (the `declared_risk_selection` keywords, `RiskSelection` fields, status values), 2.6 (`_risk_call`, `_risk_world_pairs`, certification, the five checks), "Interfaces resolved" (none assumed); config `solver_*` |
| T2 shipped discard rule | protocol Fixed definitions and Part B; PIPELINE `world_valid`, `weighted_rates`, `test_discard_rule_is_the_shipped_one`, `test_part_b_discard_equals_world_losses` |
| T3 oracle and source pins | config `risk_solver_oracle_tests` (both files), `source_paths` (`kernel.py`, `tradeoffs.py`, also `ceilings.py`, `xi/__init__.py`, `snapshots.py`); PIPELINE 5 |
| T4 `risk_report` conditional | protocol Product consequence; config `risk_report_after_run`; PIPELINE 10, 11 |
| T5 requirement set in the scope | config `token_scope` and `registry_risk_rule.scope`; protocol Claim, Product consequence, "cannot show" |
| T6 the menu | `tail_counts` unchanged; the router tests that read it pass (`test_e13_scope_equals_the_draft_config`, `test_the_tail_menu_is_the_e13_draft_s`) |
| T7 research code only | `product_split_rule` and interface 7 deleted; config `split_sample_after_run`; the split statements speak of E-13's check |
| Names of shipped code | Every name PIPELINE 1 cites was imported and checked on 18 October 2026: `xi.QUANTIZATION`, `solver._q`, `_eligible`, `_applies`, `solve_xi`, `risk.declared_risk_selection`, `world_losses`, `squad/kernel.py`, `historical.build_snapshot`, `fit_prior_xt`, `load_snapshot`, `SEED`, `snapshots.prior_frames`, `rate_components`, `snapshot_metrics`, `profiles.uncertainty.shared_match_weights`, `_per_match_components`, `features.spec.SPECS`, `decision_lab.decision_inputs`, `digests.lf_sha256`, `lf_sha256_text`, `domain.verdicts`, `runtime.finalize`, `labels.scan_labels`, `thesis.banned_key_paths(parts=)`, `providers.base.assert_may_host`, the conftest fixtures `corpus_root` and `spain_frames`, and M-05's harness `experiments/run_optimizer_curse.run`. Names the draft used that do not exist are gone: the risk solver's `solution_status`, `assignments` and `time_limit`, the "HONEST EVALUATION" tool, the work-package labels and the documents outside the repository. The functions of `risk_selection.py` are new and are not claimed to exist |
| Copy guard | Every registry text (three scopes, three badge words, three non-claims, the not-run statement, eleven statements) passes `runtime.finalize` under `PENDING` and every token and `scan_labels`; no key of the config is banned with `BANNED_KEY_PARTS` or names a provider |

### The reviser's synthetic checks (scratch scripts, not committed)

No corpus file was opened and no declared-risk rule was computed on any frozen cell.

| Check | Result |
|---|---|
| Registry records from the revised config, every family under `PENDING` and every token, through `VerdictRecord` and `runtime.finalize` | 0 refusals; a planted badge "LESS OPTIMISTIC, NOT WORSE" is refused under 6 of 6 `risk_rule` states; a planted "tends to" is found by `scan_labels`; every sentence of every registry text occurs verbatim in the protocol |
| The draft config through the same records (the reviewers' check, rerun) | every `risk_rule` state refused on `claim_token: worse`, the two ESTABLISHED tokens on `badge: worse` too |
| The revised token rules, exhaustively over two components and on 200,000 random six-component cases | no component cost under a positive or INCONCLUSIVE token; the table is total over the 20 pairs |
| Frozen-shape decision arrays (PIPELINE 9) | at 216 cells: cost token at the boundary 191 of 4,000, positive at the least favourable boundary 116 of 4,000, positive at 6 SE 3,969 of 4,000, cost at margin + 6 SE 3,981 of 4,000; at 72 cells 199, 101, 3,989 and 3,990; the percentile bootstrap on 40 seeds agrees; the draft's 2,000 trials gave the positive token 2,041 of 4,000 |
| A1 planted arms on the frozen design (BALANCE and pseudo-rules only, a stand-in for `GATED_MINUTES`, seeds not E-13's) | `TRUTH_MIX`, `RANDOM_MIX`, `IDENTICAL` classified as required in 10 of 10 seeds, 36 of 36 cells compared |
| Structure check on an invented Madrid-like structure, both snapshots, 250 splits | the three pseudo-rules classified as required in 3 of 3 corpora; 500 used and at least 222 informative directions per block |
| The risk oracle on Linux, both files (`pytest --junitxml`) | 9 tests, 0 failures, 0 errors, 0 skipped; collection of both paths gives the nine tests |
| Router tests that read this config | `test_e13_scope_equals_the_draft_config` and `test_the_tail_menu_is_the_e13_draft_s` pass |
| Count derivations | `exposure_subset_rule` and the spanning rule reproduce every vector of `geometries`; `minimum_level_rule` gives 18.0, 19.46 and 20.92 |

### For the audit

The revision has not been audited. By T8, partitioned audits with a refuter per claimed
blocker follow, repeated until no scope has a blocker. Before registration the root fills the
counts of `counted_by_root_before_registration`, checks the items of
`verified_by_root_before_registration` and states the prior-exposure items of PIPELINE 11 in the
registration commit; it also decides the router request (OPEN QUESTION 2) and whether
`split_sample_diagnostic` stays a claim (OPEN QUESTION 3).
