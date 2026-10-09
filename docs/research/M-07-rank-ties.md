# M-07: a rank that depends on the order of the rows

Erratum to the ordering figures (ρ) of Stage 1, Stage 1B and Stage 1C.

The confound audit reports how much of a construct's ordering survives adjustment
as a rank correlation. It was called Spearman. For tied data it was not: the same
rows in another order gave another number. Average ranks are the definition from
now on. The published reports are records and are not rewritten; this note is the
correction.

One paragraph below reports the StatsBomb half of Stage 1C, in aggregate.

<img src="../assets/statsbomb/statsbomb-logo.png" alt="StatsBomb" width="170">

Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data
User Agreement. This analysis is formed from StatsBomb data and carries the
StatsBomb logo as clause 1.4 of that agreement requires. No StatsBomb data and no
table derived from it is in this repository.

## What was wrong

`_spearman` ranked with `np.argsort(np.argsort(x))`. Tied values then take
distinct ranks in whatever order the sort leaves them.

Chance creation is the threat added by a player's completed key passes. Between
60 and 65 of the 290 to 345 players in each league completed none and sit at
exactly zero. Their sixty-odd ranks were handed out by position in the array.

The Stage 1B chance-creation figure for each league, recomputed over 1,000
orders of the same rows:

| League | Published | Lowest | Highest | Corrected |
|---|---:|---:|---:|---:|
| ESP | 0.8686 | 0.8626 | 0.8741 | 0.8712 |
| ENG | 0.9068 | 0.8987 | 0.9121 | 0.9090 |
| ITA | 0.8892 | 0.8811 | 0.8959 | 0.8917 |
| GER | 0.8888 | 0.8821 | 0.8973 | 0.8931 |
| FRA | 0.8896 | 0.8805 | 0.8922 | 0.8894 |

Each published figure is one draw from its range. The corrected figure is the
same number in all 1,000.

## Why nothing caught it

Every test of the audit drew its metric from a continuous distribution. No two
values were equal, and without ties the two rankings agree to the last bit. Real
chance creation is continuous too, except at zero. This is
[M-01](M-01-self-consistent-tests-can-be-wrong.md) again: the synthetic generator
lacked the one property of the real data that mattered.

The function was never compared with an independent implementation. scipy is not
a dependency, and nobody had written the definition out.

And almost nothing depended on it. The Stage 1 decision rule reads the
reliability bound, the confound R² and the closest baseline. It does not read ρ.
The one frozen gate that does, T3 of E-02, was run on an index with no tied
value. A number that gates nothing is a number nobody attacks.

It was found in October 2026, when average ranks were added for count-valued
candidates and the published Spain figures were recomputed to confirm that none
moved. Chance creation moved.

## The corrected figures

Every published ordering figure was recomputed twice from the local corpora, on
the arrays the published pipeline hands to the audit: once with the ranks it was
published with, once with average ranks.

| Record | Figures | Reproduced with the old ranks | Have a tied value and move |
|---|---:|---:|---:|
| Stage 1, Spain (`experiments/stage1_axes.json`) | 7 | 7, bit for bit | 2 |
| Stage 1B (`experiments/replication.json`) | 35 | 35, bit for bit | 8 |
| Stage 1C, Wyscout columns (`experiments/external_replication.json`) | 20 | 20, bit for bit, on the input described under "Found on the way" | 9 |
| Stage 1C, StatsBomb columns | 20 | 20, bit for bit | 12 |
| E-02, test T3 (`results.json`) | 1 | 1, bit for bit | 0 |
| Stage 1, grid sensitivity (printed only) | 5 | 5, to the three decimals printed | 0 |

Stage 1's seven figures are the Spain rows of Stage 1B. The report prints them to
two decimals, and at two decimals none changes: 0.87 and 0.97 stay 0.87 and 0.97.

