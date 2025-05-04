"""
nlp_module.py
-------------
This module processes and interprets user input using Natural Language Processing (NLP).
It identifies user intent (e.g., ticket search or delay query) and extracts key information
(e.g., station names, dates, times) to support chatbot decision-making.
"""
"""
nlp_module.py
--------------
This module handles basic NLP tasks including intent detection and 
entity extraction using spaCy and custom rule-based logic.
"""

import spacy
import re

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# -----------------------------
# Intent Detection
# -----------------------------
def detect_intent(text):
    text = text.lower()
    if any(word in text for word in ["ticket", "book", "travel", "journey"]):
        return "booking"
    elif any(word in text for word in ["delay", "late", "arrival"]):
        return "delay"
    else:
        return "unknown"

# -----------------------------
# Entity Extraction
# -----------------------------
def extract_entities(text):
    doc = nlp(text)
    entities = {
        "from_station": None,
        "to_station": None,
        "date": None,
        "time": None
    }

    # Extract locations (assuming they're proper nouns)
    location_candidates = [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "ORG")]
    if len(location_candidates) >= 2:
        entities["from_station"] = location_candidates[0]
        entities["to_station"] = location_candidates[1]
    elif len(location_candidates) == 1:
        entities["from_station"] = location_candidates[0]  # fallback

    # Extract date and time
    for ent in doc.ents:
        if ent.label_ == "DATE":
            entities["date"] = ent.text
        elif ent.label_ == "TIME":
            entities["time"] = ent.text

    return entities

# -----------------------------
# Optional Preprocessing
# -----------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()
