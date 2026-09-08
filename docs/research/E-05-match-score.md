# E-05: no overall match contribution scalar identified

The first Match Lab release is vector-valued. Two deliberately simple scalar
candidates were audited on the public 2017/18 corpus: positive completed-pass xT
accounting and the same quantity standardized within broad provider position.

Run `python experiments/run_match_score.py --competition Spain` and repeat with
`--competition England`. The script fits each league's own retrospective xT surface
and prints the full Pearson/Spearman baseline battery. No proprietary ratings,
commercial endpoints or external performance labels were collected.

| Audit | Spain | England |
|---|---:|---:|
| Outfield player-matches, positive minutes | 9,722 | 9,579 |
| Accounting vs positive pass xT, Pearson | 1.000 | 1.000 |
| Role standardized vs positive pass xT, Pearson | .988 | .982 |
| Accounting vs recorded event actions, Pearson | .527 | .564 |
| Accounting vs completed passes, Pearson | .475 | .519 |
| Accounting vs goals + assist tags, Pearson | .194 | .171 |
| Accounting vs minutes, Pearson | .355 | .361 |
| Accounting vs team result, Pearson | .027 | .089 |

The accounting candidate is algebraically the existing xT baseline; the empirical
identity is a plumbing check, not a discovery. Broad-role standardization mostly
renames that baseline. Neither earns the additional claim of an overall rating.
Recorded event actions are not tracking touches. Provider xG/xA and a licensed
external performance target are unavailable in this corpus; those tests are not run.

Positive xT gain is not conserved possession contribution: repeated forward/backward
movement can accumulate positive gains. Key-pass xT is already a subset of pass
accounting, so adding it again double counts. Style has no generally better direction.
Combining these with goals or defensive counts requires a declared utility function.

Role-relative reporting answers comparison with a reference group, not football
utility. A next-start model could estimate manager selection persistence, but would
require temporal validation against minutes and previous starts. Outcome prediction
would require leakage controls, opponent adjustment and observational limitations.
Neither was trained here. This result does not prove no scalar can ever be useful;
it rejects promoting these candidates to an overall contribution construct.

Match Lab therefore displays the component vector, with exact filters and units.
The score field is `NOT_IDENTIFIED`. Season-level reliability is not repurposed as
confidence in an individual match performance. See the [original xT definition](https://karun.in/blog/expected-threat.html)
and [VAEP research framework](https://dtai-static.cs.kuleuven.be/sports/vaep/) for
distinct value-accounting research paths requiring their own calibration and claims.
