"""Construct notebooks 03 and 04 as ipynb JSON, then nbconvert --execute them.

Kept under scripts/ rather than as a notebook so the source of truth is reviewable
diffable Python rather than a giant JSON blob with embedded outputs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NB_DIR = REPO / "notebooks"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def write_notebook(path: Path, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb, indent=1))


# ---------------------------------------------------------------------------
# Notebook 03 — full structural comparison with surrogate baselines.
# ---------------------------------------------------------------------------

NB03_CELLS: list[dict] = []

NB03_CELLS.append(md("""# 03 — Structural comparison: sperm whale codas vs Rigveda

Compares timing/sequence statistics from the two corpora against three null
models per side. The goal is **not** to argue that whale codas mean anything
Vedic; it is to ask whether the structural features of one corpus look more
like those of the other than either looks like its own surrogate.

Sections:

1. Load corpora.
2. Build whale sequences and Vedic sequences (one per stanza pāda).
3. Generate three surrogate variants per corpus.
4. Pooled inter-onset-interval (IOI) distributions: KS test + Cohen's d.
5. n-gram entropy table (n=2, n=3) across real and surrogate variants.
6. Mean lag-k autocorrelation comparison.
7. Honest verdict.
"""))

NB03_CELLS.append(code("""\
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats as sps

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from swp import features, stats as swstats
from swp.io import DATA_PROCESSED, FIGURES

FIGURES.mkdir(exist_ok=True)
RNG = np.random.default_rng(20260501)
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 140
"""))

NB03_CELLS.append(md("## 1. Load corpora"))

NB03_CELLS.append(code("""\
codas = pd.read_parquet(DATA_PROCESSED / "whale_codas.parquet")
vedic = pd.read_parquet(DATA_PROCESSED / "vedic_syllables.parquet")

print(f"Whale codas: {len(codas):,} rows; sources={dict(codas['source_dataset'].value_counts())}")
print(f"  n_clicks  median={int(codas['n_clicks'].median())} "
      f"min={int(codas['n_clicks'].min())} max={int(codas['n_clicks'].max())}")
print(f"  total_duration mean={codas['total_duration'].mean():.3f}s "
      f"median={codas['total_duration'].median():.3f}s")
print()
print(f"Vedic syllables: {len(vedic):,} rows across {vedic['verse_id'].nunique():,} pādas")
print(f"  weight: {dict(vedic['weight'].value_counts())}")
print(f"  meter labels: {vedic['meter_label'].nunique()} bins")
"""))

NB03_CELLS.append(md("""## 2. Build sequences

* Whale: one ICI sequence per coda. Codas with fewer than two clicks have no
  IOIs and are excluded from IOI-based statistics.
