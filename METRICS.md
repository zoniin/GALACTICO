# Metrics

Six axes are registered. The original specification had eleven. The difference is
the point of this document.

## What ships

| Key | Family | Evidence ceiling | Note |
|---|---|---|---|
| `progression` | quality | Estimated | xT added by moving the ball upfield |
| `chance_creation` | quality | Estimated | xT added by actions ending in a shot |
| `ball_retention` | quality | Estimated | xT-weighted share of actions keeping possession |
| `half_space_share` | style | Derived | Location share; renamed from "half-space threat" |
| `width` | style | Derived | Location share |
| `defensive_action_profile` | style | Derived | Where defensive actions happen, not how good they are |

Quality and style are separate families rendered in separate panels. A player who
plays wide is not thereby better than one who plays narrow, and a UI that sorts on
a style axis makes a claim the data does not support.

## What does not ship, and why

**Finishing.** Empirical-Bayes-adjusted goals-minus-xG has approximately zero
year-over-year correlation even at a hundred-shot floor. "Finishing 79" cannot
mean what a reader will take it to mean. Shot volume and shot location quality are
both stable and belong in style; finishing *skill* is not measurable at this tier.

**Pressing** and **press resistance.** Both depend on StatsBomb's proprietary
`under_pressure` flag, which exists in no other corpus. Computable inside the 360
tier and nowhere else, so they are a LAB-only module that never renders beside a
Wyscout-derived axis.

**Defensive coverage** as a quality axis. Defensive volume counts have
year-over-year `r < 0.50`, and interceptions per 90 do not correlate with external
defensive ratings for centre-backs or full-backs at all. What ships instead is a
location profile, labelled style. The state-of-the-art fix needs 25 Hz optical
tracking at roughly 130,000 frames per match.

**Carrying** as a cross-provider axis. StatsBomb logs carries for movement under
three metres; others record only separation beyond it. Carries are 12-15% of all
events, so this is a different quantity rather than a noisier one.

A test asserts that `finishing`, `pressing` and `defensive_coverage` stay out of
the registry. Their absence is a result, not an oversight.

## Naming

Axes were renamed where the old name promised more than the data delivers.
"Half-space threat" became half-space *value share*: it is a location share and
was never a measure of threat. "Defensive coverage" became defensive *action
profile*. The names are the credibility surface.

## Versioning

A definition is content-addressed over its formula, inputs and normalisation.
Change any of them and the hash changes, invalidating stored results instead of
silently serving a number that no longer means what it says. Rewording a summary
does not change the hash; changing the normalisation does.

