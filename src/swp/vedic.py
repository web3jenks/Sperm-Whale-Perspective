"""VedaWeb Rigveda TEI parsing → syllable-level rows.

The TEI files at https://github.com/VedaWebProject/vedaweb-data encode the Rigveda
in a nested div structure: book > hymn > stanza, with each stanza containing several
parallel <lg> blocks (one per witness/translator). The Zurich lg (xml:lang
"san-Latn-x-ISO-15919", source="zurich") holds the IAST-transliterated Sanskrit text,
one <l> per pada (quarter-line), with xml:id suffixes "_a", "_b", "_c", "_d".

The TEI does NOT carry per-syllable laghu/guru annotations or canonical meter labels
(gayatri/tristubh/...). Stanza_properties feature structures only encode chronological
strata classifiers (Arnold, Oldenberg, Wuest, Witzel, Grassmann). Therefore this
module derives both syllabification and weight from the IAST text using standard
Sanskrit prosody rules, and infers meter per stanza from the resulting syllable
counts per pada.

Prosody rules applied (DESIGN.md §6 Gate 2 fallback):
  - A syllable nucleus is one vowel slot; ai and au are diphthongs (one syllable).
  - Heavy (guru) if the vowel is long (ā, ī, ū, ē/e, ō/o, ṝ, ḹ, ai, au) OR if the
    nucleus is followed by ≥2 consonants before the next vowel (samyoga).
    Anusvara (ṃ) and visarga (ḥ) count as consonants for this rule.
  - Otherwise light (laghu).
  - Light = 1 mātrā, heavy = 2 mātrā.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"tei": TEI_NS}


# Vowel base characters (after NFD strip of combining marks).
# Sanskrit vocalic r̥ and l̥ are encoded as ṛ / ḷ (with combining ring-below or dot below).
_VOWEL_BASES = set("aeiouāīūēōṛḷ")
# Long vowel base forms (when the actual vowel char's NFC form is one of these,
# or when it has a macron). Diphthongs handled separately.
_LONG_VOWEL_FORMS = set("āīūēōṝḹ")
# In Vedic IAST, plain "e" and "o" are also long (there is no short e/o).
_ALWAYS_LONG_BASES = set("eo")


def _strip_marks(text: str) -> str:
    """Return text with combining marks (accents, diacritics) stripped."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _is_vowel_char(c: str) -> bool:
    """True if the character (single grapheme) is a Sanskrit/IAST vowel."""
    bare = _strip_marks(c).lower()
    return bool(bare) and bare[0] in _VOWEL_BASES


def _is_long_vowel(c: str) -> bool:
    """True if the vowel character is long in its own right (ignoring samyoga)."""
    nfc = unicodedata.normalize("NFC", c).lower()
    if nfc in _LONG_VOWEL_FORMS:
        return True
    bare = _strip_marks(c).lower()
    if not bare:
        return False
    # plain e / o are long in Sanskrit
    return bare[0] in _ALWAYS_LONG_BASES or bare[0] in {"ā", "ī", "ū", "ē", "ō", "ṝ", "ḹ"}


_PUNCT_TO_DROP = set("().,;:!?\"|")


def _clean_pada_text(text: str) -> str:
    """Strip whitespace, leading/trailing sandhi-marker hyphens, and edition
    punctuation (parentheses around restored vowels, etc.). Internal whitespace
    is kept because it can mark syllable boundaries. Hyphens INSIDE the pada
    are kept (they sometimes mark compounds in the Zurich edition)."""
    text = text.strip()
    text = text.strip("-")
    return "".join(c for c in text if c not in _PUNCT_TO_DROP)


@dataclass
class Syllable:
    text: str  # the syllable string (IAST), including its onset + nucleus + coda fragment
    weight: str  # "L" or "G"
    duration_matra: int  # 1 or 2


