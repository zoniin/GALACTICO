# Stage 3 — questions only

**No implementation. No answers. This document exists so Stage 3 begins with a
council rather than with a solver.**

The central problem:

> How do validated player measurements become lineup decisions?

Nothing in Stages 1–2 answers this. Establishing that progression is measurable
does **not** establish that progression is worth 0.23 objective points in a 4-3-3.
Measurement validity and decision utility are different scientific problems, and
the second one has not been started.

## The warning that should lead the council

Galáctico has spent a long time earning the right to say *we can measure
progression*. The temptation now is to multiply that by a weight and call the
product a decision. Every arbitrary constant introduced at this stage would
inherit the credibility of the measurement work without having earned any of it.

If Stage 3 produces an objective function whose coefficients cannot be defended
the way the constructs were, the project has quietly become the thing it was built
to avoid.

## What a role slot is

- Is a role slot a position, a set of responsibilities, or a location prior?
- Does a 4-3-3 have eleven distinguishable slots, or fewer with symmetry?
- Are slots defined by the formation, the manager, or the data?
- What makes two slots the same slot across formations?
- Can a slot be defined without assuming the answer to player-slot value?

## What player-slot value means

- Is it predicted performance in that slot, or fit to that slot's requirements?
- Stage 1C measured the player × role interaction at **at most 9% of variance**,
  and ~0 for anything shooting-related. What does that ceiling do to any model of
  slot-specific value?
- Persistence beat a role-mean baseline on all ten metrics tested. Does that mean
  slot value is mostly player value?
- If so, what work is the slot actually doing in the optimisation?

## How role suitability could be estimated

- Reference groups (re-percentiling against players who occupied the slot) are
  computable. Are they *useful*?
- Is there any identified counterfactual here, or only description?
- What would falsify a suitability estimate?

## What defines a functioning XI

- Which requirements are observable in event data, and which are heuristics?
- Rest defence, aerial presence, width, progression outlets — which of these can
  be measured with the four surviving constructs, and which cannot?
- **Be explicit that a heuristic is a heuristic.** A soft constraint the data
  cannot support is a hand-tuned prior wearing an optimiser's clothes.

## How competing dimensions get scaled

- Progression is in xT per 90; width is a share. What makes them commensurable?
- Percentile scaling assumes the population is the right frame. Is it?
- Is there any principled scaling, or only an epsilon-relaxed lexicographic order
  that avoids the question by refusing to trade dimensions at all?
- Prior research favoured lexicographic precisely because it needs no weights.
  Does that survive contact with a real tactical requirement?

## How uncertainty enters the solve

- Player estimates now carry match-level bootstrap distributions. Does the
  optimiser consume the distribution or the point?
- Prior research found the single optimal XI is **not statistically identified** —
  a 200-replicate bootstrap left 3–5 of 11 players above 90% selection frequency.
  Is stable-core-plus-contested-slots the output, or is there something better?
- The optimiser's curse inflates the reported objective by 3.5% at four-point
  noise. How is that reported rather than hidden?

## Whether solutions are effectively equivalent

- If twenty XIs sit within one standard error, what is the product actually
  claiming?
- Is selection frequency the honest output, or does it also overstate?
- What does a user do with "these six are locked and these five are contested"?

## The question underneath all of them

> What would falsify the claim that this XI is better than that one?

Prior research established that you never observe the counterfactual XI, so no
backtest can show the engine's team would have beaten the manager's. Stage 3 must
decide what it is claiming *instead*, before it builds anything.

## Process

This deserves its own research council, adversarially reviewed, before a line of
solver code is written. The measurement work earned its credibility by refusing to
ship constructs it could not defend. The optimisation work has to earn its own.

