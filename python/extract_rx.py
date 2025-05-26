"""
Fast prescription extractor using Microsoft's TrOCR-small model.
Outputs *always* valid JSON. On error: { "error": "...", "trace": "..." }
"""

import sys, json, re, traceback
from pathlib import Path

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    from PIL import Image
    from pdf2image import convert_from_path
    import torch
except ImportError as e:
    # Fatal: critical libs missing
    print(json.dumps({"error": f"Missing dependency: {e}"}), flush=True)
    sys.exit(0)

# ---------- Settings ----------
DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"
DPI      = 200
MODEL_ID = "microsoft/trocr-small-handwritten"

_processor, _model = None, None
def get_model():
    global _processor, _model
    if _model is None:
        _processor = TrOCRProcessor.from_pretrained(MODEL_ID)
        _model     = VisionEncoderDecoderModel.from_pretrained(MODEL_ID).to(DEVICE)
    return _processor, _model

# ---------- SIG expansion ----------
SIG_MAP = {
    r"\bpo\b": "by mouth",
    r"\bbid\b": "twice daily",
    r"\btid\b": "three times daily",
    r"\bqid\b": "four times daily",
    r"\bq(\d+)h\b": lambda m: f"every {m.group(1)} hours",
    r"\bprn\b": "as needed",
}
def expand_sig(t):
    for pat, repl in SIG_MAP.items():
        t = re.sub(pat, repl if isinstance(repl, str) else repl, t, flags=re.I)
    return t[:1].upper() + t[1:]

# ---------- Regexes ----------
PATIENT_RE  = re.compile(r"patient[:\s]+([A-Za-z ,]+)", re.I)
DOB_RE      = re.compile(r"dob[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
DOCTOR_RE   = re.compile(r"dr[.\s]+([A-Za-z .]+)", re.I)
MED_LINE_RE = re.compile(r"^([A-Za-z0-9\- ]+)\s+(\d+\s?(?:mg|mcg|g))", re.I|re.M)
SIG_RE      = re.compile(r"(?:sig:|#)\s*([^\n]+)", re.I)

def parse_fields(text: str):
    patient = PATIENT_RE.search(text)
    dob     = DOB_RE.search(text)
    doctor  = DOCTOR_RE.search(text)
    meds    = []
    for mm in MED_LINE_RE.finditer(text):
        name, dose = mm.group(1).strip(), mm.group(2).strip()
        after = text[mm.end(): mm.end()+120]
        sm = SIG_RE.search(after)
        sig = expand_sig(sm.group(1).strip()) if sm else "—"
        meds.append({"name": name, "dose": dose, "sig": sig})
    return {
        "patient": patient.group(1).title().strip() if patient else "—",
        "dob":     dob.group(1) if dob else "—",
        "doctor":  doctor.group(1).title().strip() if doctor else "—",
        "medications": meds or [{"name":"—","dose":"—","sig":"—"}]
    }

def image_to_text(img):
    proc, model = get_model()
    pix = proc(images=img, return_tensors="pt").pixel_values.to(DEVICE)
    ids = model.generate(pix, max_length=256)
    return proc.batch_decode(ids, skip_special_tokens=True)[0].lower()

def pdf_to_image(pdf):
    return convert_from_path(str(pdf), dpi=DPI, first_page=1, last_page=1)[0]

# ---------- Main ----------
def main():
    try:
        if len(sys.argv) < 2:
            raise ValueError("No file path provided")

        p = Path(sys.argv[1])
        if not p.exists():
            raise FileNotFoundError(p)

        img = pdf_to_image(p) if p.suffix.lower()==".pdf" else Image.open(p).convert("RGB")
        text = image_to_text(img)
        data = parse_fields(text)
        print(json.dumps(data), flush=True)

    except Exception as e:
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}), flush=True)

if __name__ == "__main__":
    main()
