import fitz


def clean_hindi_text(text: str) -> str:
    """Fix common PDF extraction errors for Hindi ligatures and matras."""
    replacements = {
        "होमवकक": "होमवर्क",
        "पााकक": "पार्क",
        "दोस्◦ों": "दोस्तों",
        "दोस्ों": "दोस्तों",
        "दोस् ों": "दोस्तों",
        "क्रप": "पि",      # e.g., माता-क्रपता -> माता-पिता
        "क्रल": "लि",      # e.g., इसक्रलए -> इसलिए
        "कक": "र्क",       # common fallback for trailing rka
        "स्◦": "स्त",      # common fallback for half-sa + ta
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

def extract_pdf_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    text = " ".join(pages).strip()
    return clean_hindi_text(text)
