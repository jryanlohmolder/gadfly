import json
import os
import requests
import time

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Constants
API_KEY = os.getenv("API_KEY")
LEGISLATION_TYPES = {"HR", "S", "HJRES", "SJRES"}


def get_total_votes(api_key, congress):
    """
    Fetch the total number of House votes recorded for a given congress.

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 118).

    Returns:
        int: Total number of votes recorded for the given congress.

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """
    
    # Initialize Count
    count = 0
    run_cap = 5

    # Set url
    url = f"https://api.congress.gov/v3/house-vote/{congress}"
    
    while count < run_cap:
        try:
            # Build the request headers using api_key
            headers = {"X-API-KEY": api_key}
            params = {"limit": 1}

            # Make a GET request to the house-vote endpoint with limit=1
            # Just get the pagination metadata
            response = requests.get(
                url,
                headers = headers,
                params = params,
            )

            # If receive a 429
            if response.status_code == 429:
                # call back off function
                exponential_backoff(count)
                
                # Increase count
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for get_total_votes")
                # Retry from top of the loop
                continue
            
            
            # Check for other http errors
            response.raise_for_status()
            # Extract the total count from the response
            vote_count = response.json()["pagination"]["count"]

            # Return the total as an integer
            return vote_count
        
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            raise

def get_vote_data(api_key, congress, session, vote_number):
    """
    Fetch raw vote data for a single House vote from the Congress API.

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 118).
        session (int): Session number (1 or 2).
        vote_number (int): Roll call vote number.

    Returns:
        dict: Raw vote data including congress, session, roll_call_number,
              legislation_number, legislation_type, result, and date.

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """
    
    # Initialize Count
    count = 0
    run_cap = 5

    # set url
    url = f"https://api.congress.gov/v3/house-vote/{congress}/{session}/{vote_number}"

    while count < run_cap:
        try:
            # Build request headers
            headers = {"X-API-KEY": api_key}

            # Make a GET request to the vote_number end point
            response = requests.get(
                url,
                headers = headers
            )

            # If receive a 429
            if response.status_code == 429: 
                # Call exponential backoff
                exponential_backoff(count)
                # Enumerate count  
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for get_total_votes")
                # Retry from top of the loop
                continue
                    
            # handle other http errors
            response.raise_for_status()
            
            # set up base key
            base_key = response.json()["vote"]

            # generate dicitonary holding vote_data
            vote_data = {
                "congress": base_key["congress"],
                "session": base_key["session"],
                "roll_call_number": base_key["rollCallNumber"],
                "legislation_number": base_key["bill"]["number"],
                "legislation_type": base_key["bill"]["type"],
                "result": base_key["result"],
                "date": base_key["date"],
            }

            return vote_data

        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            raise
    
def check_legislation_type(vote_data):
    """ 
    Check if a vote has a legislation_type we care about in set LEGISLATION_TYPES.
    HR: House Resolution, S: Senate Bill, HJRES: House Joint Resolution, 
    SJRES: Senate Joint Resolution

    Args:
        vote_data (dict): Raw vote data including congress, session, roll_call_number,
              legislation_number, legislation_type, result, and date.

    Returns:
        boolean: True if legislation_type in LEGISLATION_TYPES. False if 
        legislation_type not in LEGISLATION_TYPES
    """

    # Get legislation type and verify if it is in LEGISLATION_TYPES
    leg_type = vote_data.get("legislation_type")
    return leg_type in LEGISLATION_TYPES

def get_vote_metadata(vote_data):
    """
    Gets the meta data from get_vote_data() and sets it up for the Vote DB

    Args:
        vote_data (dict): Raw vote data including congress, session, 
        roll_call_number, legislation_number, legislation_type, result, and date.

    Return:
        meta_data (dict): Vote meta data including congress, session, roll_call_number,
        legislation_number, legislation_type, result, and date.  
    """

    # Alter date data to date formate
    date = datetime.strptime(vote_data["date"], "%Y-%m-%d").date()
    
    # Ensure we only get key, value pairs wanted for Vote DB
    return  {
        "congress": vote_data["congress"],
        "session": vote_data["session"],
        "roll_call_number": vote_data["roll_call_number"],
        "legislation_number": vote_data["legislation_number"],
        "legislation_type": vote_data["legislation_type"],
        "result": vote_data["result"],
        "date": date,
    } 

def fetch_member_positions(api_key, congress, session, vote_number):
    """
    Fetch how members of congress voted on piece of legislation.

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 118).
        session (int): Session number (1 or 2).
        vote_number (int): Roll call vote number.

    Returns:
        list[dict]: a list of dicts, each stating how one member voted

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """
    
    # Initialize Count
    count = 0
    run_cap = 5

    # Set url
    url = f"https://api.congress.gov/v3/house-vote/{congress}/{session}/{vote_number}/members"

    while count < run_cap:
        try:
            # Build request headers
            headers = {"X-API-KEY": api_key}

            # Make a GET request to the members end point
            response = requests.get(
                url,
                headers = headers,
            )

            # If receive a 429:
            if response.status_code == 429:
                
                # Call exponential back off
                exponential_backoff(count)
                # Enumerate count
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for fetch_member_positions")
                # Retry from top of loop
                continue
                    
            
            # Check for other HTTP errors
            response.raise_for_status()

            # Convert json data to dict
            vote_data = response.json()

            return vote_data["houseRollCallVoteMemberVotes"]["results"]


        except requests.exceptions.RequestException as e:
            print(f"Network Error {e}")
            raise

def fetch_bill_url(api_key, congress, bill_type, bill_number):
    """
    Fetch the url for legislation

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 118).
        bill_type (str): Either hr, s, hjres, sjres, from legislation_type in get_vote_data()
        bill_number (int): from legislation_number in get_vote_data()

    Returns:
        url: a link to the bills text either in HTM or XML

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        ValueError: No readable text format found for bill
        requests.exceptions.RetryError: If run_cap number is reached.
    """
    
    # Initialize count
    count = 0
    run_cap = 5

    # Set url
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/text"

    while count < run_cap:
        try:
            # Build request headers
            headers = {"X-API-KEY": api_key}

            # Make a GET request to text endpoint
            response = requests.get(
                url,
                headers = headers
            )

            # If receive a 429:
            if response.status_code == 429:
                
                # Call exponential backoff
                exponential_backoff(count)
                # Enumerate count
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for fetch_bill")
                continue
                
            # Check for other HTTP errors
            response.raise_for_status()

            # Get url for bill
            formats = response.json()["textVersions"][0].get("formats", [])
            bill_url = next((f["url"] for f in formats if f["type"] == "Formatted Text"), None)

            # If formatted text is not available
            if bill_url is None:
                bill_url = next((f["url"] for f in formats if f["type"] == "Formatted XML"), None)
            if bill_url is None:
                raise ValueError(f"No readable text format found for bill {bill_type}{bill_number}")

            return bill_url

        except requests.exceptions.RequestException as e:
            print(f"Network Error {e}")
            raise

def fetch_bill_text():
    pass

def parse_billl():
    pass

def store_categories():
    pass

def store_summary():
    pass

def exponential_backoff(count):
    """
    This function is designed to prevent repeated 429 errors

    Args:
        count (int): The number of runs repeated because of 429 error
    """
    time.sleep(2 ** count)

def main():
    pass