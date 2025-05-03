"""
ticket_search.py
----------------
This module searches for available train tickets based on user-specified journey details.
It scrapes or queries online train ticket sources (e.g., Trainline, National Rail)
and identifies the cheapest suitable option. Returns pricing and booking link.

-Implements the logic to scrape or query train ticket websites

-Parses and returns the cheapest ticket with booking link

-Handles journey parameters: origin, destination, date, time, return/single
"""

# Example imports (adjust as needed)
import requests
from bs4 import BeautifulSoup

# Example base URL (replace with the real site or API endpoint)
BASE_URL = "https://www.exampletrainbooking.com/search"


def get_cheapest_ticket(origin, destination, date, return_date=None, depart_before=None, return_after=None):
    """
    Retrieves the cheapest available train ticket for the given journey.

    Parameters:
        origin (str): Departure station name
        destination (str): Arrival station name
        date (str): Travel date (format: YYYY-MM-DD)
        return_date (str, optional): Return trip date
        depart_before (str, optional): Preferred departure time (e.g., "10:00")
        return_after (str, optional): Preferred return time for return leg (e.g., "14:00")

    Returns:
        dict: Contains ticket price, departure time, arrival time, and booking link
    """

    # TODO: Format the request or scraping logic to fetch results from chosen website/API
    # For now, return mock data
    return {
        "price": "£18.50",
        "departure": "09:30",
        "arrival": "11:15",
        "booking_link": "https://www.exampletrainbooking.com/book/12345"
    }

# Additional helper functions can go here
# e.g., def parse_ticket_html(html): ...

def build_search_url(origin, destination, date, return_date=None):
    """
    Builds the search URL or request parameters for the ticket website based on journey details.
    Returns a complete URL or a parameters dictionary for requests.
    """
    # Example: Format into GET parameters for scraping or an API
    return f"{BASE_URL}?from={origin}&to={destination}&date={date}"


def fetch_ticket_page(url):
    """
    Sends a request to the ticket booking website and retrieves the HTML content.
    Returns the raw HTML text.
    """
    headers = {"User-Agent": "Mozilla/5.0"}  # Helps bypass bot detection
    response = requests.get(url, headers=headers)
    return response.text


def parse_ticket_html(html):
    """
    Parses HTML and extracts ticket options: price, times, and link.
    Returns a list of ticket dicts.
    """
    soup = BeautifulSoup(html, "html.parser")
    ticket_list = []

    # TODO: Modify based on real HTML structure
    for result in soup.select(".ticket-option"):
        price = result.select_one(".price").text.strip()
        departure = result.select_one(".departure-time").text.strip()
        arrival = result.select_one(".arrival-time").text.strip()
        link = result.select_one("a.book-button")["href"]

        ticket_list.append({
            "price": price,
            "departure": departure,
            "arrival": arrival,
            "booking_link": link
        })

    return ticket_list


def select_cheapest_ticket(tickets):
    """
    Selects the cheapest ticket from a list of ticket dictionaries.
    Assumes price format like '£18.50'. Returns one dict.
    """
    def price_to_float(ticket):
        return float(ticket['price'].replace('£', ''))

    return min(tickets, key=price_to_float)


