#!/usr/bin/env python3
import os
import sys
import cv2
import pytesseract
import re
import json
import logging
from symspellpy import SymSpell, Verbosity

# ── Configuration ────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(__file__)
FREQ_DICT      = os.path.join(BASE_DIR, 'dictionary', 'pharmacy_dict.txt')
MED_DICT       = os.path.join(BASE_DIR, 'dictionary', 'medicine_names.txt')

# 1. Simple confusions map for common OCR misreads
_CONFUSIONS = {
    '0': ['O'], '1': ['l','I'], '5': ['S'], '8': ['B'],
}

# ── Core functions ───────────────────────────────────────────────────────────
def _init_symspell(freq_dict_path=FREQ_DICT):
    sym = SymSpell(max_dictionary_edit_distance=1, prefix_length=7)
    sym.load_dictionary(freq_dict_path, term_index=0, count_index=1)
    return sym

def _load_med_dict(med_dict_path=MED_DICT):
    with open(med_dict_path, encoding='utf8') as f:
        return {line.strip().lower() for line in f if line.strip()}

def _preprocess(path):
    img  = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    blur = cv2.medianBlur(img, 3)
    _, bw = cv2.threshold(blur, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bw

def _ocr(image):
    return pytesseract.image_to_string(image, config='--oem 1 --psm 6')

def _correct(text, sym):
    tokens = re.findall(r"\w+|\W+", text)
    out    = []
    for t in tokens:
        # skip units
        if re.fullmatch(r"\d*\s*(?:mg|g|ml)", t, re.IGNORECASE):
            out.append(t)
        elif t.isalpha():
            s = sym.lookup(t, Verbosity.CLOSEST, max_edit_distance=1)
            out.append(s[0].term if s else t)
        else:
            out.append(t)
    return ''.join(out)

def _extract(text, med_dict):
    name = re.search(r'Patient[:\s]*([A-Za-z ,\'-]+)', text, re.IGNORECASE)
    dob  = re.search(r'DOB[:\s]*([\d/-]+)',          text, re.IGNORECASE)
    med  = next((m for m in med_dict if m in text.lower()), None)
    dose = re.search(r'(\d+ ?(?:mg|g|ml))',           text, re.IGNORECASE)

    # catch “every $ hours for ? days”
    m = re.search(
        r'every\s*([\d\$\?]+)\s*hours'
        r'(?:\s*for\s*([\d\$\?]+)\s*days)?',
        text, re.IGNORECASE
    )
    if m:
        freq = f"every {m.group(1)} hours"
        if m.group(2): freq += f" for {m.group(2)} days"
    else:
        m2 = re.search(
            r'(once daily|twice daily|\d+x per day|\bq[hd]\b)',
            text, re.IGNORECASE
        )
        freq = m2.group(1) if m2 else None

    return {
        'name':       name.group(1).strip() if name else None,
        'dob':        dob.group(1).strip()  if dob  else None,
        'medication': med,
        'dosage':     dose.group(1).strip() if dose else None,
        'frequency':  freq
    }

def process_image(image_path):
    """ Electron & CLI both call this. """
    img  = _preprocess(image_path)
    raw  = _ocr(img)
    sym  = _init_symspell()
    corr = _correct(raw, sym)
    meds = _load_med_dict()
    return _extract(corr, meds)

# ── Command‐line entrypoint (JSON only) ─────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: extract_rx.py <imagePath>', file=sys.stderr)
        sys.exit(1)

    image = sys.argv[1]
    result = process_image(image)
    sys.stdout.write(json.dumps(result))  # **just** JSON, no logs or debug
