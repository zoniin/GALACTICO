# M-08: a reliability belongs to the pool it was taken over

A disclosure about the chance-creation curve of Stage 1B, and a change to what
Player Lab serves.

Player Lab served a reliability on every outfield chance-creation row, and showed
it in the tooltip of the estimator signal on each row drawn as a number. The
bundle said it was taken over the players the construct is defined for. It was
not. It was the published five-league curve, and that curve pooled goalkeepers.
The curve is now computed on the declared population.

The Stage 1B table is true of the pool it used. It is a record and is not changed.
This note says what its pool was.

## What was wrong

Chance creation is defined for outfield players. Its registry entry says so. For a
goalkeeper the profile builder dropped the row before ADR-0025 and writes a
withheld row with the reason since. Since ADR-0025 it also takes every pooled
split-half reliability over the declared population. A bundle records that rule by
name.

Four reliabilities were recomputed under the rule and written to the bundle. The
fifth was recomputed and never used. Chance creation's reliability rises with
minutes, so the builder took it from a curve instead: five constants, copied from
the table of the Stage 1B report. The figure the build script computed on the
declared population was set aside for them.

The Stage 1B pool was every player with the minutes, in five leagues. Goalkeepers
were in it: 134, 115, 101, 90 and 82 of them at the five floors. A goalkeeper
completes almost no key pass. At every floor more than nine in ten of them sit at
exactly zero in both halves. They agree with themselves and stand apart from the
outfield players. That is between-player variance the construct does not claim,
and it raised the figure.

## The two curves

Split-half reliability of chance creation by minutes floor, the five Wyscout
leagues in one pool. The recipe is Stage 1B's own: its xT fit, its estimator,
halves by match parity, a third of the floor in each half. The lower bound is the
lower end of the 90% Fisher-z interval, which is what Stage 1B graded on.

**Every player in the pool, as published**

| Minutes floor | n | r | Lower bound | Goalkeepers in the pool | Of them at zero in both halves |
|---:|---:|---:|---:|---:|---:|
| 450 | 1,903 | 0.544 | 0.517 | 134 | 126 |
| 900 | 1,551 | 0.625 | 0.599 | 115 | 107 |
| 1,350 | 1,204 | 0.683 | 0.657 | 101 | 94 |
| 1,800 | 870 | 0.725 | 0.697 | 90 | 84 |
| 2,250 | 572 | 0.756 | 0.725 | 82 | 76 |

The first four columns are the table of the Stage 1B report. The script recomputes
them and stops if one cell differs from the report as printed. They are the
published figures only with the goalkeepers in the pool.

The same five values of r are the Wyscout column of the minutes-floor table in
the Stage 1C report. That table is a record too and is not changed. Only Wyscout
figures were recomputed here.

**The declared population: outfield players**

| Minutes floor | n | r | Lower bound |
|---:|---:|---:|---:|
| 450 | 1,769 | 0.519 | 0.490 |
| 900 | 1,436 | 0.601 | 0.572 |
| 1,350 | 1,103 | 0.659 | 0.630 |
| 1,800 | 780 | 0.699 | 0.668 |
| 2,250 | 490 | 0.723 | 0.686 |

Every player in the pool has a recorded position, so the two pools differ by the
goalkeepers and by no one else. As printed, r is lower by 0.024 to 0.033 at every
floor.

## Why nothing caught it

The rule was checked where a number was computed. The curve was a constant. No
computation ran under the rule, so none could disagree with it.

No committed script produced the constants. They were copied from a report, and a
test pinned the copy.

The test of the rule could not fail. It exercised the function that filters a
population. The pooling itself was in a script that no test imported, so nothing
the test did reached it.

The published table did not name its pool. It says five leagues and a minutes
floor. It does not say that goalkeepers were counted.

[M-06](M-06-a-guard-that-never-runs.md) was a guard that never ran. This is a rule
that ran on four of the five numbers it was declared for.

## What changed and what did not

What changed:

