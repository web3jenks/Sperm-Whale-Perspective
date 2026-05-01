# Sperm Whale Perspective — Design Document

**Status:** Approved at Understanding Lock + Section 6 review.
**Date:** 2026-05-01
**PI / Thesis author:** Dr. Zijing (`zzj0402`)
**Engineering / analysis contributor:** project owner (this user)
**AI assistance:** Claude (Anthropic), via brainstorming + multi-agent execution
**Target repo:** https://github.com/zzj0402/Sperm-Whale-Perspective (via fork → PR)
**Timeline:** Weekend (~12–16 hours focused work)

---

## 1. Understanding Summary

- **What:** A reproducible Jupyter-notebook research repo performing a *structural* (timing/rhythm/syllabic) comparison between sperm whale codas and Rigvedic meter, layered on a behavioral/spatial visualization of the AUTEC sperm whale acoustic dataset.
- **Why:** Dr. Zijing has a metaphysical thesis (cosmic consciousness, whale ↔ Hindu language connection) and wants a data-grounded artifact in `zzj0402/Sperm-Whale-Perspective` that explores it without overclaiming.
- **Who for:** Primary — Dr. Zijing and his collaborators. Secondary — curious technical readers.
- **Constraints:** Weekend timeline; no semantic decoding; structural-only claims; metaphysical framing isolated to a ghost-drafted README "Motivation" section that Dr. Zijing edits.
- **Non-goals:** No translation. No claim of cosmic knowledge in whales. No semantic mapping. No interactive dashboard. No PDF paper.

## 2. Decision Log

| # | Decision | Alternatives | Rationale |
|---|---|---|---|
| 1 | Structural resonance only | Hypothesis-form, exploratory decoding, full speculative translation | Only level scientifically defensible |
| 2 | Both AUTEC (spatial) + CETI/DSWP (codas) | AUTEC only, CETI only, +global sightings | Honors full brief; AUTEC alone insufficient for codas |
| 3 | Reproducible Jupyter notebooks + README | Quarto site, full PDF, dashboard | Cheapest, standard, upgradeable later |
| 4 | B-tier stats: descriptive + null-model surrogates | Descriptive only, full computational linguistics, replicate Sharma | Minimum bar for credibility |
| 4b | Cut human-language control corpus | …per timeline | Weekend scope |
| 5 | Ghost-draft Motivation, Dr. Zijing edits | He writes from scratch, minimal one-paragraph, separate essay file | Less work for him, his voice preserved |
| 6 | Fork → PR workflow | Direct collaborator, hand-off, separate repo | Standard, safe, reversible |
| 7 | Disclose AI assistance in README | Omit | Becoming standard; protects credibility |
| 8 | Rigveda full corpus (VedaWeb XML) | Mantra subset, all 4 Vedas, defer to Dr. Zijing | Best stats; per-syllable laghu/guru annotations |
| 9 | Weekend timeline | 1 week, 2–3 weeks, open-ended | User-specified |
| 10 | Multi-agent decomposition: parallel-by-corpus (3 agents + lead) | Sequential pipeline, parallel-by-notebook | Real parallelism without coordination overhead |

## 3. Assumptions (verification gated)

1. CETI/Sharma supplementary coda data is openly downloadable from Zenodo. **Gate 1.**
2. VedaWeb Rigveda XML is openly downloadable and parseable. **Gate 2.**
3. Dr. Zijing's repo doesn't already have an incompatible structure. **Gate 3.**
4. Dr. Zijing will be available within the weekend window to edit the ghost-drafted Motivation.
5. Project owner opens the PR under their GitHub identity.
6. "Weekend" = ~12–16 hours of focused work including writing.

## 4. Repository Structure

```
sperm-whale-perspective/
├── README.md                    # ghost-drafted by synthesis agent
├── LICENSE                      # MIT (code) + CC-BY-4.0 (prose)
├── pyproject.toml               # uv-managed deps
├── uv.lock
├── .gitignore
├── data/
│   ├── README.md                # provenance + checksums + licenses
│   ├── raw/                     # untouched downloads (gitignored if >50MB)
│   │   ├── autec_dataset_682/
│   │   ├── ceti_sharma_2024/
│   │   └── vedaweb_rigveda/
│   └── processed/               # parquet files; small; committed
│       ├── whale_codas.parquet
│       ├── whale_acoustic_events.parquet
│       └── vedic_syllables.parquet
├── notebooks/
│   ├── 01_whale_data.ipynb      # owned by whale-corpus
│   ├── 02_vedic_data.ipynb      # owned by vedic-corpus
│   ├── 03_comparison.ipynb      # owned by synthesis
│   └── 04_results.ipynb         # owned by synthesis
├── src/swp/
│   ├── __init__.py
│   ├── io.py
│   ├── features.py
│   └── stats.py
├── figures/
└── docs/
    ├── DESIGN.md
    └── MOTIVATION.md            # if Dr. Zijing wants long-form essay
```

