# UI Simplification Design

## Scope

Refine only the existing artifact-reading Streamlit interface. Data generation, cleaning, splitting, model fitting, calibration, threshold selection, recommendation ranking, experiment outputs, and saved artifacts remain unchanged. The working tree remains uncommitted and unpushed.

## Navigation

Keep exactly two pages. Replace the sidebar radio control with two full-width buttons: `⌂ Research Overview` and `▦ Model Results`. The selected button uses Streamlit's primary state plus an adjacent `aria-current="page"` label. Hover, focus-visible, narrow-screen, and reduced-motion styles make the state clear without relying only on color.

## Research overview

Use one custom hero containing the project title, a short beginner subtitle, and an integrated source clarification: the fully generated traffic is a development stand-in for the flow structure and attack scenarios studied in CIC-IDS2017 and does not use or reproduce CIC-IDS2017 records. Retain the normal/suspicious explanatory cards, a concise synthetic-data explanation, and a four-step high-level workflow. Remove provenance, cleaning/leakage, excluded-column, and saved-schema sections. Artifact validation remains active behind the interface.

## Results

Show only three concepts: attack detection, false alarms, and the saved recommendation. Remove charts, detailed-run expanders, shift/calibration content, seed variation, errors/ablations, SHAP status, and saved demo replay. The recommendation algorithm is not changed; its displayed explanation is shortened to the recommended model plus its saved attack-detection and false-alarm means.

## Tables

Retain one semantic `st.table` view for the model comparison; explain the three beginner concepts in accessible cards above it. Model rows contain only Model, Attack detection, False alarms, and Result. The recommended row receives a text marker (`★ Recommended`) and stronger styling, so meaning does not depend on color. CSS supplies card borders, distinct headers, zebra separation, numeric alignment, horizontal scrolling, and a visible small-screen scroll hint.

## Visual system and motion

Use the existing navy/teal/amber palette with quieter surfaces, stronger typography, more whitespace, and consistent radii. Apply a gentle staggered reveal to hero/cards/primary sections. `prefers-reduced-motion` reduces all motion to effectively zero.

## Research honesty and failure behavior

Remove the repeated long warning and all visible `Research demo` labels, badges, sidebar notes, and footer wording. Keep the factual synthetic-data boundary integrated into the overview copy without a prominent warning treatment. Preserve the existing fail-closed artifact loader and beginner recovery state.

## Verification

Use Streamlit AppTest to prove the new navigation and page content, the requested removals, accurate integrated source clarification, real artifact-derived comparison values, recommendation marker, responsive table contract, focus visibility, and reduced motion. Run focused and full pytest, Ruff format/check, mypy, lock and diff checks, then start Streamlit against a real saved artifact and verify local health. Independent UI QA must review without editing.