def syllabify_pada(pada_text: str) -> list[Syllable]:
    """Split a pada (IAST quarter-line) into syllables and assign weight to each.

    Algorithm:
      1. Lowercase + clean.
      2. Walk left-to-right collecting characters. Identify each vowel nucleus,
         applying the diphthong rule (a + i → ai, a + u → au; only when the second
         char is unaccented — accent on the second vowel breaks the diphthong).
      3. Split the consonant cluster between two adjacent vowel nuclei: in Sanskrit
         prosody, the FIRST consonant of a cluster goes with the previous syllable
         (closes it) and the rest start the next syllable's onset. This matters
         only for syllable-string assignment; weight is determined by counting all
         consonants between this nucleus and the next vowel.
      4. Determine weight: heavy if vowel is long, OR if ≥2 consonants follow it
         before the next vowel (anusvara ṃ and visarga ḥ count as consonants).
    """
    text = _clean_pada_text(pada_text).lower()
    if not text:
        return []

    # Locate all vowel nucleus positions (with diphthong collapsing).
    nuclei: list[tuple[int, int]] = []  # list of (start_idx, end_idx_exclusive) into text
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if _is_vowel_char(c):
            # Diphthong: a + i  or  a + u, only when the first vowel's NFC base is
            # plain 'a' (with or without an accent) AND the second is i/u with no
            # accent of its own.
            base_first = _strip_marks(c).lower()
            if base_first.startswith("a") and i + 1 < n:
                nxt = text[i + 1]
                if _is_vowel_char(nxt):
                    base_second = _strip_marks(nxt).lower()
                    # Only ai / au form diphthongs in Sanskrit. Treat as one nucleus
                    # if the second vowel is plain (no accent that would mark it as
                    # its own syllable) — most editions of the Rigveda put the
                    # accent on the diphthong as a whole, so we accept any acute on
                    # either char as part of the diphthong.
                    if base_second in {"i", "u"}:
                        nuclei.append((i, i + 2))
                        i += 2
                        continue
            nuclei.append((i, i + 1))
            i += 1
        else:
            i += 1

    if not nuclei:
        return []

    syllables: list[Syllable] = []
    for k, (start, end) in enumerate(nuclei):
        nucleus_text = text[start:end]
        # Find consonants following the nucleus, up to (but not including) the next
        # vowel nucleus or end of string.
        next_start = nuclei[k + 1][0] if k + 1 < len(nuclei) else n
        coda_region = text[end:next_start]
        # Count phoneme-bearing consonants in the coda region: any character that
        # is a letter (post-strip) but not whitespace/punct. Anusvara ṃ and visarga
        # ḥ are letters and count.
        coda_consonants = [c for c in coda_region if c.strip() and unicodedata.category(c).startswith("L")]
        # Aspirated consonants in IAST are written as digraphs (kh, gh, ch, jh, ṭh,
        # ḍh, th, dh, ph, bh). For weight purposes a samyoga is "≥2 consonant
        # phonemes", so we collapse aspirate digraphs into one consonant unit.
        n_consonants = _count_consonant_phonemes(coda_consonants)

        # Determine weight.
        is_diphthong = (end - start) == 2
        long_vowel = is_diphthong or _is_long_vowel(nucleus_text)
        heavy = long_vowel or n_consonants >= 2
        weight = "G" if heavy else "L"

        # Build the syllable string: include onset (consonants between previous
        # nucleus end and this nucleus) + nucleus + the FIRST consonant of the coda
        # (which closes this syllable in classical Sanskrit syllabification).
        prev_end = nuclei[k - 1][1] if k > 0 else 0
        onset_region = text[prev_end:start]
        # Strip whitespace from onset for cleaner display
        onset = onset_region.strip()

        # First-consonant rule: include the first consonant (digraph if aspirate).
        if coda_consonants:
            first_c = coda_consonants[0]
            # check if it forms an aspirate with the next char
            if len(coda_consonants) >= 2 and coda_consonants[1] == "h" and first_c in set("kgcjṭḍtdpb"):
                first_unit = first_c + "h"
            else:
                first_unit = first_c
        else:
            first_unit = ""

        syll_text = (onset + nucleus_text + first_unit).replace(" ", "")
        syllables.append(Syllable(text=syll_text, weight=weight, duration_matra=2 if heavy else 1))

    return syllables


def _count_consonant_phonemes(chars: list[str]) -> int:
    """Count consonant phonemes, collapsing aspirate digraphs (kh, gh, ch, jh, ṭh,
    ḍh, th, dh, ph, bh) into one phoneme each."""
    aspirable = set("kgcjṭḍtdpb")
    count = 0
    i = 0
    while i < len(chars):
        c = chars[i]
        if c in aspirable and i + 1 < len(chars) and chars[i + 1] == "h":
            count += 1
            i += 2
        else:
            count += 1
            i += 1
    return count


