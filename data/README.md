# Data

This directory holds raw and processed datasets for the analysis. Raw data is
gitignored — reproduce by following the download instructions below. Processed
parquet files are committed.

## Sources

### 1. AUTEC sperm whale acoustic detections (OBIS-SEAMAP dataset 682)
- **URL:** https://seamap.env.duke.edu/dataset/682
- **Citation:** DECAF — AUTEC Sperm Whales — Multiple Sensors — Complete Dataset.
  Density Estimation of Cetaceans from passive Acoustic Fixed sensors (DECAF), 2010.
- **License:** CC-BY (All)
- **Records:** 675 acoustic detection events of 44 individual sperm whales,
  Aug 15 – Sep 23 2007, Tongue of the Ocean (Bahamas), AUTEC hydrophone array.
- **Local path:** `data/raw/autec_dataset_682/`

### 2. CETI / Sharma et al. 2024 — sw-combinatoriality
- **URL:** https://zenodo.org/records/10817697
- **DOI:** 10.5281/zenodo.10817697
- **Citation:** Sharma, P., Gero, S., Payne, R. et al. *Contextual and combinatorial
  structure in sperm whale vocalisations.* Nat Commun 15, 3617 (2024).
- **License:** CC-BY-4.0
- **Contents:** Coda dataset and codebase from the paper — coda annotations,
  rhythm/tempo features.
- **Local path:** `data/raw/ceti_sharma_2024/`

### 3. VedaWeb — Rigveda TEI XML
- **URL:** https://github.com/VedaWebProject/vedaweb-data
- **Citation:** VedaWeb. A Web-Based Platform for the Analysis of Vedic Sanskrit Texts.
  CCeH, University of Cologne.
- **License:** CC (per-file in TEI header)
- **Contents:** 10 books of the Rigveda in TEI XML, ~220 MB total.
- **Local path:** `data/raw/vedaweb_rigveda/`

## Processed outputs (committed)

- `processed/whale_codas.parquet` — one row per coda. Schema in `src/swp/io.py`.
- `processed/whale_acoustic_events.parquet` — one row per click detection. Schema in `src/swp/io.py`.
- `processed/vedic_syllables.parquet` — one row per Vedic syllable. Schema in `src/swp/io.py`.