**Stage 1B** (the two ESP rows are also Stage 1's)

| Construct | League | Tied | Published | Corrected | Difference |
|---|---|---:|---:|---:|---:|
| `chance_creation` | ESP | 64 | 0.868563 | 0.871168 | +0.002604 |
| `chance_creation` | ENG | 65 | 0.906808 | 0.908954 | +0.002146 |
| `chance_creation` | ITA | 65 | 0.889226 | 0.891736 | +0.002510 |
| `chance_creation` | GER | 60 | 0.888765 | 0.893134 | +0.004369 |
| `chance_creation` | FRA | 61 | 0.889558 | 0.889365 | -0.000193 |
| `half_space_share` | ESP | 2 | 0.973775 | 0.973773 | -0.000002 |
| `half_space_share` | FRA | 2 | 0.960543 | 0.960553 | +0.000010 |
| `width` | GER | 2 | 0.989539 | 0.989550 | +0.000011 |

`progression`, `progression_per_action`, `ball_retention` and `verticality` have
no tied value in any league. Their 20 figures, and the other 7 of the two style
constructs, are the same number under both rankings.

**Stage 1C, Wyscout columns** (the harmonised estimator, four leagues)

| Construct | League | Tied | Published | Corrected | Difference |
|---|---|---:|---:|---:|---:|
| `chance_creation` | ESP | 64 | 0.899189 | 0.901755 | +0.002567 |
| `chance_creation` | ENG | 65 | 0.925167 | 0.929447 | +0.004281 |
| `chance_creation` | ITA | 65 | 0.908403 | 0.910831 | +0.002428 |
| `chance_creation` | FRA | 61 | 0.908562 | 0.909104 | +0.000542 |
| `half_space_share` | ESP | 6 | 0.971112 | 0.971110 | -0.000001 |
| `half_space_share` | ENG | 8 | 0.942470 | 0.942469 | -0.000001 |
| `half_space_share` | FRA | 2 | 0.935407 | 0.935415 | +0.000008 |
| `width` | ENG | 5 | 0.984156 | 0.984149 | -0.000007 |
| `width` | ITA | 2 | 0.990689 | 0.990693 | +0.000004 |

`progression` and `progression_per_action` have no tied value in any league.
Their 8 figures and the other 3 are the same number under both rankings.

**Stage 1C, StatsBomb columns.** Twelve of the twenty figures have a tied value
and move. The largest absolute difference is 0.000428, a tenth of the Wyscout
one; 15 to 23 players per competition sit at zero chance creation, not sixty.
The figures themselves are not printed here.

**E-02** has no tied value among its 306 players. T3 is 0.594833505570755 under
both rankings.

**The grid table** of the Stage 1 report has no tied value. Its five figures and
its top-10 and top-25 counts reproduce as printed.

The largest absolute difference anywhere is **0.004369** (Stage 1B, chance
creation, Germany).

E-01 quotes two rank correlations. They were computed before this module existed,
by code that was never committed. They were not recomputed and nothing is claimed
about them.

## What changed and what did not

**No verdict, gate or threshold comparison changes.**

- Stage 1 and 1B statuses do not read ρ. Rerun under the corrected default, all
  35 statuses equal the committed ones and the seven replication labels are the
  same.
- The audit's own floor is ρ ≥ 0.50. The lowest corrected figure on the public
  corpus is 0.7761, and it is tie-free. `ConfoundVerdict.passed` is the same under
  both rankings in all 75 cells, StatsBomb included.
- E-02's T3 floor is 0.50 and the figure did not move. RESEARCH_ONLY stands.
- No threshold on ρ is written for the Stage 1C external verdicts, and its report
  prints no ρ. None of its forty figures is below 0.50 under either ranking.
- The top-12 count sorts the same arrays, so a tie at the twelfth place would
  make it order-dependent too. No cell has one.
- Nothing shipped holds an ordering figure. The profile bundle, the construct
  registry and the API contain none; the only callers are three experiment
  scripts. Nothing was rebuilt.

What changed:

- `ties="average"` is the default of `_spearman` and `discriminant_validity`.
  `ties="legacy"` remains, to reproduce a figure published before this note, and
  warns whenever it meets tied data.
- The three reports carry one line pointing here. No other line of them changed,
  and no result file was regenerated.
- The Stage 1B and 1C runners were not changed. Run today they compute the
  corrected figures, and they still write over the result files they wrote then.

## Found on the way

Three of the four Wyscout columns of Stage 1C do not reproduce from the corpus as
it is. They reproduce to the last bit when the `dangerous_loss` column is withheld
from Spain, England and France, and the runner falls back to failed passes alone
when that column is absent. Italy reproduces with the column present. So one
published table mixes two turnover recipes.

On the corpus as it is, the nine xT-weighted figures for those three leagues
differ from the published ones before any tie correction, by up to 0.000444. The
largest tie correction is 0.004281 on either corpus. The tables above use the
input that reproduces the publication. This is not corrected here.

The second finding is about the record itself. `experiments/external_replication.json`
carried the StatsBomb half of Stage 1C beside the Wyscout half: four blocks of
aggregate figures, machine-readable, tracked since the day the report was published.
LICENSING.md keeps tables derived from StatsBomb data out of the repository, and the
guard that enforces it reads paths and extensions, not what a JSON file holds. The
blocks were removed from the tree with this note and remain in the history. The
runner now writes that half under the gitignored cache, and a test fails if a tracked
result file holds such a block again. The StatsBomb row of the table above compares
with that local record: the script reports it where the record exists and says
that it compared nothing where it does not.

## The checks to apply from now on

1. A statistic of the data must not move when the rows do. Permute the rows in
   the test.
2. A function named after a statistic is tested against the definition written
   out independently, not only against itself.
3. Synthetic test data needs the awkward property the real data has. A count, or
   a sum over a rare event, has a mass at zero.
4. A result file that does not carry the hash of its input cannot be told apart
   from one computed on another corpus.

## Commands

```
PYTHONPATH=. .venv/Scripts/python.exe experiments/run_rank_tie_erratum.py
PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q tests/test_rank_ties.py tests/test_confound.py
```

The first prints every number in this note and writes nothing. It ran in about
95 seconds on Windows with numpy 2.5.3. "Bit for bit" is a statement about that
machine: ranks handed out by an unstable sort are not promised on another one.

`tests/test_rank_ties.py` holds the two tables above. The check job compares them
with this note and with the committed result files; the corpus job recomputes the
corrected column. The StatsBomb paragraph is recomputed only where the local
cache is, which is no CI job.
