"""Structural feature extraction for whale codas and Vedic syllable sequences.

All functions consume a list of sequences. A sequence may be a list of inter-onset
intervals (whale codas) or a list of weight tokens / mātrā durations (Vedic).
The numeric output is intentionally agnostic to the underlying corpus so that the
same surrogate-comparison machinery applies to both sides.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

import numpy as np

WEIGHT_TO_MATRA = {"L": 1.0, "G": 2.0}


def weights_to_durations(weights: Sequence[str]) -> np.ndarray:
    return np.asarray([WEIGHT_TO_MATRA[w] for w in weights], dtype=float)


def inter_onset_intervals(seq: Sequence[float]) -> np.ndarray:
    return np.asarray(seq, dtype=float)


def seq_length_hist(sequences: Iterable[Sequence]) -> np.ndarray:
    lengths = np.asarray([len(s) for s in sequences], dtype=int)
    if lengths.size == 0:
        return np.zeros(0, dtype=int)
    out = np.bincount(lengths, minlength=lengths.max() + 1)
    return out


def pooled_ioi(sequences: Iterable[Sequence[float]]) -> np.ndarray:
    parts = [np.asarray(s, dtype=float) for s in sequences if len(s) > 0]
    if not parts:
        return np.zeros(0, dtype=float)
    return np.concatenate(parts)


def autocorrelation(seq: Sequence[float], max_lag: int = 5) -> np.ndarray:
    x = np.asarray(seq, dtype=float)
    n = x.size
    out = np.full(max_lag, np.nan)
    if n < 2:
        return out
    x = x - x.mean()
    denom = np.dot(x, x)
    if denom == 0:
        return out
    for lag in range(1, max_lag + 1):
        if lag >= n:
            break
        out[lag - 1] = np.dot(x[: n - lag], x[lag:]) / denom
    return out


def mean_autocorrelation(
    sequences: Iterable[Sequence[float]], max_lag: int = 5
) -> np.ndarray:
    rows = []
    for s in sequences:
        ac = autocorrelation(s, max_lag=max_lag)
        if not np.all(np.isnan(ac)):
            rows.append(ac)
    if not rows:
        return np.full(max_lag, np.nan)
    arr = np.vstack(rows)
    return np.nanmean(arr, axis=0)


def _quantile_bin_per_sequence(
    sequences: Iterable[Sequence[float]], n_bins: int
) -> list[list[int]]:
    out = []
    for s in sequences:
        arr = np.asarray(s, dtype=float)
        if arr.size == 0:
            out.append([])
            continue
        if arr.size < n_bins or np.unique(arr).size < 2:
            tokens = np.zeros(arr.size, dtype=int).tolist()
            out.append(tokens)
            continue
        edges = np.quantile(arr, np.linspace(0, 1, n_bins + 1)[1:-1])
        tokens = np.searchsorted(edges, arr, side="right").tolist()
        out.append(tokens)
    return out


def discretize_whale(
    sequences: Iterable[Sequence[float]], n_bins: int = 5
) -> list[list[int]]:
    """Bin per-coda ICIs into quantile bins. Tokens are bin indices 0..n_bins-1."""
    return _quantile_bin_per_sequence(sequences, n_bins)


def ngram_counts(sequences: Iterable[Sequence], n: int = 2) -> Counter:
    counts: Counter = Counter()
    for s in sequences:
        if len(s) < n:
            continue
        for i in range(len(s) - n + 1):
            counts[tuple(s[i : i + n])] += 1
    return counts


def ngram_entropy(sequences: Iterable[Sequence], n: int = 2) -> float:
    counts = ngram_counts(sequences, n=n)
    total = sum(counts.values())
    if total == 0:
        return float("nan")
    probs = np.asarray(list(counts.values()), dtype=float) / total
    return float(-np.sum(probs * np.log2(probs)))


def whale_ngram_entropy(
    sequences: Iterable[Sequence[float]], n: int = 2, n_bins: int = 5
) -> float:
    return ngram_entropy(discretize_whale(sequences, n_bins=n_bins), n=n)


def vedic_ngram_entropy(weight_sequences: Iterable[Sequence[str]], n: int = 2) -> float:
    return ngram_entropy(weight_sequences, n=n)
