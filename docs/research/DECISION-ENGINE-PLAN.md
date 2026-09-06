# Decision Engine: claim and falsification plan

Council synthesis, recorded before the first integrated solve.

## XI claim

Given a declared candidate set, eligibility rules and tactical requirements,
identify feasible assignments with the least stated structural shortfall. This
does not identify the best football team or a causal alternative match result.

The first solver uses explicit role slots, one player per slot and one slot per
player. CP-SAT is already a project dependency. Its integer formulation is
certified against an independent exhaustive oracle on tiny instances. Report
quantization, status and bounds; an unproven incumbent is only FEASIBLE.

BALANCE minimizes the maximum normalized shortfall, then the total normalized
shortfall. Normalizers and priority order are tactical policy, not discovered
football utility. SATISFY makes the declared minima hard. No arbitrary quality
sum, role interaction uplift, chemistry or learned continuity coefficient enters.
Equal solutions remain equal; administrative tie-breaking is not player evidence.

Use observed pre-cutoff Madrid appearances for the candidate set, not current-team
metadata. Filter league events before fitting xT as well as before constructing
player properties. Eligibility is an explicit football rule. Historical pass
rates are carried into a hypothetical XI as a modeling assumption, not a causal
forecast. Injury/suspension availability is unknown.

Shared match worlds perturb all players and all features together. Preserve
world IDs and zero-exposure holes. Selection frequency is model stability under
resampling, not a probability of being a better player. Equivalent-optimum
membership must qualify any stable-core claim, especially for unmeasured keepers.

## Match claim

Describe what the event corpus records in a match: lineups, selected timeline,
shots, positive completed-pass xT flow, pass-origin distributions, player vectors
and an explicitly inferred pass network when direct recipients are absent.
Match totals do not inherit season-level reliability or persistent-ability claims.
No xG is fabricated for Wyscout. No rolling statistic is called momentum.

The scalar council compares event-value accounting, role standardization and
outcome prediction with a contribution vector. Positive pass xT is exactly its
own baseline; adding key-pass xT double counts a subset of passes. Without a
validated utility/target, no overall match rating ships. A runnable baseline audit
will document redundancy; low correlation alone cannot establish validity.

## Adversarial acceptance

Test impossible eligibility, duplicate players, locked/excluded conflict, arbitrary
candidate ordering, exact ties, ineligible superstars, missing estimates, noisy
and correlated teammates, cascading lock changes and changed requirement hashes.
Compare the solver against a separate brute-force implementation. Real-data smoke
checks establish only structural sanity, never manager superiority.

Run browser interactions and inspect actual screenshots. The frontend renders
server decisions; it never decides coverage, eligibility, uncertainty or winners.
Keep Player Lab's gate, style and selected-player color invariants.

Historical selection agreement compares against previous XI and prior minutes;
it is manager similarity, not correctness. Outcome association, formation inference,
continuity, role transition models and robust regret remain separate experiments.
Expected regret is equivalent to expected objective optimization for a fixed
feasible set; it is not a new product mode. Worst-case/CVaR require declared risk
preferences and are not implied by bootstrap frequencies.

## Primary references used by the independent council

- [CP-SAT integer modeling and solver status](https://developers.google.com/optimization/cp/cp_solver).
- [Pappalardo event schema and corpus license](https://figshare.com/articles/dataset/Events/7770599).
- [Expected threat's movement-value definition](https://karun.in/blog/expected-threat.html).
- [VAEP framework](https://dtai-static.cs.kuleuven.be/sports/vaep/): a different
  calibrated event-value research path, not an already validated match rating here.
