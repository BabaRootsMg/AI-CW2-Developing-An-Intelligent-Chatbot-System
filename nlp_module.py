# File: stations_loader.py
import csv
from pathlib import Path

def load_station_dict(csv_path: Path) -> dict[str, str]:
    """
    Load a CSV of UK stations with columns:
      official_name, long_name, name_alias, alpha3, tiploc
    Returns a dict mapping each official_name, long_name, and name_alias (lowercased)
    to its 3-letter code.
    """
    station_map: dict[str, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            official, longname, alias, alpha3, tiploc = row
            code = alpha3.strip() or tiploc.strip()
            if not code or code == "\\N":
                continue
            for key in (official, longname, alias):
                if key and key != "\\N":
                    station_map[key.lower()] = code
    return station_map


# File: nlp_module.py
import re
import logging
import spacy
from spacy.matcher import PhraseMatcher
from dateparser.search import search_dates
from pathlib import Path
from stations_loader import load_station_dict
import difflib

class NLPProcessor:
    """
    NLP Processor for intent classification, entity extraction, and slot filling.
    Uses a full station list with fuzzy fallback for user input.
    """
    def __init__(self, station_dict: dict[str,str]=None, stations_csv_path: str=None):
        self.logger = logging.getLogger(__name__)
        self.nlp = spacy.load("en_core_web_sm")
        if station_dict is None and stations_csv_path:
            station_dict = load_station_dict(Path(stations_csv_path))
        self.stations = station_dict or {
            "norwich": "NWI",
            "london": "LST",
            "oxford": "OXF",
            "ipswich": "IPS"
        }
        # PhraseMatcher setup
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp.make_doc(name) for name in self.stations.keys()]
        self.matcher.add("STATION", patterns)
        # Intent keywords
        self.intent_keywords = {
            "find_ticket": ["ticket","price","journey","cheapest","book","train","travel","trip","fare"],
            "predict_delay": ["delay","late","arrival","predict","delayed"]
        }
        # Precompile regex
        self._pat_return = re.compile(r"\b(return|back)\b", re.IGNORECASE)
        self._pat_single = re.compile(r"\b(single|one[- ]way)\b", re.IGNORECASE)
        self._pat_train  = re.compile(r"train\s*(\d+)", re.IGNORECASE)
        self._pat_delay  = re.compile(r"(\d+)\s*minutes?", re.IGNORECASE)

    def predict_intent(self, text: str) -> tuple[str,float]:
        txt = text.lower()
        scores = { intent: sum(1 for kw in kws if kw in txt) for intent,kws in self.intent_keywords.items() }
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])
        total = sum(len(kws) for kws in self.intent_keywords.values())
        confidence = best_score/total if total else 0.0
        if best_score == 0:
            return "unsupported", confidence
        return best_intent, confidence

    def extract_datetimes(self, text: str) -> dict:
        slots = {}
        matches = search_dates(text, settings={"PREFER_DATES_FROM":"future"}) or []
        dates = [dt for _,dt in matches]
        if dates:
            first = dates[0]
            slots['date'] = first.date()
            if first.time()!=first.replace(hour=0,minute=0,second=0,microsecond=0).time():
                slots['time'] = first.time()
            if len(dates)>1:
                second = dates[1]
                slots['return_date'] = second.date()
                if second.time()!=second.replace(hour=0,minute=0,second=0,microsecond=0).time():
                    slots['return_time'] = second.time()
        return slots

    def extract_stations(self, text: str, intent: str) -> dict:
        doc = self.nlp(text)
        matches = self.matcher(doc)
        found = [doc[start:end].text.lower() for _,start,end in matches]
        unique = list(dict.fromkeys(found))
        slots = {}
        if intent=='predict_delay':
            if unique:
                slots['current_station']=self.stations[unique[0]]
            if len(unique)>1:
                slots['destination']=self.stations[unique[1]]
        else:
            frmto = re.search(r"from\s+([A-Za-z ]+?)\s+to\s+([A-Za-z ]+?)\b", text, re.IGNORECASE)
            if frmto:
                dep=frmto.group(1).strip().lower(); dst=frmto.group(2).strip().lower()
                dc=self.stations.get(dep); ec=self.stations.get(dst)
                if dc and ec:
                    return {'departure':dc,'destination':ec}
            if len(unique)>=2:
                slots['departure']=self.stations[unique[0]]
                slots['destination']=self.stations[unique[1]]
            elif unique:
                slots['stations']=[self.stations[unique[0]]]
        # fuzzy fallback
        if not slots and len(text)<40:
            cand=difflib.get_close_matches(text.lower(), self.stations.keys(), n=1, cutoff=0.8)
            if cand:
                slots['stations']=[self.stations[cand[0]]]
        return slots

    def extract_trip_type(self, text: str) -> str|None:
        if self._pat_return.search(text): return 'return'
        if self._pat_single.search(text): return 'single'
        return None

    def extract_train_info(self, text: str) -> dict:
        slots={}
        tid=self._pat_train.search(text)
        if tid: slots['train_id']=tid.group(1)
        dm=self._pat_delay.search(text)
        if dm: slots['delay_minutes']=int(dm.group(1))
        return slots

    def parse(self, text: str) -> dict:
        intent,conf=self.predict_intent(text)
        slots={}
        slots.update(self.extract_datetimes(text))
        slots.update(self.extract_stations(text,intent))
        tp=self.extract_trip_type(text)
        if tp: slots['trip_type']=tp
        if intent=='predict_delay': slots.update(self.extract_train_info(text))
        return {'intent':intent,'confidence':conf,'slots':slots}

    def missing_slots(self, intent: str, slots: dict) -> list[str]:
        reqs={'find_ticket':['departure','destination','date','trip_type'],
              'predict_delay':['train_id','current_station','delay_minutes','destination']}
        return [k for k in reqs.get(intent,[]) if k not in slots]


