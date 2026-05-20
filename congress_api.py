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
            while count < run_cap:
                # call back off function
                exponential_backoff(count)
                # try calling again
                response = requests.get(
                    url,
                    headers = headers,
                    params = params,
                )

                # check if call worked
                if response.status_code == 200:
                    vote_count = response.json()["pagination"]["count"]
                    break
                
                # Increase count
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for get_total_votes")
        
        else:
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
            while count < run_cap:
                # call exponential backoff
                exponential_backoff(count)
                # try call again
                response = requests.get(
                    url,
                    headers = headers
                )

                # check if call worked
                if response.status_code == 200:
                    break     
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for get_total_votes")
                
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
            while count < run_cap:
                # Call exponential back off
                exponential_backoff(count)
                # Try call again
                response = requests.get(
                    url,
                    headers = headers,
                )

                if response.status_code == 200:
                    break
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for get_total_votes")
                
        else:
            # Check for other HTTP errors
            response.raise_for_status()

        # Convert json data to dict
        vote_data = response.json()

        return vote_data["houseRollCallVoteMemberVotes"]["results"]


    except requests.exceptions.RequestException as e:
        print(f"Network Error {e}")
        raise

def fetch_bill():
    pass

def parse_bill():
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