## 5. Agent Contracts

### `whale-corpus` produces
- `data/processed/whale_codas.parquet` — columns: `coda_id (str)`, `recording_id (str)`, `n_clicks (int)`, `ici_seq (list[float], seconds)`, `total_duration (float, seconds)`, `source_dataset (str: "ceti"|"autec")`
- `data/processed/whale_acoustic_events.parquet` — columns: `event_id (str)`, `timestamp_utc (datetime)`, `hydrophone_id (str)`, `lat (float)`, `lon (float)`
- `notebooks/01_whale_data.ipynb` — narrates ingestion, summary stats, 2–3 spatial/temporal plots.

### `vedic-corpus` produces
- `data/processed/vedic_syllables.parquet` — columns: `verse_id (str)`, `syllable_idx (int)`, `syllable_str (str, IAST)`, `weight (str: "L"|"G")`, `duration_matra (int: 1|2)`, `meter_label (str)`
- `notebooks/02_vedic_data.ipynb` — narrates XML parse, per-meter syllable distributions.

### `synthesis` consumes both, produces
- `notebooks/03_comparison.ipynb` — feature extraction, null-model surrogates, statistical comparison.
- `notebooks/04_results.ipynb` — final plots + interpretation.
- `figures/*.png`
- `README.md` (full) + `docs/MOTIVATION.md` (ghost-drafted Dr. Zijing voice).

### Lead (orchestrator)
- Repo init, `pyproject.toml`, `src/swp/` skeleton, final integration, PR open.

## 6. Verification Gates

| Gate | Action | Failure mode | Fallback | **Result** |
|---|---|---|---|---|
| 1 | Confirm CETI/Sharma supplementary coda data is openly downloadable + has rhythm/tempo annotations | Request-only, audio-only, or missing annotations | AUTEC click-timing only | **✅ PASS** — https://zenodo.org/records/10817697 (DOI 10.5281/zenodo.10817697) — `sw-combinatoriality.zip` 4.9MB, CC-BY-4.0 |
| 2 | Confirm VedaWeb XML is parseable + has laghu/guru annotations | Annotations implicit/missing | Derive laghu/guru from IAST programmatically (~2h) | **✅ PASS** — https://github.com/VedaWebProject/vedaweb-data — 10 TEI files in `rigveda/TEI/rv_book_{01..10}.tei`, ODD+RNG schemas included, CC-licensed. Whether laghu/guru is encoded vs derived is to be confirmed by the vedic-corpus agent on first inspection. |
| 3 | Clone `zzj0402/Sperm-Whale-Perspective`, inspect existing structure | Repo already has incompatible layout | Integrate into existing structure | **✅ PASS** — repo contains only a 71-byte README. Full greenfield. |

## 7. Statistical Methodology (B-tier)

- Compute timing/structural features on both corpora:
  - Inter-onset interval (IOI) distributions
  - Sequence-length histograms
  - Autocorrelation of duration sequences
  - n-gram entropy (n=2, 3) over weight sequences
- Generate **surrogate** sequences (shuffled codas, shuffled syllables, Poisson-spaced) and run identical features.
- Statistical tests: Kolmogorov–Smirnov for distribution comparison; chi-square for n-gram frequency.
- Report effect sizes alongside p-values; treat results as exploratory.
- **No human-language control corpus** in v1 (timeline-cut; named in repo as a known limitation).

## 8. Tech Stack

- Python 3.12, `uv` for env management
- `pandas`, `numpy`, `scipy`, `matplotlib`, `lxml`, `pyarrow`, `jupyter`
- No ML frameworks needed
- License: MIT (code) + CC-BY-4.0 (prose/figures)

## 9. Risks (non-gating)

- **Apophenia.** Mitigated by null-model surrogates.
- **Sample-size asymmetry.** AUTEC (6 wks) vs Rigveda (10,500 verses) — fine for distributional tests, not paired tests.
- **Cultural sensitivity.** Ghost-drafted Motivation must respect Vedic tradition; synthesis agent reviews for tone.

## 10. Open Items (defaulted)

- **Project owner's role:** Engineering & analysis contributor, acknowledged in README.
- **Specific Rigvedic verses:** None highlighted; treat all 10,500 verses uniformly. Optionally feature Gayatri / Mahamrityunjaya as illustrative examples in plots.