* Vedic: one weight sequence per pāda (e.g. `RV.1.1.1.a`). Pādas labelled
  `unknown` meter are kept (they're just unbinned by canonical meter).
"""))

NB03_CELLS.append(code("""\
whale_ici = [list(s) for s in codas["ici_seq"].tolist() if len(s) > 0]
print(f"whale: {len(whale_ici):,} sequences with >=1 IOI")

vedic_weights = (
    vedic.sort_values(["verse_id", "syllable_idx"])
         .groupby("verse_id", sort=False)["weight"]
         .apply(list)
         .tolist()
)
vedic_weights = [s for s in vedic_weights if len(s) >= 2]
print(f"vedic: {len(vedic_weights):,} pāda sequences with >=2 syllables")

vedic_durations = [features.weights_to_durations(s).tolist() for s in vedic_weights]
"""))

NB03_CELLS.append(md("""## 3. Generate surrogates

Three null models per corpus:

* **shuffle-within**: permute the order of units within each sequence. Preserves
  per-sequence multiset and length; destroys position-specific structure.
* **shuffle-across**: pool all units across sequences and redistribute into the
  original lengths. Preserves global unit frequencies and length distribution;
  destroys per-sequence identity.
* **poisson**: replace each sequence with exponentially-spaced IOIs (whale) or
  with i.i.d. weight tokens drawn from the global L/G frequency (Vedic).
  Destroys all structure beyond the first moment.
"""))

NB03_CELLS.append(code("""\
whale_within = swstats.surrogate_shuffle_within(whale_ici, RNG)
whale_across = swstats.surrogate_shuffle_across(whale_ici, RNG)
whale_poisson = swstats.surrogate_poisson(whale_ici, RNG)

vedic_within = swstats.surrogate_shuffle_within(vedic_weights, RNG)
vedic_across = swstats.surrogate_shuffle_across(vedic_weights, RNG)

# Poisson analogue for Vedic: i.i.d. weight tokens from global frequency.
_w_pool = [w for s in vedic_weights for w in s]
_p_L = _w_pool.count("L") / len(_w_pool)
def _poisson_vedic(seqs, rng):
    out = []
    for s in seqs:
        out.append(rng.choice(["L", "G"], size=len(s), p=[_p_L, 1 - _p_L]).tolist())
    return out
vedic_iid = _poisson_vedic(vedic_weights, RNG)

vedic_dur_within = [features.weights_to_durations(s).tolist() for s in vedic_within]
vedic_dur_across = [features.weights_to_durations(s).tolist() for s in vedic_across]
vedic_dur_iid = [features.weights_to_durations(s).tolist() for s in vedic_iid]

print("surrogates built")
"""))

NB03_CELLS.append(md("""## 4. Pooled IOI distributions

Whale IOIs are click-to-click intervals in seconds. Vedic IOIs are syllable
durations in mātrās (1 or 2). To compare the two corpora head-to-head we
**z-score within each corpus** so that we are asking about distribution
*shape*, not absolute units.
"""))

NB03_CELLS.append(code("""\
def zscore(arr):
    arr = np.asarray(arr, dtype=float)
    return (arr - arr.mean()) / arr.std(ddof=0)

pool = {
    "whale_real": features.pooled_ioi(whale_ici),
    "whale_within": features.pooled_ioi(whale_within),
    "whale_across": features.pooled_ioi(whale_across),
    "whale_poisson": features.pooled_ioi(whale_poisson),
    "vedic_real": features.pooled_ioi(vedic_durations),
    "vedic_within": features.pooled_ioi(vedic_dur_within),
    "vedic_across": features.pooled_ioi(vedic_dur_across),
    "vedic_iid": features.pooled_ioi(vedic_dur_iid),
}

pool_z = {k: zscore(v) for k, v in pool.items()}

rows = []
def _row(name, a_key, b_key):
    a, b = pool[a_key], pool[b_key]
    D, p = swstats.ks_test(a, b)
    d = swstats.effect_size_cohens_d(a, b)
    rows.append({"comparison": name, "n_a": len(a), "n_b": len(b),
                 "KS_D": D, "p": p, "cohens_d": d})

_row("whale real vs whale shuffle-within", "whale_real", "whale_within")
_row("whale real vs whale shuffle-across", "whale_real", "whale_across")
_row("whale real vs whale poisson",        "whale_real", "whale_poisson")
_row("vedic real vs vedic shuffle-within", "vedic_real", "vedic_within")
_row("vedic real vs vedic shuffle-across", "vedic_real", "vedic_across")
_row("vedic real vs vedic iid (poisson)",  "vedic_real", "vedic_iid")

rows.append({"comparison": "z(whale real) vs z(vedic real)",
             "n_a": len(pool_z["whale_real"]), "n_b": len(pool_z["vedic_real"]),
             "KS_D": swstats.ks_test(pool_z["whale_real"], pool_z["vedic_real"])[0],
             "p":    swstats.ks_test(pool_z["whale_real"], pool_z["vedic_real"])[1],
             "cohens_d": swstats.effect_size_cohens_d(pool_z["whale_real"], pool_z["vedic_real"])})

ks_df = pd.DataFrame(rows)
ks_df["p"] = ks_df["p"].apply(lambda x: f"{x:.2e}")
ks_df["KS_D"] = ks_df["KS_D"].round(4)
ks_df["cohens_d"] = ks_df["cohens_d"].round(3)
ks_df
"""))

NB03_CELLS.append(code("""\
# Figure: pooled IOI histograms in z-units (shape comparison).
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
bins = np.linspace(-3, 5, 60)
axes[0].hist(pool_z["whale_real"], bins=bins, alpha=0.55, label="real", color="steelblue", density=True)
axes[0].hist(pool_z["whale_poisson"], bins=bins, alpha=0.45, label="poisson", color="grey", density=True)
axes[0].hist(pool_z["whale_within"], bins=bins, alpha=0.35, label="shuffle-within", color="orange", density=True)
axes[0].set_title("Whale ICIs (z-scored)")
axes[0].set_xlabel("z(IOI)")
axes[0].legend(fontsize=8)

axes[1].hist(pool_z["vedic_real"], bins=bins, alpha=0.55, label="real", color="seagreen", density=True)
axes[1].hist(pool_z["vedic_iid"], bins=bins, alpha=0.45, label="iid L/G", color="grey", density=True)
axes[1].hist(pool_z["vedic_within"], bins=bins, alpha=0.35, label="shuffle-within", color="orange", density=True)
axes[1].set_title("Vedic syllable durations (z-scored)")
axes[1].set_xlabel("z(duration in mātrās)")
axes[1].legend(fontsize=8)

fig.suptitle("Pooled IOI distribution shape — real vs surrogates")
fig.tight_layout()
fig.savefig(FIGURES / "03_pooled_ioi_histograms.png", bbox_inches="tight")
plt.show()
"""))

NB03_CELLS.append(md("""## 5. n-gram entropy

Whale ICIs are first quantized into 5 bins **per coda** (so the discretisation
is local, not corpus-wide), then 2-grams and 3-grams are tallied. Vedic uses
the natural L/G alphabet directly.

Lower entropy → more structured. We compare each corpus's real n-gram entropy
to its surrogates: a real value below all three surrogates indicates structure
beyond what the surrogate preserves.
"""))

NB03_CELLS.append(code("""\
def entropy_row(name, seqs, vedic_mode=False):
    if vedic_mode:
        h2 = features.vedic_ngram_entropy(seqs, n=2)
        h3 = features.vedic_ngram_entropy(seqs, n=3)
    else:
        h2 = features.whale_ngram_entropy(seqs, n=2, n_bins=5)
        h3 = features.whale_ngram_entropy(seqs, n=3, n_bins=5)
    return {"variant": name, "H_2gram": round(h2, 4), "H_3gram": round(h3, 4)}

ent_rows = [
    entropy_row("whale: real",            whale_ici),
    entropy_row("whale: shuffle-within",  whale_within),
    entropy_row("whale: shuffle-across",  whale_across),
    entropy_row("whale: poisson",         whale_poisson),
    entropy_row("vedic: real",            vedic_weights, vedic_mode=True),
    entropy_row("vedic: shuffle-within",  vedic_within,  vedic_mode=True),
    entropy_row("vedic: shuffle-across",  vedic_across,  vedic_mode=True),
    entropy_row("vedic: iid L/G",         vedic_iid,     vedic_mode=True),
]
ent_df = pd.DataFrame(ent_rows)
ent_df
"""))

NB03_CELLS.append(code("""\
# Chi-square on 2-gram counts: real vs each surrogate.
def _counts(seqs, vedic_mode):
    if vedic_mode:
        return features.ngram_counts(seqs, n=2)
    return features.ngram_counts(features.discretize_whale(seqs, n_bins=5), n=2)

whale_real_c     = _counts(whale_ici,     False)
whale_within_c   = _counts(whale_within,  False)
whale_across_c   = _counts(whale_across,  False)
whale_poisson_c  = _counts(whale_poisson, False)
vedic_real_c     = _counts(vedic_weights, True)
vedic_within_c   = _counts(vedic_within,  True)
vedic_across_c   = _counts(vedic_across,  True)
vedic_iid_c      = _counts(vedic_iid,     True)

chi_rows = []
for label, real, surr in [
    ("whale real vs shuffle-within",  whale_real_c, whale_within_c),
    ("whale real vs shuffle-across",  whale_real_c, whale_across_c),
    ("whale real vs poisson",         whale_real_c, whale_poisson_c),
    ("vedic real vs shuffle-within",  vedic_real_c, vedic_within_c),
    ("vedic real vs shuffle-across",  vedic_real_c, vedic_across_c),
    ("vedic real vs iid L/G",         vedic_real_c, vedic_iid_c),
]:
    chi2, p = swstats.chi2_ngram(real, surr)
    chi_rows.append({"comparison": label, "chi2": round(chi2, 2),
                     "p": "<1e-300" if p == 0 else f"{p:.2e}"})

pd.DataFrame(chi_rows)
"""))

NB03_CELLS.append(md("## 6. Lag-k autocorrelation"))

NB03_CELLS.append(code("""\
def _ac(seqs):
    return features.mean_autocorrelation(seqs, max_lag=6)

ac_table = pd.DataFrame({
    "lag": np.arange(1, 7),
    "whale_real":     _ac(whale_ici),
    "whale_within":   _ac(whale_within),
    "whale_across":   _ac(whale_across),
    "whale_poisson":  _ac(whale_poisson),
    "vedic_real":     _ac(vedic_durations),
    "vedic_within":   _ac(vedic_dur_within),
    "vedic_across":   _ac(vedic_dur_across),
    "vedic_iid":      _ac(vedic_dur_iid),
}).set_index("lag").round(3)
ac_table
"""))

NB03_CELLS.append(code("""\
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
lags = np.arange(1, 7)
axes[0].plot(lags, ac_table["whale_real"],    "o-", label="real",          color="steelblue")
axes[0].plot(lags, ac_table["whale_within"],  "s--", label="shuffle-within", color="orange")
axes[0].plot(lags, ac_table["whale_across"],  "^--", label="shuffle-across", color="firebrick")
axes[0].plot(lags, ac_table["whale_poisson"], "x--", label="poisson",        color="grey")
axes[0].axhline(0, color="black", lw=0.5)
axes[0].set_title("Whale codas — mean lag-k autocorrelation of ICI")
axes[0].set_xlabel("lag k"); axes[0].set_ylabel("autocorrelation")
axes[0].legend(fontsize=8)

axes[1].plot(lags, ac_table["vedic_real"],    "o-", label="real",          color="seagreen")
axes[1].plot(lags, ac_table["vedic_within"],  "s--", label="shuffle-within", color="orange")
axes[1].plot(lags, ac_table["vedic_across"],  "^--", label="shuffle-across", color="firebrick")
axes[1].plot(lags, ac_table["vedic_iid"],     "x--", label="iid L/G",        color="grey")
axes[1].axhline(0, color="black", lw=0.5)
axes[1].set_title("Vedic pādas — mean lag-k autocorrelation of mātrā")
axes[1].set_xlabel("lag k")
axes[1].legend(fontsize=8)

fig.tight_layout()
fig.savefig(FIGURES / "03_autocorrelation.png", bbox_inches="tight")
plt.show()
"""))

NB03_CELLS.append(md("""## 7. Honest verdict

We expect surrogates to differ from real within each corpus — that is the
sanity check. The question that matters for "structural resonance" is
whether the **z-scored real whale ↔ real Vedic** distance is *smaller* than
the within-corpus real ↔ surrogate distances.

Numbers below let the reader judge for themselves; the README headline is
written from these.
"""))

NB03_CELLS.append(code("""\
# Within-corpus surrogate KS distances are computed on RAW (non-z-scored) pools
# because shuffle-within / shuffle-across preserve the per-corpus multiset
# exactly, so the only nontrivial within-corpus surrogate for KS is poisson.
def _ks(a, b):
    return swstats.ks_test(a, b)[0]

cross_D         = _ks(pool_z["whale_real"], pool_z["vedic_real"])
whale_within_D  = _ks(pool["whale_real"],   pool["whale_within"])
whale_across_D  = _ks(pool["whale_real"],   pool["whale_across"])
whale_poisson_D = _ks(pool["whale_real"],   pool["whale_poisson"])
vedic_within_D  = _ks(pool["vedic_real"],   pool["vedic_within"])
vedic_across_D  = _ks(pool["vedic_real"],   pool["vedic_across"])
vedic_iid_D     = _ks(pool["vedic_real"],   pool["vedic_iid"])

print("KS distance:")
print(f"  whale_real ↔ vedic_real (z-scored)    : {cross_D:.3f}")
print(f"  whale_real ↔ whale_shuffle_within     : {whale_within_D:.3f}")
print(f"  whale_real ↔ whale_shuffle_across     : {whale_across_D:.3f}")
print(f"  whale_real ↔ whale_poisson            : {whale_poisson_D:.3f}")
print(f"  vedic_real ↔ vedic_shuffle_within     : {vedic_within_D:.3f}  (multiset preserved → 0)")
print(f"  vedic_real ↔ vedic_shuffle_across     : {vedic_across_D:.3f}  (multiset preserved → 0)")
print(f"  vedic_real ↔ vedic_iid                : {vedic_iid_D:.3f}")

# The honest signal is whether the cross-corpus z-scored distance is below the
# within-corpus distances on the *non-trivial* surrogates (poisson/iid), since
# the shuffle surrogates trivially preserve the IOI multiset.
nontrivial_floor = max(whale_poisson_D, vedic_iid_D)
print(f"\\nNon-trivial within-corpus surrogate KS floor: {nontrivial_floor:.3f}")
print(f"Cross-corpus distance:                         {cross_D:.3f}")
if cross_D < nontrivial_floor:
    print("\\n→ STRUCTURAL RESONANCE SIGNAL on pooled-IOI shape: cross-corpus distance "
          "is smaller than each corpus's distance to its own structure-destroying null.")
else:
    print("\\n→ NO STRUCTURAL RESONANCE on pooled-IOI shape: real whale ↔ real Vedic "
          "distributions differ by more than each corpus differs from its own poisson/iid null.")

# n-gram entropy gap (real vs strongest surrogate) — a positive gap means the
# corpus has structure beyond what shuffling preserves.
print()
print("n-gram entropy structure gap (smaller real H = more structure than null):")
print(f"  whale H(real)−H(within) = {ent_df.iloc[0]['H_2gram'] - ent_df.iloc[1]['H_2gram']:+.4f} bits")
print(f"  vedic H(real)−H(within) = {ent_df.iloc[4]['H_2gram'] - ent_df.iloc[5]['H_2gram']:+.4f} bits")
"""))

write_notebook(NB_DIR / "03_comparison.ipynb", NB03_CELLS)


# ---------------------------------------------------------------------------
# Notebook 04 — story-telling results notebook with headline plots only.
# ---------------------------------------------------------------------------

NB04_CELLS: list[dict] = []

NB04_CELLS.append(md("""# 04 — Headline results

A short, plot-driven version of notebook 03 for non-technical readers. Two
figures and one verdict.
"""))

NB04_CELLS.append(code("""\
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from swp import features, stats as swstats
from swp.io import DATA_PROCESSED, FIGURES

FIGURES.mkdir(exist_ok=True)
RNG = np.random.default_rng(20260501)
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 140

codas = pd.read_parquet(DATA_PROCESSED / "whale_codas.parquet")
vedic = pd.read_parquet(DATA_PROCESSED / "vedic_syllables.parquet")

whale_ici = [list(s) for s in codas["ici_seq"].tolist() if len(s) > 0]
vedic_weights = (
    vedic.sort_values(["verse_id", "syllable_idx"])
         .groupby("verse_id", sort=False)["weight"]
         .apply(list)
         .tolist()
)
vedic_weights = [s for s in vedic_weights if len(s) >= 2]
vedic_durations = [features.weights_to_durations(s).tolist() for s in vedic_weights]
print(f"loaded {len(whale_ici):,} codas and {len(vedic_weights):,} pādas")
"""))

NB04_CELLS.append(md("## Headline 1 — sequence length distributions"))

NB04_CELLS.append(code("""\
whale_lens = np.asarray([len(s) for s in whale_ici])
vedic_lens = np.asarray([len(s) for s in vedic_weights])

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
axes[0].hist(whale_lens, bins=np.arange(1, whale_lens.max() + 2) - 0.5,
             color="steelblue", edgecolor="white")
axes[0].set_title(f"Whale codas — clicks per coda (n={len(whale_lens):,})")
axes[0].set_xlabel("inter-click intervals per coda"); axes[0].set_ylabel("count")

axes[1].hist(vedic_lens, bins=np.arange(1, max(vedic_lens.max() + 2, 25)) - 0.5,
             color="seagreen", edgecolor="white")
axes[1].set_title(f"Rigveda pādas — syllables per pāda (n={len(vedic_lens):,})")
axes[1].set_xlabel("syllables per pāda")

fig.tight_layout()
fig.savefig(FIGURES / "04_sequence_lengths.png", bbox_inches="tight")
plt.show()
"""))

NB04_CELLS.append(md("""## Headline 2 — z-scored IOI distributions, side by side

Whale and Vedic units differ (seconds vs mātrās), so we standardise within
each corpus and compare the *shapes* of the resulting distributions.
"""))

NB04_CELLS.append(code("""\
def zscore(a):
    a = np.asarray(a, dtype=float)
    return (a - a.mean()) / a.std(ddof=0)

whale_pool = features.pooled_ioi(whale_ici)
vedic_pool = features.pooled_ioi(vedic_durations)

# Surrogate baselines for the verdict line.
whale_within = swstats.surrogate_shuffle_within(whale_ici, RNG)
whale_poisson = swstats.surrogate_poisson(whale_ici, RNG)
vedic_within = swstats.surrogate_shuffle_within(vedic_weights, RNG)
_p_L = sum(s.count("L") for s in vedic_weights) / sum(len(s) for s in vedic_weights)
vedic_iid = [RNG.choice(["L", "G"], size=len(s), p=[_p_L, 1 - _p_L]).tolist() for s in vedic_weights]
vedic_iid_dur = [features.weights_to_durations(s).tolist() for s in vedic_iid]

zw, zv = zscore(whale_pool), zscore(vedic_pool)
zwi = zscore(features.pooled_ioi(whale_within))
zwp = zscore(features.pooled_ioi(whale_poisson))
zvi = zscore(features.pooled_ioi(vedic_iid_dur))

fig, ax = plt.subplots(figsize=(8, 4.2))
bins = np.linspace(-3, 5, 50)
ax.hist(zw, bins=bins, density=True, alpha=0.55, label="whale ICI (real)", color="steelblue")
ax.hist(zv, bins=bins, density=True, alpha=0.55, label="vedic mātrā (real)", color="seagreen")
ax.hist(zwp, bins=bins, density=True, alpha=0.20, label="whale poisson surrogate", color="grey",
        histtype="step", linewidth=1.5)
ax.set_title("Pooled IOI distribution shape — z-scored within each corpus")
ax.set_xlabel("z(IOI)"); ax.set_ylabel("density")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(FIGURES / "04_zscored_ioi.png", bbox_inches="tight")
plt.show()

D_cross, p_cross = swstats.ks_test(zw, zv)
# Within-corpus comparisons use raw (not z-scored) pools because the shuffle
# surrogates trivially preserve the multiset; the meaningful surrogates here
# are poisson (whale) and i.i.d. L/G (vedic).
D_w_poisson, _ = swstats.ks_test(whale_pool, features.pooled_ioi(whale_poisson))
D_v_iid, _    = swstats.ks_test(vedic_pool, features.pooled_ioi(vedic_iid_dur))

floor = max(D_w_poisson, D_v_iid)
print(f"KS distance whale_real ↔ vedic_real (z-scored): D={D_cross:.3f}")
print(f"Within-corpus real ↔ structure-destroying-null KS: whale={D_w_poisson:.3f}, vedic={D_v_iid:.3f}")
print(f"Non-trivial surrogate floor: {floor:.3f}")
"""))

NB04_CELLS.append(md("## Headline 3 — n-gram entropy of real vs surrogate"))

NB04_CELLS.append(code("""\
def _whale_h(seqs):
    return features.whale_ngram_entropy(seqs, n=2, n_bins=5)
def _vedic_h(seqs):
    return features.vedic_ngram_entropy(seqs, n=2)

whale_h_real = _whale_h(whale_ici)
whale_h_within = _whale_h(whale_within)
whale_h_poisson = _whale_h(whale_poisson)
vedic_h_real = _vedic_h(vedic_weights)
vedic_h_within = _vedic_h(vedic_within)
vedic_h_iid = _vedic_h(vedic_iid)

fig, ax = plt.subplots(figsize=(7, 3.6))
labels = ["whale\\nreal", "whale\\nshuffle-within", "whale\\npoisson",
          "vedic\\nreal", "vedic\\nshuffle-within", "vedic\\niid L/G"]
vals = [whale_h_real, whale_h_within, whale_h_poisson,
        vedic_h_real, vedic_h_within, vedic_h_iid]
colors = ["steelblue", "lightsteelblue", "lightgrey",
          "seagreen", "lightgreen", "lightgrey"]
ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.5)
ax.set_ylabel("2-gram entropy (bits)")
ax.set_title("Lower bar = more structure than the null model captures")
fig.tight_layout()
fig.savefig(FIGURES / "04_ngram_entropy.png", bbox_inches="tight")
plt.show()