- `RELIABILITY_CURVE` in the profile builder holds the declared-population curve:
  0.519, 0.601, 0.659, 0.699, 0.723.
- `experiments/run_chance_creation_curve.py` computes both curves. It first
  reproduces the published table, to its printed digits, or stops.
- The pooling is one function in the builder. Its test uses halves in which
  pooling the goalkeepers back in changes the answer.
- The bundle rule has a new name, so the API refuses a bundle built before this
  note.
- In the shipped bundle, La Liga 2017/18, the reliability served on all 319
  outfield chance-creation rows moved. The page shows it on the 172 rows drawn as
  a number, in the tooltip of the estimator signal. The API calls an estimator's
  signal strong from 0.70 and limited from 0.50.

| Minutes | Outfield rows | Served before | Served now | Signal before | Signal now |
|---|---:|---:|---:|---|---|
| 900 to 1,349 | 77 | 0.625 | 0.601 | limited | limited |
| 1,350 to 1,799 | 70 | 0.683 | 0.659 | limited | limited |
| 1,800 to 2,249 | 53 | 0.725 | 0.699 | strong | limited |
| 2,250 and over | 119 | 0.756 | 0.723 | strong | strong |

53 rows change from strong to limited. They are the outfield players with 1,800 to
2,249 minutes, whose chance creation is still shown as a number.

What did not:

- The Stage 1B report. Its table is true of the pool it used, and no number in any
  published report changes.
- No value, percentile, interval or render state. The floor is a number of
  minutes, and no minutes changed.
- The four other reliabilities. They were already taken on the declared
  population.
- The registry. The estimator's floor and the note beside it are part of a hashed
  entry and were not edited.
- The recipe of the curve. It is Stage 1B's, as the published one was. Player Lab
  computes its own values on an xT surface fitted with another turnover rule. The
  two were not unified here.
- Anything outside Player Lab. The profile builder reads the curve and nothing
  else does.

## The open question

The estimator shows chance creation as a number from 1,800 minutes. The registry
note beside that floor says the construct "clears the number grade only near 1,800
minutes". The number grade is a reliability of 0.70.

On the declared population:

- At 1,800 minutes r is 0.699, and 0.69925 to five places. It is under 0.70.
- r reaches 0.70 at the 2,250 floor only, where it is 0.723.
- Stage 1B graded on the lower bound. The lower bound is 0.668 at 1,800 minutes and
  0.686 at 2,250. Neither reaches 0.70. On the published pool they were 0.697 and
  0.725.

So 53 point estimates are printed beside an estimator signal the page now calls
limited, and the floor rests on a figure from a pool with goalkeepers in it.
Whether the floor moves, and to where, is the owner's decision. It was not taken
here: the floor is part of a registry entry, and editing the entry changes its
hash.

## The checks to apply from now on

1. A reliability is printed only on rows of the pool it was taken over. Beside
   every reliability table, say who was in the pool and how many.
2. A rule that a bundle declares covers every number of its kind, the constants
   included. List the numbers before saying the rule holds.
3. A constant copied from a report has a committed script that produces it and a
   test that ties the two. The script reproduces the published figure first, to
   its printed digits, or stops.
4. When a population is narrowed, recompute everything that was pooled over the
   wider one, and then everything that rests on those figures: floors, thresholds
   and the sentences that explain them.
5. A test of a rule exercises the step that carries the rule out. Take the step
   out and watch the test fail.

## Commands

```
PYTHONPATH=. .venv/Scripts/python.exe experiments/run_chance_creation_curve.py
PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q tests/test_chance_creation_curve.py tests/test_registry_contract.py
```

The first prints both curves and writes nothing. It ran in under half a minute on
Windows, on the five public leagues.

`tests/test_chance_creation_curve.py` holds the tables above. Its tests without
data compare them with this note, with the Stage 1B report and with the constants
in the builder. Its slow tests recompute both curves and read the rebuilt bundle.
They need the corpus, which in CI only the `historical-browser` job has.
