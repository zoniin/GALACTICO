"""M-05: known latent requirement rates expose selection optimism.

Synthetic experiment, not football calibration. Exhaustive sets avoid reliance
on the solver being audited. Oracle shrinkage assumes known population variance.
"""

import json
from itertools import combinations

import numpy as np


def run(seed=20260906, trials=4000):
    rng = np.random.default_rng(seed)
    sets = np.array(list(combinations(range(8), 3)))
    latent = rng.normal(1.8, 0.3, size=(trials, 8, 2))
    minimum = 6.2

    def loss(values):
        sums = values[:, sets].sum(axis=2)
        deficit = np.maximum(0, (minimum - sums) / minimum)
        # Infinitesimal lex tie ordering represented by lexsort, not a football weight.
        return deficit.max(axis=2), deficit.sum(axis=2)

    truth, truth_total = loss(latent)
    output = []
    for noise in (0.1, 0.3, 0.6):
        measured = latent + rng.normal(0, noise, size=latent.shape)
        raw, total = loss(measured)
        chosen = np.lexsort((total, raw), axis=1)[:, 0]
        row = np.arange(trials)
        shrunk = 1.8 + (0.3**2 / (0.3**2 + noise**2)) * (measured - 1.8)
        shrink_loss, shrink_total = loss(shrunk)
        shrink_chosen = np.lexsort((shrink_total, shrink_loss), axis=1)[:, 0]
        output.append(
            {
                "noise_sd": noise,
                "raw_mean_reported_max_deficit": float(raw[row, chosen].mean()),
                "raw_mean_true_selected_max_deficit": float(truth[row, chosen].mean()),
                "raw_optimism": float((truth[row, chosen] - raw[row, chosen]).mean()),
                "oracle_shrinkage_optimism": float(
                    (truth[row, shrink_chosen] - shrink_loss[row, shrink_chosen]).mean()
                ),
                "raw_mean_regret": float((truth[row, chosen] - truth.min(axis=1)).mean()),
                "oracle_shrinkage_mean_regret": float(
                    (truth[row, shrink_chosen] - truth.min(axis=1)).mean()
                ),
            }
        )
    return {
        "seed": seed,
        "trials": trials,
        "results": output,
        "claim": "Synthetic selected-deficit optimism, not an empirical football correction",
        "shipping": "No correction coefficient is transferred to historical XI outputs",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