# Standard syllable-count → meter mapping for Rigvedic meters. The classical
# scheme assigns names by total syllables of a typical 4-pada stanza (or 3-pada
# for gayatri). We classify per-stanza by total syllable count and number of
# padas. See e.g. Macdonell, Vedic Grammar for Students (Appendix II).
def infer_meter(pada_syllable_counts: list[int]) -> str:
    """Infer canonical meter name from the syllable counts of a stanza's padas."""
    n_padas = len(pada_syllable_counts)
    total = sum(pada_syllable_counts)
    if n_padas == 0:
        return "unknown"
    avg = total / n_padas
    # Classify primarily by total; allow ±1 syllable per pada for textual variation.
    # 3-pada meters
    if n_padas == 3:
        if total in range(22, 26):  # ~24, gayatri (8+8+8)
            return "gayatri"
        if total in range(31, 35):  # ~33, ushnih variants
            return "ushnih"
        if total in range(28, 32):  # ~30, viraj variants (3 × 10)
            return "viraj"
    # 4-pada meters
    if n_padas == 4:
        if total in range(30, 35):  # ~32, anustubh (4 × 8)
            return "anustubh"
        if total in range(34, 39):  # ~36, brihati (8+8+12+8)
            return "brihati"
        if total in range(38, 42):  # ~40, pankti (5 × 8) — rarely 4 × 10
            return "pankti"
        if total in range(42, 46):  # ~44, tristubh (4 × 11)
            return "tristubh"
        if total in range(46, 50):  # ~48, jagati (4 × 12)
            return "jagati"
    if n_padas == 5:
        if total in range(38, 42):
            return "pankti"
    # Fall back: name by total syllable count
    if 7 <= avg <= 9:
        return "gayatri-like" if n_padas == 3 else "anustubh-like"
    if 10 <= avg <= 11:
        return "tristubh-like"
    if 11 < avg <= 12:
        return "jagati-like"
    return "atichandas" if total > 50 else "unknown"


def _verse_id(book: int, hymn: int, stanza: int, pada: str) -> str:
    return f"RV.{book}.{hymn}.{stanza}.{pada}"


def iter_stanza_padas(tei_root: etree._Element) -> Iterator[tuple[int, int, int, list[tuple[str, str]]]]:
    """Yield (book, hymn, stanza, [(pada_letter, IAST_text), ...]) for each stanza.

    Reads xml:id values like 'b01_h001_01_zur_a' to extract the pada letter, and
    pulls book/hymn/stanza numbers from the parent div hierarchy.
    """
    for hymn_div in tei_root.iter(f"{{{TEI_NS}}}div"):
        if hymn_div.attrib.get("type") != "hymn":
            continue
        hymn_xmlid = hymn_div.attrib.get(f"{{{XML_NS}}}id", "")
        # e.g. 'b01_h001'
        try:
            book_num = int(hymn_xmlid.split("_")[0][1:])
            hymn_num = int(hymn_xmlid.split("_")[1][1:])
        except (IndexError, ValueError):
            continue
        for stanza_div in hymn_div.findall(f"./{{{TEI_NS}}}div[@type='stanza']"):
            stanza_xmlid = stanza_div.attrib.get(f"{{{XML_NS}}}id", "")
            try:
                stanza_num = int(stanza_xmlid.split("_")[2])
            except (IndexError, ValueError):
                continue
            zur = stanza_div.find(f"./{{{TEI_NS}}}lg[@source='zurich']")
            if zur is None:
                continue
            padas: list[tuple[str, str]] = []
            for l_elem in zur.findall(f"./{{{TEI_NS}}}l"):
                lid = l_elem.attrib.get(f"{{{XML_NS}}}id", "")
                # Skip the *_tokens lines (they hold morphological annotation, not text)
                if lid.endswith("_tokens"):
                    continue
                # Pada letter is the last underscore-segment of the id, e.g. '..._zur_a'
                pada_letter = lid.rsplit("_", 1)[-1] if lid else ""
                if pada_letter not in {"a", "b", "c", "d", "e", "f"}:
                    continue
                text = "".join(l_elem.itertext())
                padas.append((pada_letter, text))
            if padas:
                yield book_num, hymn_num, stanza_num, padas


def parse_book(tei_path: Path) -> list[dict]:
    """Parse one TEI book file into a list of syllable-row dicts."""
    tree = etree.parse(str(tei_path))
    root = tree.getroot()
    rows: list[dict] = []
    for book, hymn, stanza, padas in iter_stanza_padas(root):
        # First pass: syllabify each pada to compute counts → infer meter
        pada_sylls: list[tuple[str, list[Syllable]]] = []
        for letter, text in padas:
            sylls = syllabify_pada(text)
            pada_sylls.append((letter, sylls))
        meter = infer_meter([len(s) for _, s in pada_sylls])
        # Second pass: emit one row per syllable
        for letter, sylls in pada_sylls:
            vid = _verse_id(book, hymn, stanza, letter)
            for idx, syl in enumerate(sylls):
                rows.append(
                    {
                        "verse_id": vid,
                        "syllable_idx": idx,
                        "syllable_str": syl.text,
                        "weight": syl.weight,
                        "duration_matra": syl.duration_matra,
                        "meter_label": meter,
                    }
                )
    return rows
