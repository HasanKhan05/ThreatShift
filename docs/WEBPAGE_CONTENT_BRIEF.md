# Website Content Brief

The website has two pages selected through the left sidebar: **Research Overview** and **Model Results**. The highlighted navigation button and the “Viewing” text show which page is open. Every result displayed by the website is read from saved experiment artifacts; the website does not generate data, train models, or score traffic.

## Page 1 — ThreatShift Research Results

### Main introduction

- **What the visitor sees:** The page title, a short explanation that four machine-learning models are compared, and a sentence identifying the synthetic dataset’s relationship to CIC-IDS2017.
- **What it means in simple language:** The study asks which model can find suspicious examples while avoiding unnecessary alerts.
- **Why it is included:** It gives a non-technical visitor the purpose of the project immediately.
- **Important limitation and source clarification:** The traffic is fully generated. It is a development stand-in for the flow structure and attack scenarios studied in CIC-IDS2017; it does not use or reproduce CIC-IDS2017 records.

### Normal pattern and Suspicious pattern

- **What the visitor sees:** Two illustrated cards: a steady “Normal pattern” and an irregular “Suspicious pattern.”
- **What it means in simple language:** The cards introduce the two broad classes the models try to tell apart: benign and attack-like synthetic flows.
- **Why it is included:** It makes the classification task understandable without requiring networking or machine-learning knowledge.
- **Important limitation:** The shapes are explanatory symbols, not live traffic and not model predictions.

### Why synthetic data

- **What the visitor sees:** A short explanation of why the study uses repeatable generated data.
- **What it means in simple language:** Using the same declared seed recreates the same study data, so another person can repeat the comparison.
- **Why it is included:** It explains the project’s reproducibility goal and why generated data is useful during development.
- **Important limitation:** The data does not represent a real organization or live network.

### How the study works

- **What the visitor sees:** Four steps: Generate, Prepare, Compare, and Review.
- **What it means in simple language:** The project creates repeatable synthetic flows, checks and cleans them, compares four models fairly, then reviews detection and false alarms together.
- **Why it is included:** It gives visitors a simple map of the workflow without exposing implementation detail.
- **Important limitation:** This is a high-level summary. The website presents saved evidence and does not run these steps itself.

## Page 2 — Results & Model Comparison

### Results introduction

- **What the visitor sees:** The “Results & Model Comparison” title and a sentence explaining that the page focuses on the two main outcomes.
- **What it means in simple language:** This page narrows the comparison to finding attacks and avoiding false alerts.
- **Why it is included:** It keeps the result story focused and easy to scan.

### Plain-language result measures

- **What the visitor sees:** Three short definitions: Attack detection, False alarms, and Overall recommendation.
- **What it means in simple language:**
  - **Attack detection:** The share of attack rows the model finds. Higher is better.
  - **False alarms:** The share of benign rows incorrectly flagged. Lower is better.
  - **Overall recommendation:** The model selected by the study’s predeclared rule using complete saved evidence.
- **Why it is included:** Visitors can understand the measures before reading any percentages or recommendation.
- **How to interpret it:** Detection and false alarms must be considered together. A model that detects more attacks may also create more false alerts.

### Summary measures

- **What the visitor sees:** Two metric cards populated from validated saved comparison rows.
- **What it means in simple language:** The cards surface the clearest top-level detection and false-alarm findings available in the saved evidence.
- **Why it is included:** They provide a quick overview before the full model table.
- **How to interpret it:** Read each card’s label and explanatory caption. The two cards can refer to different models; they are summaries, not a new calculation performed by the website. If validated comparison rows are missing, the page says the measures are unavailable.

### Model comparison

- **What the visitor sees:** A table labelled “Saved model comparison,” with one row per model and the columns Model, Attack detection, False alarms, and Result. A recommended row is marked with the text and star “★ Recommended” and is also visually emphasized.
- **What it means in simple language:** The table places the models side by side using the same two outcomes.
- **Why it is included:** It lets visitors compare every model without technical diagnostic charts.
- **How to interpret the table:**
  - **Model** is the model’s readable name.
  - **Attack detection** is the saved mean detection percentage; higher is better.
  - **False alarms** is the saved mean false-alarm percentage; lower is better.
  - **Result** says either “Compared” or “★ Recommended.” The marker is based on the saved-evidence rule, not simply the best value in one column.
  - On a narrow screen, the table can be scrolled sideways to see every column.
- **Important limitation:** The percentages come from the project’s saved synthetic-development evidence. They are not measured performance on CIC-IDS2017 or on a live organization’s traffic.

### Overall recommendation

- **What the visitor sees:** A highlighted card naming the recommended model, its displayed attack-detection and false-alarm percentages, and a note that the unchanged predeclared research rule was used.
- **What it means in simple language:** This is the study’s overall choice after considering the required saved evidence rather than picking a model from one isolated score.
- **Why it is included:** It provides a clear conclusion while keeping the selection rule visible.
- **How to interpret it:** Treat it as the recommendation for this synthetic study only. If the saved evidence is incomplete or tied under the rule, the page explains why a recommendation is unavailable instead of inventing one.

## Key Terms

- **Synthetic data:** Computer-generated records created from declared rules and a repeatable seed, rather than captured from a real network.
- **Network flow:** A summary of communication between network endpoints, represented here by generated flow-style features.
- **Benign or normal traffic:** Traffic labelled as not belonging to the synthetic attack class.
- **Suspicious traffic:** Generated traffic with characteristics associated with the study’s attack class; it does not mean a real incident was observed.
- **Attack detection:** The proportion of labelled attack rows correctly found by a model.
- **False alarm:** A benign row incorrectly flagged as an attack.
- **Machine-learning model:** A trained method that learns patterns from prepared examples and produces classifications.
- **Model comparison:** Evaluating several models on the same saved study evidence using the same measures.
- **Recommended model:** The model favored by the project’s predeclared saved-evidence rule when the required evidence is complete and not tied.
- **Saved evidence:** Validated experiment outputs already stored on disk and read by the website.
- **CIC-IDS2017:** The public intrusion-detection dataset named in the project’s historical research framing. The current synthetic dataset contains no CIC-IDS2017 records.

## Dataset Provenance

The current study data is fully synthetic and reproducible from the repository’s declared scenario and seed. The repository’s historical research design names CIC-IDS2017; the active synthetic data is a development stand-in inspired by the flow structure and attack-scenario context studied there. It is not the original CIC-IDS2017 dataset, is not derived from its records, and is not an exact copy.

This boundary matters when reading the results: the displayed findings describe performance on the project’s generated scenario only. They cannot be treated as measured CIC-IDS2017 performance, captured-network performance, or evidence that the models are ready for a real organization.

## Current Website Story

The website explains a reproducible development study in which four models learn to separate generated normal and suspicious flow patterns. The overview introduces why the data is synthetic and how the comparison works. The results page then shows the saved attack-detection and false-alarm evidence, compares the models in one table, and presents a recommendation only when the predeclared rule supports one. The conclusion is useful for this synthetic scenario, while the data-source wording keeps it separate from results on CIC-IDS2017 or live network traffic.
