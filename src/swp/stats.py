"""Surrogate sequence generators and statistical tests for the structural comparison.

Each surrogate is a null model that destroys a specific kind of structure while
preserving others; the contrast between real and surrogate quantifies how much
of the observed feature value is attributable to that structure.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
from scipy import stats as sps


def surrogate_shuffle_within(
    sequences: Iterable[Sequence], rng: np.random.Generator
) -> list[list]:
    """Shuffle the order of units within each sequence. Preserves multiset and length."""
    out = []
    for s in sequences:
        arr = list(s)
        if len(arr) > 1:
            idx = rng.permutation(len(arr))
            arr = [arr[i] for i in idx]
        out.append(arr)
    return out


def surrogate_shuffle_across(
    sequences: Iterable[Sequence], rng: np.random.Generator
) -> list[list]:
    """Pool all units across sequences, then redistribute into the original lengths."""
    seqs = [list(s) for s in sequences]
    pool = [u for s in seqs for u in s]
    if not pool:
        return seqs
    perm = rng.permutation(len(pool))
    pool = [pool[i] for i in perm]
    out = []
    cursor = 0
    for s in seqs:
        n = len(s)
        out.append(pool[cursor : cursor + n])
        cursor += n
    return out


def surrogate_poisson(
    sequences: Iterable[Sequence[float]], rng: np.random.Generator
) -> list[list[float]]:
    """For each sequence, replace IOIs with exponential samples matching its mean.

    Sequences shorter than two events have no inter-onset intervals to perturb,
    so they are returned untouched.
    """
    out = []
    for s in sequences:
        arr = np.asarray(s, dtype=float)
        if arr.size == 0:
            out.append([])
            continue
        mean = float(arr.mean())
        if mean <= 0 or not np.isfinite(mean):
            out.append(arr.tolist())
            continue
        out.append(rng.exponential(scale=mean, size=arr.size).tolist())
    return out


def ks_test(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    res = sps.ks_2samp(np.asarray(a, dtype=float), np.asarray(b, dtype=float))
    return float(res.statistic), float(res.pvalue)


def chi2_ngram(
    real_counts: dict, surrogate_counts: dict
) -> tuple[float, float]:
    """Chi-square goodness-of-fit comparing observed n-gram counts to surrogate-implied
    expectations. Both inputs map n-gram tuple → count. Keys are unioned; expectations
    are scaled to the observed total. n-grams with expected count < 5 are dropped."""
    keys = sorted(set(real_counts) | set(surrogate_counts), key=lambda k: str(k))
    obs = np.asarray([real_counts.get(k, 0) for k in keys], dtype=float)
    exp = np.asarray([surrogate_counts.get(k, 0) for k in keys], dtype=float)
    obs_total = obs.sum()
    exp_total = exp.sum()
    if obs_total == 0 or exp_total == 0:
        return float("nan"), float("nan")
    exp = exp * (obs_total / exp_total)
    mask = exp >= 5.0
    obs, exp = obs[mask], exp[mask]
    if obs.size < 2:
        return float("nan"), float("nan")
    exp = exp * (obs.sum() / exp.sum())
    res = sps.chisquare(f_obs=obs, f_exp=exp)
    return float(res.statistic), float(res.pvalue)


def effect_size_cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 2 or b.size < 2:
        return float("nan")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    pooled = np.sqrt(((a.size - 1) * va + (b.size - 1) * vb) / (a.size + b.size - 2))
    if pooled == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled)
