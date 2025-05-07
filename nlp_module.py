import re
import logging
import spacy
from spacy.matcher import PhraseMatcher
from dateparser.search import search_dates

class NLPProcessor:
    """
    NLP Processor for intent classification, entity extraction, and slot filling.
    Refactored for efficiency, confidence scoring, and modular extraction.
    """
    def __init__(self, station_dict=None):
        # Logger setup
        self.logger = logging.getLogger(__name__)
        # Load spaCy English model once
        self.nlp = spacy.load("en_core_web_sm")

        # Station name-to-code mapping
        self.stations = station_dict or {
            "norwich": "NWI",
            "london": "LST",
            "oxford": "OXF",
            "ipswich": "IPS"
        }
        # Setup PhraseMatcher for station names
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp.make_doc(name) for name in self.stations]
        self.matcher.add("STATION", patterns)

        # Intent keywords for simple intent classification
        self.intent_keywords = {
            "find_ticket": [
                "ticket", "price", "journey", "cheapest", "book",
                "train", "travel", "trip", "fare"
            ],
            "predict_delay": ["delay", "late", "arrival", "predict", "delayed"]
        }

        # Precompile regex patterns once
        self._pat_return = re.compile(r"\b(return|back)\b", re.IGNORECASE)
        self._pat_single = re.compile(r"\b(single|one[- ]way)\b", re.IGNORECASE)
        self._pat_train = re.compile(r"train\s*(\d+)", re.IGNORECASE)
        self._pat_delay = re.compile(r"(\d+)\s*minutes?", re.IGNORECASE)

    def predict_intent(self, text):
        """
        Determine user intent and confidence based on keyword matching.
        Returns (intent, confidence).
        """
        txt = text.lower()
        scores = {
            intent: sum(1 for kw in kws if kw in txt)
            for intent, kws in self.intent_keywords.items()
        }
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])
        total = sum(len(kws) for kws in self.intent_keywords.values())
        confidence = best_score / total if total else 0.0
        if best_score == 0:
            self.logger.debug("No intent keywords matched; marking as unsupported")
            return "unsupported", confidence
        self.logger.debug(f"Intent '{best_intent}' with confidence {confidence:.2f}")
        return best_intent, confidence

    def extract_datetimes(self, text):
        """
        Extract date and time mentions using dateparser.
        Returns dict with 'date', 'time', and optional 'return_date'.
        """
        slots = {}
        matches = search_dates(text, settings={"PREFER_DATES_FROM": "future"}) or []
        dates = [dt for _, dt in matches]
        if dates:
            first = dates[0]
            slots['date'] = first.date()
            if first.time() != first.replace(hour=0, minute=0, second=0, microsecond=0).time():
                slots['time'] = first.time()
            if len(dates) > 1:
                second = dates[1]
                slots['return_date'] = second.date()
                if second.time() != second.replace(hour=0, minute=0, second=0, microsecond=0).time():
                    slots['return_time'] = second.time()
        self.logger.debug(f"Extracted datetimes: {slots}")
        return slots

    def extract_stations(self, text, intent):
        """
        Use PhraseMatcher to find station mentions.
        For 'find_ticket', assign 'departure' and 'destination'.
        For 'predict_delay', assign 'current_station' and 'destination'.
        """
        doc = self.nlp(text)
        matches = self.matcher(doc)
        found = []
        for _, start, end in matches:
            span = doc[start:end].text.lower()
            if span in self.stations:
                found.append(span)
        unique = list(dict.fromkeys(found))
        slots = {}
        if intent == 'predict_delay':
            if unique:
                slots['current_station'] = self.stations[unique[0]]
            if len(unique) > 1:
                slots['destination'] = self.stations[unique[1]]
        else:
            # Try regex-based 'from X to Y' only if codes valid
            frmto = re.search(r"from\s+([A-Za-z ]+?)\s+to\s+([A-Za-z ]+?)\b", text, re.IGNORECASE)
            if frmto:
                dep_raw = frmto.group(1).strip().lower()
                dst_raw = frmto.group(2).strip().lower()
                dep_code = self.stations.get(dep_raw)
                dst_code = self.stations.get(dst_raw)
                if dep_code and dst_code:
                    slots['departure'] = dep_code
                    slots['destination'] = dst_code
                    self.logger.debug(f"Extracted stations via regex: {slots}")
                    return slots
            # Fallback to ordered mentions
            if len(unique) >= 2:
                slots['departure'] = self.stations[unique[0]]
                slots['destination'] = self.stations[unique[1]]
            elif unique:
                slots['stations'] = [self.stations[unique[0]]]
        self.logger.debug(f"Extracted stations: {slots}")
        return slots

    def extract_trip_type(self, text):
        """
        Detect 'single' vs 'return' trip type.
        """
        if self._pat_return.search(text):
            return 'return'
        if self._pat_single.search(text):
            return 'single'
        return None

    def extract_train_info(self, text):
        """
        Extract train_id and delay_minutes for delay prediction.
        """
        slots = {}
        tid = self._pat_train.search(text)
        if tid:
            slots['train_id'] = tid.group(1)
        dm = self._pat_delay.search(text)
        if dm:
            slots['delay_minutes'] = int(dm.group(1))
        self.logger.debug(f"Extracted train info: {slots}")
        return slots

    def parse(self, text):
        """
        Parse user text into intent, confidence, and slots.
        """
        intent, confidence = self.predict_intent(text)
        slots = {}
        slots.update(self.extract_datetimes(text))
        slots.update(self.extract_stations(text, intent))
        trip = self.extract_trip_type(text)
        if trip:
            slots['trip_type'] = trip
        if intent == 'predict_delay':
            slots.update(self.extract_train_info(text))
        self.logger.info(f"Parsed intent={intent}, confidence={confidence:.2f}, slots={slots}")
        return {'intent': intent, 'confidence': confidence, 'slots': slots}

    def missing_slots(self, intent, slots):
        """
        Given intent and current slots, return list of missing required slots.
        """
        requirements = {
            "find_ticket": ["departure", "destination", "date", "trip_type"],
            "predict_delay": ["train_id", "current_station", "delay_minutes", "destination"]
        }
        req = requirements.get(intent, [])
        missing = [k for k in req if k not in slots]
        self.logger.debug(f"Missing slots for intent '{intent}': {missing}")
        return missing
