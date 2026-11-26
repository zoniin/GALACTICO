# Architecture

## Layers

The tree below is the long-term module map, not a completeness claim. `bridge`,
VISION, learned role fit, embeddings and opponent utility remain research/stubs.

```
providers/   adapters; provider quirks terminate here
ingestion/   raw -> provider-neutral schema -> Parquet; the Wyscout tag sidecar beside it
storage/     DuckDB over Parquet, three tiers kept apart
features/    quality / style / spatial / physical / team
reliability/ the gate; runs before axes are designed
models/      xt, embeddings, role_fit, similarity, complementarity, opponent
bridge/      LIVE aggregates -> LAB axes, with measured error
optimization/xi, squad, transfers, sensitivity
vision/      calibration, detection, tracking, projection, shape
validation/  pre-registered experiments and baselines
api/         FastAPI over prepared state
```

## Pages, shell and design system

Two apps serve the pages: the full local app (`galactico.api.player_lab:app`) and the hosted
one (`galactico.match_centre.public:app`, deployed on Vercel). Both serve every page through
one shell (ADR-0033).

| Module or file | Responsibility |
|---|---|
| `site_nav.py` | The shell: skip link, header (wordmark, navigation, season chip, theme switch), the phone tab bar and the footer ("About the numbers", the page's data credits). Fills the `<!--shell:head-->`, `<!--shell:header-->` and `<!--shell:footer-->` placeholders of every page file. The navigation is deployment-aware: it lists a destination only when the serving app answers its route. Standard library only, so the hosted function ships it (`vercel.json` `includeFiles`) |
| `match_centre/routes.py` | The current-season pages and their APIs, included by both apps: `/` and `/match-centre` (Matches), `/match-centre/leagues` (Table), `/match-centre/scouting`, `/lineup`, `/about`; an old Player Lab link to `/` opens `/player` where the app serves it |
| `api/about.py` | The archive's sections of "About the numbers", read from the registries where they are defined; the local app hands them to the shell |
| `web/tokens.css`, `base.css`, `components.css` | The design system: every colour literal and its light and dark role (`tokens.css`); fonts, type scale, links and the focus ring (`base.css`); the shell and the `ui-*` components (`components.css`). Cascade order `tokens, base, legacy, components, page` |
| `web/labs.css`, `labs-shared.css`, `planning.css`, `xi-extensions.css`, `match-centre.css`, `studio-shell.css`, `studio.css`, `goal-scout.css` | The sheets written before the system, in the `legacy` layer, reading its roles (`labs.css` re-points the labs' old names at them) |
| `web/theme.js` | Applies a reader's stored theme choice before paint |

| Page file | Route | Place in the navigation | Season |
|---|---|---|---|
| `match-centre.html` | `/`, `/match-centre` | Matches | 2026/27 |
| `leagues.html` | `/match-centre/leagues` | Table | 2026/27 |
| `scouting.html` | `/match-centre/scouting` | Players | 2026/27 |
| `studio.html` | `/lineup` | Lineup | 2026/27 |
| `index.html` | `/player` (local) | Players | 2017/18 archive |
| `match.html` | `/match` (local) | Matches | 2017/18 archive |
| `xi.html` | `/xi` (local) | Lineup | 2017/18 archive |
| `squad.html` | `/squad` (local) | Squad & signings | 2017/18 archive |
| `transfer.html` | `/transfer` (local) | Squad & signings | 2017/18 archive |
| `about.html` | `/about` | the footer of every page | — |

## Implemented historical decision path

`api/player_lab.py` serves Player Lab at `/player` and registers `api/decision_lab.py`. Player
Lab is frozen since ADR-0011, except the corrections of ADR-0025 and ADR-0027
(October 2026).
This path renders three code-native pages under `web/` (the planning path below
adds two); JavaScript presents server decisions and never computes eligibility,
coverage or an objective.

| Module | Responsibility |
|---|---|
| `profiles/` | Versioned season estimates, gates and shared-match uncertainty |
| `match_lab/service.py` | Public Pappalardo-only loading, retained provider tags, retrospective xT and file hashes |
| `match_lab/model.py` | Provider-neutral `MatchIntelligence`: timelines, shot locations, positive pass-xT flow, inferred networks and contribution vectors. On a player row a registry construct is served only inside its declared context; the timeline, the network and team rows are not gated |
| `optimization/historical.py` | Strict prior-date snapshot, independent pre-cutoff xT fit, versioned eligibility, heuristic minima and coherent team-match worlds |
| `optimization/xi/domain.py` | Typed candidates, role-slot templates, requirements, assessments and `XIResult` |
| `optimization/xi/solver.py` | Exact quantized CP-SAT; lexicographic deficits, certification, tie-aware membership, removal and candidate-injection re-solves |
| `optimization/xi/ceilings.py`, `conflict.py`, `frontier.py`, `risk.py` | The exact additions of ADR-0030: the attainable range of each requirement sum; a certified minimal conflicting set in the arithmetic of the solve it explains; the complete nondominated requirement-sum vectors of declared dimensions; declared-risk selection over shared worlds. Each is checked against the brute-force oracle `tests/xi_exact_oracle.py`, written by an author who built none of them |
| `api/xi_extensions.py` | Their router: one corpus-free menu route and four POST routes through `runtime.finalize`, the declared-inputs ledger and the build-gated snapshot loader |

`GET /api/matches` and `/api/matches/{id}` expose the historical match artifacts;
`/{id}/{timeline,shots,network,players,flow,teams}` expose individual sections.
`GET /api/xi/scenarios`, `POST /api/xi/solve` and `POST /api/xi/sensitivity`
serve the decision model. There is no persistent XI store or separate explain
service: the solve returns the contributions, requirements, changes and provenance.

Match Lab's full-season xT is retrospective and cannot feed a historical decision
backtest. XI snapshots refit only on earlier calendar dates. All world inputs,
requirement inputs, formation rules, solver versions and seeds enter provenance;
missing exposure stays missing. Necessary–possible membership bounds include
equivalent optima; a deterministic displayed XI does not resolve those ties.

Opponent conditioning is designed to change requirements, not player ratings.
Only its descriptive team inputs exist. Candidate injection is a transfer
foundation, not a validated recruitment ranking. No universal utility, overall
match rating, learned role adjustment or robust-risk product mode is implemented.

## Implemented planning path

Squad Lab and Transfer Lab stand beside the historical decision path and edit none
of it. `historical.py`, the XI solver and the xT grid are imported from, never
changed: their bytes are hashed into published experiment results.

| Module | Responsibility |
|---|---|
| `storage/public.py` | The one guarded reader of the public frames: hosting guard first, provider column checked, explicit files only |
| `ingestion/sidecar.py` | The Wyscout tags and match-sheet fields the neutral frames drop, as three tables per competition joined on `event_id`; facts with the provider's meaning, no construct (ADR-0028) |
| `optimization/snapshots.py` | Pre-decision snapshot for any club and decision match or cutoff date under a named eligibility rule set; byte parity with `historical.build_snapshot` for Madrid; `TEAM_MATCHES` or `LEAGUE_MATCHES` worlds |
| `optimization/reference.py` | League distributions of starting-XI requirement sums before a cutoff (descriptive) |
| `optimization/squad/kernel.py` | The exact lexicographic shortfall as a linear epigraph; the same integers as `solve_xi`; conservative floor/ceil for hard statements |
| `optimization/squad/depth.py`, `stress.py`, `brief.py` | Slot depth with attributed drops; exact k-absence stress; the role brief (inverse problem per slot) |
| `optimization/transfers/universe.py`, `injection.py`, `retention.py` | Gated candidate universe; exact forced-inclusion re-solves; the break-even carry-over fraction |
| `domain/evidence.py` | The one mapping from shipped vocabularies to `EvidenceClass`, and composition by the weakest |
| `domain/verdicts.py` | One typed record per preregistered claim; a LOCAL-tier record can label, never gate. Holds E-11's sixteen LOCAL records (ADR-0029) and E-10's seven PUBLIC records (ADR-0031), registered and not run |
| `domain/thesis.py` | Walks any payload for rating-like keys by exact key and, at the planning boundary, by key part |
| `domain/labels.py` | The copy guard: words a served string may not contain outside a named denial. Run on the string values of every new 200 reply outside its provenance blocks |
| `api/runtime.py` | How every new request runs: error mapping, budgets that start with the request, result cache with single-flight, sixteen requests past the cache lookup and two long computations at a time, the boundary check `finalize` (providers, keys, served words), NaN-free responses |
| `api/shell.py` | What every new lab page shows: the not-measured list, evidence and verdict payloads, the copy guard's scan of visible text. The navigation is `site_nav.py`'s |
| `api/planning.py`, `squad_lab.py`, `transfer_lab.py` | The declared planning problem, the build gate (one build per key, the key holding the identity of the corpus files read; two at once; 429 after the wait), cache keys on the request as resolved, and the two lab routers |

Every new 200 reply passes `runtime.finalize`, computed or read from the result
store. The provider set at any depth of the payload must be exactly the hosted
one. No key is one of thirteen banned keys, and no key holds as a part one of
rating, ratings, rank, ranks, ranking, ranked, merit or overall; a rating under
another name passes. The copy guard runs there too (`domain/labels.py`): in every
string value outside a provenance block a word such as "best", "weakness" or
"forecast" may appear only inside a named denial. It reads no key and no string
under provenance, and an error body passes none of these checks. Product code
imports nothing from `galactico.validation` or `experiments`;
`tests/test_research_firewall.py` parses the imports.

`GET /api/evidence/verdicts` returns the registry. `/squad` and `/transfer` and
their endpoints are listed in the routers. The two planning pages compute nothing
about football; `web/labs-shared.js` and `web/planning.js` are render functions
over server payloads.

## Research pipelines

Each preregistered experiment has its pipeline under `galactico/validation/` and a
runner under `experiments/`. They are built and tested on synthetic data only, run on
the real corpus once after the protocol commit, and firewalled from product code
(`tests/test_research_firewall.py` lists every one). E-11's, built against its frozen
`PIPELINE.md`, has not run:

| Module | Responsibility |
|---|---|
| `validation/sb_reader.py` | LOCAL tier: the licensed provider's double-coded folders read from their match index only; team sheets, events, the closed vocabulary and the folder digest |
| `validation/provider_crosswalk.py` | The public provider's sheets and people; match and team-sheet crosswalks and the name-and-nationality link, in memory only; no function takes an event frame |
| `validation/provider_inputs.py` | Both providers' events harmonised under two readers, reference xT surfaces on the frozen fit, player and team inputs, event pairing and divergence tables |
| `validation/provider_agreement.py` | Rank and level agreement, one weight array per axis, the decision rule (`classify`), the permuted controls, admission and the registry tokens |
| `validation/provider_agreement_synthetic.py` | Planted corpora, population values and the acceptance run |
| `experiments/run_provider_agreement.py` | `preflight`, `acceptance` and `execute`, with the refusal checks of the protocol; writes aggregates only, under the gitignored local root |

## The provenance core

`galactico.domain.provenance` holds the project's defining abstraction.
`MetricResult` carries value, evidence class, uncertainty, sample size,
reliability and a provenance DAG, and arithmetic propagates all of them.

Three laws, each covered by property tests:

1. **Composition never strengthens.** `(a + b).evidence >= max(a, b)`. No
   sequence of operations can turn a prediction into an observation.
2. **Correlation is preserved where it is known.** Two results carrying draws from
   the same bootstrap replicate set combine element-wise. Different replicate sets
   fall back to quadrature and record `independence-assumed`, because for football
   metrics derived from the same events that assumption is usually false.
3. **Precision follows the uncertainty.** `render()` derives decimal places from
   the standard deviation. Quoting 78.43 when the sd is 6 is a lie about
   precision and is not reachable through the public API.

`explain()` returns value, evidence, grade, reliability, sample size, assumptions
and the full lineage. The question "where did this number come from" always has a
complete answer.

## Comparability

`MetricDefinition.comparable_across` declares which providers may be pooled for a
given metric; `assert_comparable` raises otherwise. Definitions are
content-addressed over formula, inputs and normalisation, so changing what is
computed changes the version hash and invalidates stored results.

## Data tiers

`PUBLIC` may be hosted and is what the demo runs on. `REFERENCE_ONLY` is reachable
and not ours to use: never ingested, never hosted, no adapter, and an entry at
that tier cannot be written with a permission on. `LOCAL_LICENSED` is downloaded
at runtime into a gitignored cache and never served. `TRIAL` is time-boxed and
never a dependency. The readers of the public frames call `assert_may_host`.
`assert_may_ingest` and `assert_may_commit` are the guards for a fetch and for a write
to the tree; nothing outside the tests calls either yet. `scripts/check_licensing.py` guards
the repository in CI.

## Storage

DuckDB over Parquet. Read-heavy analytical workload, one writer, no server to run
or back up. Partitioned by competition-season and provider, because those are the
boundaries that matter for both queries and licensing.

## Testing

Eight categories, and one of them behaves differently from the rest.

| Category | Fails the build? |
|---|---|
| Unit, data/schema, statistical, regression, solver, leakage, licensing | yes |
| Research acceptance | **no** |

A research acceptance test asks whether a model beats its baseline. When it does
not, the model is wrong, not the code. Those are marked `@pytest.mark.research`
and reported separately: a null result is an output, and a build that goes red
because reality disagreed with a hypothesis trains you to stop asking.

