"""Schema constants and parquet load/save helpers.

Schemas are locked in docs/DESIGN.md §5. Do not change without updating the design doc.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
FIGURES = REPO_ROOT / "figures"

WHALE_CODAS_SCHEMA = {
    "coda_id": "str",
    "recording_id": "str",
    "n_clicks": "int64",
    "ici_seq": "object",
    "total_duration": "float64",
    "source_dataset": "str",
}

WHALE_ACOUSTIC_EVENTS_SCHEMA = {
    "event_id": "str",
    "timestamp_utc": "datetime64[ns, UTC]",
    "hydrophone_id": "str",
    "lat": "float64",
    "lon": "float64",
}

VEDIC_SYLLABLES_SCHEMA = {
    "verse_id": "str",
    "syllable_idx": "int64",
    "syllable_str": "str",
    "weight": "str",
    "duration_matra": "int64",
    "meter_label": "str",
}
