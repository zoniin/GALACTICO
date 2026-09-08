# M-05: minimizing shortfall still selects estimation noise

Run `python experiments/run_optimizer_curse.py`. Seed 20260906, 4,000 synthetic
trials; eight candidates, choose three, two known latent requirement rates.
Enumerate all 56 sets. Minimize maximum normalized shortfall, then total shortfall.
Latent rates have mean 1.8, SD .3; each requirement minimum is 6.2. These are
simulation settings, not football calibration.

| Observation noise SD | Reported max deficit | True selected max deficit | Optimism | Oracle-shrinkage optimism |
|---:|---:|---:|---:|---:|
| .1 | .0596 | .0727 | .0131 | .0072 |
| .3 | .0463 | .1067 | .0605 | .0235 |
| .6 | .0310 | .1388 | .1078 | .0341 |

As measurement noise increases, the model appears to cover requirements better
while the selected set's true shortfall gets worse. Avoiding an opaque football
score does not avoid the optimizer's curse.

Gaussian shrinkage using the *known* population mean and variance reduces this
simulation's optimism, but does not eliminate nonlinear selection bias. Its
assumptions are not estimated for historical Madrid, so no correction coefficient
is transferred into XI Lab. The product reports model-implied quantities,
conditional shared-world stability, and equally optimal membership bounds. It
does not call those quantities calibrated forecasts or optimism-corrected utility.

Next experiment: estimate shrinkage out of sample with temporal training, then
evaluate selection and reporting separately. Robust/CVaR/minimax-regret modes
need an explicit risk preference and meaningful identified loss. Expected regret
alone is not a distinct optimizer: its world-optimal term is constant across choices.
