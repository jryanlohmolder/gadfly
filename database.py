from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Vote, MemberVote, Category, VoteFlag, Member, Base


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


def get_engine():
    """
    Creates and returns a SQLAlchemy engine connected to the local SQLite database.
    Creates all tables defined in models.py if they do not already exist.
 
    Returns:
        sqlalchemy.engine.Engine: Connected engine for congress_voting_data.db
 
    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the engine cannot be created.
    """
    engine = create_engine("sqlite:///congress_voting_data.db")
    Base.metadata.create_all(engine)
    return engine

def store_vote(metadata, engine=None):
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

    if engine is None:
        engine = get_engine()
    filtered = {k: v for k, v in metadata.items() if k in VOTE_FIELDS}
    with Session(engine) as session:
        new_vote = Vote(**filtered)
        session.add(new_vote)
        session.commit()

def store_member_vote(member_id, vote_id, position, engine=None):
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

    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        new_member_vote = MemberVote(member_id=member_id, vote_id=vote_id, position=position)
        session.add(new_member_vote)
        session.commit()

def store_category(vote_id, category, direction, flagged, engine=None):
    """
    Inserts a category for a vote and records it in the vote_categories table.

    Args:
        vote_id (int): Primary key from the vote table
        category (str): One of the pre-defined 11 categories captured in a particular piece of legislation
        direction (Boolean): Which direction the legislation in regards to the category
        flagged (Boolean): If true category has been flagged for internal contradiction

    Returns:
        None

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert or commit fails.
    """
    
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        new_category = Category(vote_id=vote_id, category=category, direction=direction, flagged=flagged)
        session.add(new_category)
        session.commit()

def store_vote_flag(vote_id, flag_name, severity, explanation, engine=None):
    """
    Inserts a category for a vote and records it in the vote_flags table.

    Args:
        vote_id (int): Primary key from the vote table
        flag_name (text): Type of flag that was captured for a particular piece of legislation
        severity (text): How serious is the flag (red, caution, informatory)
        explanation (text): 1-2 setences explaining why the legislation was flagged

    Returns:
        None

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert or commit fails.
    """

    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        new_vote_flag = VoteFlag(vote_id=vote_id, flag_name=flag_name, severity=severity, explanation=explanation)
        session.add(new_vote_flag)
        session.commit()

def store_vote_summary(vote_id, summary, chunk_count, engine=None):
    """
    Updates the summary and chunk_count for an existing vote record.
    
    Args:
        vote_id (int): Primary key from the vote table
        summary (str): LLM-generated plain language summary of the bill
        chunk_count (int): Number of chunks the bill text was split into
    
    Returns:
        None
    
    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update or commit fails.
    """
    
    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        vote = session.get(Vote, vote_id)
        vote.summary = summary
        vote.chunk_count = chunk_count
        session.commit()

def store_member(member_id, name, state, district, party, chamber, picture_url, photo_cred, committees, authored_leg, co_authored_leg, engine=None):
    """
    Inserts a member of congress into the members table.

    Args:
        member_id (str): Primary key from the member table. The BioguideID taken form congress api
        name (text): Name of congressional representative: Last, First Middle Initial
        state (text): State that representative represents
        district (int): District the representative represents (null for all senators)
        party (text): Political Party the representative is registered as
        chamber (text): House of Representatives or Senate
        picture_url (str): url link to an image of the representative
        photo_cred (text): Who the image is acreditted to
        committees (text): A list of all committees the representative sits on
        authored_leg (text): Legislation the member authored
        co_authored_leg (text): Legislation the member co-authored

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert or commit fails.
    """

    if engine is None:
        engine = get_engine()
    with Session(engine) as session:
        new_member = Member(member_id=member_id, name=name, state=state, district=district, party=party, chamber=chamber, picture_url=picture_url, photo_cred=photo_cred, committees=committees, authored_leg=authored_leg, co_authored_leg=co_authored_leg)
        session.add(new_member)
        session.commit()
        