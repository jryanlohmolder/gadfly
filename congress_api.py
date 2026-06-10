import os
import requests
import time

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Constants
API_KEY = os.getenv("CONGRESS_API_KEY")
LEGISLATION_TYPES = {"HR", "S", "HJRES", "SJRES"}

def get_all_votes(api_key, congress):
    """
    Fetch all House roll call votes for a given congress that are tied to
    legislation types we care about (HR, S, HJRES, SJRES).

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 119).

    Returns:
        list[dict]: A list of dicts, each containing congress, session,
            roll_call_number, legislation_number, legislation_type, result,
            and date for a single vote.

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """

    # Set url
    url = f"https://api.congress.gov/v3/house-vote/{congress}"

    # Set run cap
    run_cap = 5

    # Empty all votes list
    all_votes = []

    while url:
        # Initialize Count
        count = 0
    
        while count < run_cap:
            try:
                # Build the request headers using api_key
                headers = {"X-API-KEY": api_key}

                # Make a GET request to the house-vote endpoint with limit=1
                # Just get the pagination metadata
                response = requests.get(
                    url,
                    headers = headers,
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

                # Get all relevant votes
                data = response.json()
                votes = data["houseRollCallVotes"]
                break
            
            except requests.exceptions.RequestException as e:
                print(f"Network error: {e}")
                raise

        for vote in votes:
            if vote.get("legislationType") in LEGISLATION_TYPES:
                relevant_vote = {}
                relevant_vote["congress"] = congress
                relevant_vote["session"] = vote["sessionNumber"]
                relevant_vote["roll_call_number"] = vote["rollCallNumber"]
                relevant_vote["legislation_number"] = vote["legislationNumber"]
                relevant_vote["legislation_type"] = vote["legislationType"].lower()
                relevant_vote["result"] = vote["result"]
                relevant_vote["date"] = datetime.strptime(vote["startDate"], "%Y-%m-%dT%H:%M:%S%z").date()

                all_votes.append(relevant_vote)

        # Set url pagination to next or None
        if data["pagination"]["next"]:
            url = data["pagination"]["next"] + "&api_key=" + api_key
        else:
            url = None

    return all_votes

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

            # Extract member vote data
            data = response.json()["houseRollCallVoteMemberVotes"]["results"]
            
            # Create empty list of member votes
            member_votes = []

            for entry in data:
                member_vote = {}
                member_vote["member_id"] = entry["bioguideID"]
                member_vote["position"] = entry["voteCast"]

                # Add member position to member votes list
                member_votes.append(member_vote)

            return member_votes


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
        bill_url: a link to the bills text either in HTM or XML

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
                    raise requests.exceptions.RetryError("Max retries exceeded for fetch_bill_url")
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

def fetch_bill_text(bill_url):
    """
    Fetch the text of the specific legislation.

    Args:
        bill_url (str): The url linked to the legislation returned from fetch_bill_url()

    Returns:
        response.text(str): The body of the bill that will be parsed by Claude

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        ValueError: No readable text found for bill
        requests.exceptions.RetryError: If run_cap number is reached.
    """

    # Initialize count
    count = 0
    run_cap = 5

    while count < run_cap:
        try:
            # Make GET request to bill url
            response = requests.get(bill_url)

            # If receive a 429:
            if response.status_code == 429:

                # call exponential backoff
                exponential_backoff(count)
                # enumerate count
                count += 1

                if count == run_cap:
                    raise requests.exceptions.RetryError("Max retries exceeded for fetch_bill_text")
                continue

            # Check for other HTTP errors
            response.raise_for_status()

            # Return bill text
            if not response.text or not response.text.strip():
                raise ValueError(f"Empty response body from {bill_url}")
            
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Network Error {e}")
            raise
    
def get_all_members(api_key, congress):
    """
    Fetch all current members of congress and relevant data to populate Members Database

    Args:
        api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g., 118).

    Returns:
        list[dict]: a list of dicts, each containing members bioguide ID, name, state, party, chamber,
        url link of picture, and attribution for the picture

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """

    # Empty representatives list
    representatives = []

    # Set url
    url = f"https://api.congress.gov/v3/member/congress/{congress}?api_key={api_key}&limit=20"

    # Set run cap
    run_cap = 5
    
    while url:
        # Initialize count
        count = 0
        
        while count < run_cap:
            try:
                # make API call (with error handling)
                response = requests.get(url)

                # If receive a 429
                if response.status_code == 429:
                    # Call exponential back off
                    exponential_backoff(count)
                    # enumerate count
                    count += 1

                    if count == run_cap:
                        raise requests.exceptions.RetryError("Max retries exceeded for get_all_members")
                    continue

                # Check for other HTTP errors
                response.raise_for_status()

                # extract members
                data = response.json()
                members = data["members"]
                break
            
            except requests.exceptions.RequestException as e:
                print (f"Network error: {e}")
                raise
        
        # loop over members on this page
        for member in members:
            member_dict = {}

            # extract fields and append to members
            member_dict["member_id"] = member["bioguideId"]
            member_dict["name"] = member["name"]
            member_dict["state"] = member["state"]
            member_dict["district"] = member.get("district")
            member_dict["party"] = member["partyName"]

            # extract member's chamber
            for item in member["terms"]["item"]:
                if "endYear" not in item.keys():
                    member_dict["chamber"] = item["chamber"]

            member_dict["picture_url"] = member.get("depiction", {}).get("imageUrl")
            member_dict["photo_cred"] = member.get("depiction", {}).get("attribution")

            # Add member_dict to representatives list
            if "chamber" in member_dict.keys():
                representatives.append(member_dict)

        # set url to pagination["next"] or None
        if data["pagination"]["next"]:
            url = data["pagination"]["next"] + "&api_key=" + api_key
        else:
            url = None
    
    return representatives

def get_sponsored_leg(api_key, member_id):
    """
    Fetch all sponsored legislation for a member of congress to populate SponsoredLegislation database.
    
    Args:
        api_key (str): Congress API authentication key.
        member_id (str): Member's bioguide ID (e.g., 'W000779').
    
    Returns:
        list[dict]: A list of dicts, each containing a legislation number and policy area.
    
    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """

    # Empty List of Sponsored Legislation
    sponsored_bills = []

    # URL
    url = f"https://api.congress.gov/v3/member/{member_id}/sponsored-legislation?api_key={api_key}&limit=20"

    run_cap = 5
    
    while url:
        # Initialize count
        count = 0

        while count < run_cap:
            try:
                # Make API call
                response = requests.get(url)

                # If 429 error received 
                if response.status_code == 429:
                    # Call exponential backoff
                    exponential_backoff(count)
                    # Enumerate count
                    count += 1

                    # If count equals run_cap
                    if count == run_cap:
                        raise requests.exceptions.RetryError("Max retries exceeded for get_sponsored_leg")
                    continue

                # Check for other HTTP Errors
                response.raise_for_status()

                # Extract legislation
                data = response.json()
                leg = data["sponsoredLegislation"]
                break
            
            except requests.exceptions.RequestException as e:
                print(f"Network error: {e}")
                raise

        # Loop of legislation
        for bill in leg:
            sponsored_leg = {}

            # Verify if policy type is in LEGISLATION_TYPES
            if bill["type"] in LEGISLATION_TYPES:
                # Extract legislation number and policy area
                sponsored_leg["legislation_number"] = bill["number"]
                sponsored_leg["policy_area"] = bill.get("policyArea", {}).get("name")
                sponsored_leg["legislation_type"] = bill["type"]
                
                # Add dict to sponsored legislation
                sponsored_bills.append(sponsored_leg)

        # Set url pagination to next or None
        if data["pagination"]["next"]:
            url = data["pagination"]["next"] + "&api_key=" + api_key
        else:
            url = None
            
    return sponsored_bills

def get_cosponsored_leg(api_key, member_id):
    """
    Fetch all cosponsored legislation for a member of congress to populate CosponsoredLegislation database.
    
    Args:
        api_key (str): Congress API authentication key.
        member_id (str): Member's bioguide ID (e.g., 'W000779').
    
    Returns:
        list[dict]: A list of dicts, each containing a legislation number and policy area.
    
    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap number is reached.
    """

    # Empty List of Sponsored Legislation
    cosponsored_bills = []

    # URL
    url = f"https://api.congress.gov/v3/member/{member_id}/cosponsored-legislation?api_key={api_key}&limit=20"

    run_cap = 5
    
    while url:
        # Initialize count
        count = 0

        while count < run_cap:
            try:
                # Make API call
                response = requests.get(url)

                # If 429 error received 
                if response.status_code == 429:
                    # Call exponential backoff
                    exponential_backoff(count)
                    # Enumerate count
                    count += 1

                    # If count equals run_cap
                    if count == run_cap:
                        raise requests.exceptions.RetryError("Max retries exceeded for get_cosponsored_leg")
                    continue

                # Check for other HTTP Errors
                response.raise_for_status()

                # Extract legislation
                data = response.json()
                leg = data["cosponsoredLegislation"]
                break
            
            except requests.exceptions.RequestException as e:
                print(f"Network error: {e}")
                raise

        # Loop of legislation
        for bill in leg:
            cosponsored_leg = {}

            # Verify if policy type is in LEGISLATION_TYPES
            if bill["type"] in LEGISLATION_TYPES:
                # Extract legislation number and policy area
                cosponsored_leg["legislation_number"] = bill["number"]
                cosponsored_leg["policy_area"] = bill.get("policyArea", {}).get("name")
                cosponsored_leg["legislation_type"] = bill["type"]
                
                # Add dict to sponsored legislation
                cosponsored_bills.append(cosponsored_leg)

        # Set url pagination to next or None
        if data["pagination"]["next"]:
            url = data["pagination"]["next"] + "&api_key=" + api_key
        else:
            url = None
            
    return cosponsored_bills

def exponential_backoff(count):
    """
    This function is designed to prevent repeated 429 errors

    Args:
        count (int): The number of runs repeated because of 429 error
    """
    time.sleep(2 ** count)

def main():
    pass
