import logging
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from nlp_module import NLPProcessor
from trainlinescraper import find_cheapest_ticket

class Chatbot:
    """
    Chatbot class logic handling dialogue state, external calls, and responses.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Load NLP with full station list
        self.nlp = NLPProcessor(stations_csv_path="Task2/data/stations.csv")
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._reset_state()

    def _reset_state(self):
        """Clear dialogue state for a new conversation."""
        self.state = {"intent": None, "slots": {}}
        self.confirm_done = False

    def respond(self, user_text: str) -> str:
        """Generate a response for the user's message."""
        raw = user_text.strip()
        text = raw.lower()

        # If we're waiting on station confirmation:
        if self.state.get("intent") == "find_ticket" and self.confirm_done:
            # Positive confirmation
            if re.match(r'^(yes|y|correct|right)\b', text):
                self.logger.info("User confirmed stations")
                return self._handle_find_ticket()
            # Negative confirmation (e.g. "no", "no not correct")
            if re.match(r'^(no|n)\b', text) or "not correct" in text:
                self.logger.info("User denied station confirmation")
                self.confirm_done = False
                # Clear previously captured stations
                slots = self.state["slots"]
                slots.pop("departure", None)
                slots.pop("destination", None)
                return "(Info needed) Where are you departing from?"

        # Standard parse
        parsed = self.nlp.parse(raw)
        intent = parsed["intent"]
        confidence = parsed["confidence"]
        slots = parsed["slots"]
        self.logger.debug(f"Parsed intent={intent} (conf={confidence:.2f}), slots={slots}")

        # First turn: guard unsupported or very low confidence
        if self.state["intent"] is None:
            if intent == "unsupported" or confidence < 0.05:
                self.logger.info("Fallback on first turn: unsupported or low confidence")
                self._reset_state()
                return (
                    "Sorry, I can only help with UK train enquiries. "
                    "Could you rephrase or ask about train tickets or delays?"
                )
            self.state["intent"] = intent

        # Update slots
        self.state["slots"].update(slots)

        # Route to the appropriate handler
        if self.state["intent"] == "find_ticket":
            return self._handle_find_ticket()

        # Catch-all fallback
        self._reset_state()
        return "Sorry, I don't know how to help with that."

    def _handle_find_ticket(self) -> str:
        """Slot-filling and ticket lookup logic."""
        s = self.state["slots"]

        # Promote any fuzzy‐matched station codes
        if "stations" in s:
            codes = s.pop("stations")
            if "departure" not in s and codes:
                s["departure"] = codes[0]
            elif "destination" not in s and codes:
                s["destination"] = codes[0]

        # Build reverse map: code -> pretty station name
        code_to_name = {}
        for name, code in self.nlp.stations.items():
            if code not in code_to_name:
                pretty = name.title().replace(" Rail Station", "")
                code_to_name[code] = pretty

        # Step 1: Confirm stations (use full names)
        if not self.confirm_done:
            if "departure" in s and "destination" in s:
                dep_name = code_to_name.get(s["departure"], s["departure"])
                dst_name = code_to_name.get(s["destination"], s["destination"])
                self.confirm_done = True
                self.logger.info("Asking station confirmation")
                return (
                    f"Just to confirm: you want to travel from {dep_name} to {dst_name}, correct?"
                )
            # If one of the stations is missing, prompt for it immediately
            if "departure" not in s:
                return "(Info needed) Where are you departing from?"
            if "destination" not in s:
                return "(Info needed) Where are you going to?"

        # Step 2: Prompt for missing slots in logical order
        if "date" not in s:
            return "(Info needed) On what date would you like to travel? (e.g. 2025-07-15)"
        if "time" not in s:
            return "(Info needed) At what time would you prefer? Please use 24-hour HH:MM format."
        if "trip_type" not in s:
            return "(Info needed) Is this a single or return trip?"

        # Step 3: All slots present – perform ticket search
        dep_name = code_to_name.get(s["departure"], s["departure"])
        dst_name = code_to_name.get(s["destination"], s["destination"])

        self.logger.info(f"All slots filled: {s}, initiating ticket search")
        future = self.executor.submit(
            find_cheapest_ticket,
            departure=dep_name,
            destination=dst_name,
            date=s["date"],
            time_of_day=s.get("time"),
            trip_type=s["trip_type"]
        )

        try:
            ticket = future.result(timeout=300)
        except TimeoutError:
            self.logger.error("Ticket search timed out")
            self._reset_state()
            return "Sorry, searching for tickets is taking too long. Please try again later."
        except Exception:
            self.logger.exception("Error during ticket search")
            self._reset_state()
            return "Oops, something went wrong fetching tickets. Try again later."

        # Step 4: Present result and reset
        response = f"The cheapest fare is £{ticket.price:.2f}. Book here: {ticket.url}"
        self.logger.info("Presented cheapest ticket to user")
        self._reset_state()
        return response

# Singleton instance for GUI/CLI
_bot = Chatbot()

def get_bot_response(msg: str) -> str:
    return _bot.respond(msg)
