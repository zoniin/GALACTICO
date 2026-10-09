# M-06: a guard that never runs is not a guard

The README said: "There is no overall rating, and a test fails the build if one
appears." The test existed. On a laptop with the corpus it ran and passed. In CI
it had never run once.

## What was wrong

`tests/test_player_lab.py` began with a module-level skip on the profile bundle.
The `check` job has no data, so all fifteen tests in the file were skipped there,
including five that need no data at all. The `historical-browser` job downloads
the corpus and builds the bundle, and ran no pytest. So the project's central
assertion was skipped in the job without data and absent from the job with it.
Nothing was red, because a skip is not a failure.

The guard itself was weaker than its sentence. It read the top-level keys of the
first fifty profiles. A rating on profile 51, or one level down inside a construct,
passed.

The same pass over the repository found the pattern six more times:

| Guard | How it failed open |
|---|---|
| Licence guard | Outside a git work tree it printed "nothing to check" and exited 0. It skipped renames and read the working file, not the staged blob |
| Docs consistency | Deleting a generated block made the test return early, which is a pass |
| Research firewall | It searched for two module names as substrings; four planted imports passed and a comment failed |
| Reliability gate | Three units at r = 0.95 graded as a publishable number: with no interval, the lower bound fell back to the point estimate |
| Confound audit | A verdict made entirely of NaN passed, because NaN compares false against every threshold. A constant metric passed the whole audit |
| Preregistration order | Convention and `git log`; no test |

And once more in the code written to repair them. The first version of the page
copy guard removed allowed denials as raw substrings, so "Mariano rating 91"
scanned clean: "no rating" sits inside the name.

And a third time, in the documents written about the repair. They said the copy
guard scans every served label. It ran in the tests, on the replies those tests
asked for, and nowhere else: the placement gap this note is about. An auditor who
had not written it found it by searching for the call. It could not simply be moved
to the boundary, because it took 2.3 seconds on the largest real reply; it runs
there now, at 85 milliseconds, with a test that its answers did not change.

## Why nothing caught it

Each guard had a test, or was a test. Each was run by hand at the moment it was
written, on the machine that had the data, and it passed. After that the question
"does this run where the failure would happen?" was never asked again, and a green
build answered a different question.

M-03 said a 200 response is not a working application. This is the same shape one
level up: a passing suite is not evidence that a guard executed.

## What changed

- The corpus job runs the suite. The data-free thesis tests moved to a module with
  no skip.
- `galactico/domain/thesis.py` walks any payload by exact key, with path-scoped
  exemptions (`teams[].score` is a scoreline), and the bundle test covers every
  profile and every nested key. New responses pass it at the boundary
  (`runtime.finalize`), not only in a test, and since the audit so does the copy guard.
- Fail-open defaults became fail-closed: undefined is not a pass, no interval is
  no lower bound, outside a work tree is an error.
- Preregistration order and protocol hashes are machine-checked from git.
- Each repair began with a test that failed because of the defect.

## The checks to apply from now on

1. For every guard, name the job that executes it and confirm it is not skipped
   there. A skip reason that is always true in CI is a deleted test.
2. A guard must fail when its input is missing, undefined or unreadable. Write
   that test first.
3. A guard that samples (`[:50]`) or matches by substring is weaker than its
   sentence. Either tighten the guard or weaken the sentence.
4. When a guard is described in prose ("a test fails the build if..."), the prose
   is a claim. Give it a test of its own, or do not make it.
5. A reviewer who did not write the guard should try to walk past it. Of the
   defects above, the author of the code found none.

Same shape as the five notes before it: **verification placement matters as much
as verification existence.**
