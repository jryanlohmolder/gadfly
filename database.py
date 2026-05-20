from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Vote, MemberVote


# Constants
VOTE_FIELDS = {
    "congress", 
    "session", 
    "roll_call_number",
    "legislation_number",
    "legislation_type",
    "result",
    "date",
}

# Create engine
engine = create_engine("sqlite:///votes.db")


def store_vote(metadata, engine=engine):
    """
    Inserts a single vote record into the votes table.

    Args:
        metadata (dict): A dict returned by get_vote_metadata() containing
            keys: congress, session, roll_call_number, legislation_number,
            legislation_type, result, date.

    Returns:
        None

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert or commit fails.
    """

    filtered = {k: v for k, v in metadata.items() if k in VOTE_FIELDS}
    with Session(engine) as session:
        new_vote = Vote(**filtered)
        session.add(new_vote)
        session.commit()

def store_member_vote(member_id, vote_id, position, engine=engine):
    """
    Inserts a vote for a single memember for a single vote and records it in the member_votes table.

    Args:
        member_id (int): Primary key from the member table
        vote_id (int): Primary key from the vote table
        position (str): How the member voted on that particular vote

    Returns:
        None

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert or commit fails.
    """

    with Session(engine) as session:
        new_member_vote = MemberVote(member_id=member_id, vote_id=vote_id, position=position)
        session.add(new_member_vote)
        session.commit()

