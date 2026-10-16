# Preregistered experiments

One directory per experiment:

    E-XX-slug/
        preregistration.md   committed BEFORE the analysis runs
        config.json          machine-readable thresholds
        PIPELINE.md          the pipeline specification, where one is frozen with the protocol
        acceptance.json      the synthetic acceptance stamp, committed before the run where a protocol requires one
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
| E-08 partial opening histories | executed; NOT_ESTABLISHED, development selection chose context only |
| E-11 provider agreement | preregistered; pipeline built and acceptance stamped on synthetic data; not run |
