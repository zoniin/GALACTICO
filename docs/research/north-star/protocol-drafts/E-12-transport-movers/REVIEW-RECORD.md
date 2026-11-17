# E-12 first revision · checkpoint review

The 19 October checkpoint (`5f76156`) contains the revised preregistration, config
and pipeline. This record compares those files with the binding [ROOT 2.8
rulings](../../ROOT-DECISIONS.md) and the registered E-11 dependency. It covers the
text available in Git. The original reviewers' individual reports are unavailable here.

| Ruling | Finding |
|---|---|
| Y1 and Y2, role continuity | The cross-provider comparison uses players whose two broad position labels agree. The origin reference population still includes unlinked players. Players whose labels differ can enter a separate descriptive calculation after the gates pass. |
| Y3, report the share beside every contrast | At the checkpoint, the protocol promised the share for every contrast, but the config put it behind both decision gates. The revised config and pipeline derive each arm's share from the linked cohort at the construct's minute floors. These counts are available even for a construct refused admission or a comparison below its sample threshold. An empty arm gives a null share. |
| Y3, sample size | The planning example of 313 stayers requires 72 movers under the configured inverse-sample-size bound. The estimates of how many movers retain their role still need the pre-registration recount specified in the config. |
| Y4, ordering | The draft permits registration before E-11 runs. Execution requires the E-11 records it reads to have resolved. The proposed admission rule combines the registry token with the E-11 admission status. DISSENT 8 requests confirmation of that conjunction. |

The three E-11 protocol file hashes and the three implementation file hashes pinned
in the E-12 config match the checkpoint files after LF normalization. The five
construct definitions also agree with E-11 on numerator, denominator, scale and
minimum denominator.

E-12 remains a draft. The questions in [PIPELINE, DISSENT](PIPELINE.md#dissent)
still need decisions where indicated. The audit and the pre-registration structural
counts are outstanding. This review used protocol text, source files and planning
arithmetic. It produced no transfer outcome.
