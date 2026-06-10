import anthropic_api
import congress_api
import database

from dotenv import load_dotenv
import os

load_dotenv()

congress_api_key = os.getenv("CONGRESS_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

def load_members(congress_api_key, congress, engine=None):
    """
    Fetches all members for a given congress and stores them along with
    their sponsored and cosponsored legislation. Skips members already
    in the database along with their legislation.

    Args:
        congress_api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g. 118).
        engine: SQLAlchemy engine. Creates one if not provided.

    Returns:
        None

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap is reached.
        sqlalchemy.exc.SQLAlchemyError: If any database operation fails.
    """

    # Get all members
    members = congress_api.get_all_members(congress_api_key, congress)

    # Loop over all members
    for member in members:
        # Skip if member already exists
        if database.member_exists(member["member_id"]):
            continue

        # Get sponsored and co-sponsored legislation
        sponsored_leg = congress_api.get_sponsored_leg(congress_api_key, member["member_id"])
        cosponsored_leg = congress_api.get_cosponsored_leg(congress_api_key, member["member_id"])

        # Store members, sponsored and co-sponsored legislation
        database.store_member(
            member["member_id"], member["name"], 
            member["state"], member["district"],
            member["party"], member["chamber"],
            member["picture_url"], member["photo_cred"],
            engine=engine
            )
        
        for leg in sponsored_leg:
            database.store_sponsored_legislation(
                member["member_id"], leg["legislation_number"],
                leg["legislation_type"], leg["policy_area"],
                engine=engine
                )
            
        for leg in cosponsored_leg:
            database.store_cosponsored_legislation(
                member["member_id"], leg["legislation_number"],
                leg["legislation_type"], leg["policy_area"],
                engine=engine
            )

    # Print progress
    print(f"load_members complete: {len(members)} members processed")

def load_votes(congress_api_key, congress, engine=None):
    """
    Fetches all votes for a given congress and stores them along with
    bill text and member positions. Skips votes already in the database.

    Args:
        congress_api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g. 118).
        engine: SQLAlchemy engine. Creates one if not provided.

    Returns:
        None

    Raises:
        requests.exceptions.HTTPError: If a non-429 HTTP error is returned.
        requests.exceptions.RequestException: If a network error occurs.
        requests.exceptions.RetryError: If run_cap is reached.
        sqlalchemy.exc.SQLAlchemyError: If any database operation fails.
    """
    
    # Get all votes
    votes = congress_api.get_all_votes(congress_api_key, congress)
    
    # Loop over votes
    for vote in votes:
        # Check if vote exists
        if database.vote_exists(vote["congress"], vote["session"], vote["roll_call_number"]):
            continue

        # Get bill url
        bill_url = congress_api.fetch_bill_url(congress_api_key, congress,vote["legislation_type"], vote["legislation_number"])                         
        
        # Get bill text
        bill_text = congress_api.fetch_bill_text(bill_url)

        # Get member positions
        member_positions = congress_api.fetch_member_positions(congress_api_key, congress, vote["session"], vote["roll_call_number"])

        # Add bill text to vote dict
        vote["bill_text"] = bill_text

        # Store vote / get vote id
        vote_id = database.store_vote(vote, engine=engine)

        # Store member vote
        for position in member_positions:
            database.store_member_vote(position["member_id"], vote_id, position["position"], engine=engine)

    # Print progress
    print(f"load_votes complete: {len(votes)}")

def categorize_votes(engine, limit=None):
    """
    Fetches all unanalyzed votes and runs them through the LLM pipeline,
    storing summaries, categories, and flags. Skips votes that have
    already been analyzed. 

    Args:
        engine: SQLAlchemy engine. Creates one if not provided.
        limit (int): Optional cap on how many votes to process.
            Defaults to None (process all unanalyzed votes).

    Returns:
        None

    Raises:
        json.JSONDecodeError: If Claude returns malformed JSON.
        ValueError: If all chunks fail JSON parsing.
        requests.exceptions.RetryError: If run_cap is reached.
        anthropic.APIError: If a non-429 API error is returned.
        sqlalchemy.exc.SQLAlchemyError: If any database operation fails.
    """
    
    # Get unanalyzed votes
    votes = database.get_unanalyzed_votes(engine)
    # Check if there is a limit
    if limit is not None:
        votes = votes[:limit]

    # Loop over votes
    for vote in votes:
        # Parse the bill text
        result = anthropic_api.parse_bill_text(vote["bill_text"])
        
        # Store Summary
        database.store_vote_summary(vote["vote_id"], result["summary"], result["chunk_count"], engine)
        # Store categories
        for name, data in result["categories"].items():
            database.store_category(vote["vote_id"], name, data["direction"], data["flagged"], engine)

        # Store flags
        for name, data in result["flags"].items():
            database.store_vote_flag(vote["vote_id"], name, data["severity"], data["explanation"], engine)
            
    # Print progress
    print(f"votes categorized: {len(votes)}")

def initial_load(congress_api_key, congress):
    """
    Runs the full data pipeline: loads members, votes, and categorizes votes.

    Args:
        congress_api_key (str): Congress API authentication key.
        congress (int): Congress number (e.g. 118).

    Returns:
        None
    """
    engine = database.get_engine()
    load_members(congress_api_key, congress, engine)
    load_votes(congress_api_key, congress, engine)

if __name__ == "__main__":
    congress = 119
    initial_load(congress_api_key, congress)