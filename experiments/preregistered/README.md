# Preregistered experiments

One directory per experiment:

    E-XX-slug/
        preregistration.md   committed BEFORE the analysis runs
        config.yaml          machine-readable thresholds
        results.json         raw output
        analysis.md          interpretation, written after

The point is not academic theatre. It is to make changing the rules after seeing
results visibly difficult — E-01 changed its criteria post hoc and that is exactly
why it is labelled exploratory rather than confirmatory.

If `analysis.md` contradicts `preregistration.md`, the preregistration wins and
the contradiction is the finding.

| Experiment | Status |
|---|---|
| E-01 metronome fit | exploratory, complete — `docs/research/E-01-metronome-fit.md` |
| E-02 metronome confirmatory | executed; frozen rejection rule not met; research-only |
| E-04 conditional spatial tendency | preregistered, not run |
| E-07 lineup transport | executed; INCONCLUSIVE at the preregistered development sample gate |