print(f"whale: real={whale_h_real:.3f}, within={whale_h_within:.3f}, poisson={whale_h_poisson:.3f}")
print(f"vedic: real={vedic_h_real:.3f}, within={vedic_h_within:.3f}, iid={vedic_h_iid:.3f}")
"""))

NB04_CELLS.append(md("""## Verdict

Strict reading: a structural-resonance claim requires the cross-corpus distance
to be **smaller** than the worst within-corpus real-vs-surrogate distance. The
cell below prints the verdict; copy the bolded line into the README.
"""))

NB04_CELLS.append(code("""\
if D_cross < floor:
    verdict = (f"**Weak structural similarity detected** — cross-corpus z-scored IOI distance "
               f"D={D_cross:.3f} is below the worst within-corpus real-vs-surrogate distance "
               f"D={floor:.3f}. See notebook 03 for the full breakdown.")
else:
    verdict = (f"**No structural resonance detected beyond what surrogate sequences produce.** "
               f"The z-scored pooled-IOI distance between real whale codas and real Rigvedic pādas "
               f"(KS D={D_cross:.3f}) exceeds the worst real-vs-surrogate distance within either "
               f"corpus (D={floor:.3f}). The two distributions differ in shape by more than each "
               f"corpus differs from its own structure-destroying nulls.")
print(verdict)
"""))

write_notebook(NB_DIR / "04_results.ipynb", NB04_CELLS)


# ---------------------------------------------------------------------------
# Execute both notebooks in place.
# ---------------------------------------------------------------------------

for name in ("03_comparison.ipynb", "04_results.ipynb"):
    nb_path = NB_DIR / name
    print(f"executing {nb_path} ...")
    subprocess.run(
        [
            "jupyter", "nbconvert", "--to", "notebook", "--execute",
            "--inplace", "--ExecutePreprocessor.timeout=600",
            str(nb_path),
        ],
        check=True,
    )
print("done")
