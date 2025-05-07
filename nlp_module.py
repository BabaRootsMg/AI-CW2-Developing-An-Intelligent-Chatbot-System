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
import re
import spacy
from dateparser.search import search_dates

class NLPProcessor:
    """
    NLP Processor for intent classification, entity extraction, and slot filling.
    Supports 'find_ticket' and 'predict_delay' intents with relevant slots.
    """
    def __init__(self, station_dict=None):
        # Load spaCy English model for tokenization/NER
        self.nlp = spacy.load("en_core_web_sm")

        # Intent keywords (simple keyword-based intent classification)
        self.intent_keywords = {
            "find_ticket": ["ticket", "price", "journey", "cheapest"],
            "predict_delay": ["delay", "late", "arrival", "predict"]
        }

        # Station name-to-code mapping (overrideable)
        # Example defaults; replace with full list or load from KB/DB
        self.stations = station_dict or {
            "norwich": "NWI",
            "london": "LST",
            "oxford": "OXF",
            "ipswich": "IPS"
        }

    def predict_intent(self, text):
        """Determine user intent based on keyword matching."""
        txt = text.lower()
        for intent, keywords in self.intent_keywords.items():
            if any(kw in txt for kw in keywords):
                return intent
        return "smalltalk"

    def extract_entities(self, text):
        """
        Extract raw entities from text:
          - Dates and times via dateparser.search.search_dates
          - Station names via simple lookup
          - Trip type (single/return)
          - Train ID
          - Delay minutes
        Returns a dict of potential slots.
        """
        ents = {}

        # 1) Find date/time mentions
        dt_matches = search_dates(text, settings={"PREFER_DATES_FROM": "future"}) or []
        datetimes = [dt for _, dt in dt_matches]
        if datetimes:
            # assign first as date/time
            first = datetimes[0]
            ents["date"] = first.date()
            # only set time if not midnight
            if first.time() != first.replace(hour=0, minute=0, second=0, microsecond=0).time():
                ents["time"] = first.time()
            # keep raw list if needed
            if len(datetimes) > 1:
                ents["datetimes"] = datetimes

        # 2) Find station mentions
        found = []
        for name, code in self.stations.items():
            if re.search(rf"\b{name}\b", text, re.IGNORECASE):
                found.append((name.lower(), code))
        if found:
            # Try regex 'from X to Y'
            frmto = re.search(r"from\s+([A-Za-z ]+)\s+to\s+([A-Za-z ]+)", text, re.IGNORECASE)
            if frmto:
                dep = frmto.group(1).strip().lower()
                dst = frmto.group(2).strip().lower()
                if dep in self.stations:
                    ents["departure"] = self.stations[dep]
                if dst in self.stations:
                    ents["destination"] = self.stations[dst]
            elif len(found) >= 2:
                # fallback: first as departure/current, second as destination
                ents["departure"] = found[0][1]
                ents["destination"] = found[1][1]
            else:
                # single station mention; let dialog manager ask
                ents.setdefault("stations", []).append(found[0][1])

        # 3) Trip type
        if re.search(r"\b(return|back)\b", text, re.IGNORECASE):
            ents["trip_type"] = "return"
        elif re.search(r"\b(single|one[- ]way)\b", text, re.IGNORECASE):
            ents["trip_type"] = "single"

        # 4) Train ID (for delay prediction)
        tid = re.search(r"train\s*(\d+)", text, re.IGNORECASE)
        if tid:
            ents["train_id"] = tid.group(1)

        # 5) Delay minutes (for delay prediction)
        dm = re.search(r"(\d+)\s*minutes?", text, re.IGNORECASE)
        if dm:
            ents["delay_minutes"] = int(dm.group(1))

        return ents

    def parse(self, text):
        """
        Parse user text into intent + slots.
        """
        intent = self.predict_intent(text)
        slots = self.extract_entities(text)
        return {"intent": intent, "slots": slots}

    def missing_slots(self, intent, slots):
        """
        Given an intent and current slots, return list of missing required slots.
        """
        requirements = {
            "find_ticket": ["departure", "destination", "date", "trip_type"],
            "predict_delay": ["train_id", "current_station", "delay_minutes", "destination"]
        }
        required = requirements.get(intent, [])
        missing = []
        for key in required:
            if key not in slots:
                missing.append(key)
        return missing

# Example usage:
# nlp = NLPProcessor()\# state = nlp.parse("I need a ticket from Norwich to London on July 15 return")
# print(state)
# print(nlp.missing_slots(state['intent'], state['slots']))
