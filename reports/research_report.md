# Cyberattack detection research report

## Research question

Within a deterministic synthetic `BENIGN` versus `ATTACK` study, which fixed model best balances attack detection, false alarms, and reliable confidence when controlled traffic patterns change over time? This is a reproducible research question, not a claim that any model is ready to operate an intrusion-detection system.

## Evidence protocol

Each study run starts with versioned synthetic flow generation. Its sidecar records generator/scenario versions, seed, requested/emitted rows, class and period distributions, feature definitions, assumptions, controlled shift, and SHA-256 checksum bindings. The pipeline rejects missing, malformed, mismatched, unsupported, or non-synthetic provenance before cleaning.

The comparison uses the same permitted feature contract, split manifest policy, model configurations, and seed schedule for every primary model. IDs, addresses, timestamp/period, attack-family metadata, labels, row order, and post-event candidates are excluded. Preprocessing/resampling are train-only; early stopping/calibration/fixed-FPR threshold selection are validation-only; random-test and chronological-holdout rows remain evaluation-only.

## Controlled temporal shift

Five ordered generator periods use attack prevalences of 20%, 24%, 28%, 48%, and 56%. The final two periods deliberately raise attack prevalence, traffic volume, and SYN activity. This is a transparent covariate/prior intervention that lets the study compare random and later-period measurements. It is not naturally occurring drift, an unseen-attack test, or evidence about future network traffic.

Time-aware evaluation is retained because distribution change can degrade static security classifiers; it does not turn a controlled scenario into deployment evidence. See *Learn to adapt: Robust drift detection in security domain* ([Computers & Electrical Engineering, 2023](https://doi.org/10.1016/j.compeleceng.2022.108788)) for drift concerns in security-domain learning.

## Interpretation and limitations

Saved metrics, error slices, ablations, and explanation status describe only the generated scenario and frozen protocol. Feature-group ablation measures sensitivity to removing a group, not causality. SHAP outputs are model associations on selected saved samples, not causes or attack attribution.

NIST’s [AI RMF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) emphasizes documented testing, evaluation, verification, validation, uncertainty, and limits to generalization. This project follows that posture by preserving artifacts and reporting unavailable evidence plainly. No numerical conclusion is asserted here without a generated, validated artifact.

Synthetic data does not automatically establish utility, realism, or privacy. [NIST SP 800-226](https://doi.org/10.6028/NIST.SP.800-226) discusses synthetic-data privacy hazards and utility uncertainty. This generator uses no private source traffic, but it offers no anonymity, disclosure-risk, or privacy guarantee.