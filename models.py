from sqlalchemy import Column, String, Integer, Date, Text, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Vote(Base):
    """
    Represents a single House roll call vote in the votes table.

    Attributes:
        vote_id (int): Primary key, auto-assigned by the database.
        congress (int): Congress number (e.g. 118).
        session (int): Legislative session number.
        roll_call_number (int): Roll call number for this vote.
        legislation_number (str): Bill identifier (e.g. 'HR 1234').
        legislation_type (str): Type of legislation (e.g. 'HR', 'S').
        result (str): Outcome of the vote (e.g. 'Passed', 'Failed').
        date (Date): Date the vote was held.
        description (str): LLM-generated summary, populated after bill text is fetched.
    """

    __tablename__ = "votes"
    vote_id = Column(Integer, primary_key=True, autoincrement=True)
    congress = Column(Integer, nullable=False)
    session = Column(Integer, nullable=False)
    roll_call_number = Column(Integer)
    legislation_number = Column(String)
    legislation_type = Column(String, nullable=False)
    result = Column(String, nullable=False)
    date = Column(Date)
    chunk_count = Column(Integer)
    summary = Column(Text)


class Member(Base):
    """
    Represents a single member of congress in the members table.

    Attributes:
        member_id (int): Primary key, auto-assigned by database
        name (str): name of the representative
        state (str): state that the representative represents
        district (int): the district the representative represents
        chamber (str): specifies if the representative is in the house or senate
        picture_url (text): provides an image of the representative
        committees (text): all the committees the represenative sits on
        authored_leg (text): lists all the bills the representative has written
        co_authored_leg (text): lists all bills representative has coauthored

    """

    __tablename__ = "members"
    member_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    district = Column(Integer)
    party = Column(String)
    chamber = Column(String, nullable=False)
    picture_url = Column(Text)
    photo_cred = Column(Text)
    committees = Column(Text)
    authored_leg = Column(Text)
    co_authored_leg = Column(Text)


class MemberVote(Base):
    """
    Represents a single member vote in the member votes table

    Attributes:
        member_id: Taken from the members table
        categories: Is any combination of the 11 categories the legislation falls under
        position: the way the represenative voted on that particular legislation (i.e. yea, nay, abstains)
    """

    __tablename__ = "member_votes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.member_id"), nullable=False)  
    vote_id = Column(Integer, ForeignKey("votes.vote_id"), nullable=False)
    position = Column(String)


class Category(Base):
    """
    Represents a single category for a single vote.

    Attributes:
        vote_id: taken from votes table
        category: single category for that particular vote
        direction: which way the bill goes (False=left, True=right)
        flagged: if the category is problematic
    """

    __tablename__ = "vote_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vote_id = Column(Integer, ForeignKey("votes.vote_id"), nullable=False)
    category = Column(Text)
    direction = Column(Boolean)
    flagged = Column(Boolean)

class VoteFlag(Base):
    """
    Represents a single flag for a particular vote.

    Attributes:
        vote_id: taken from votes table
        flag_name: describes what is being flagged
        severity: red / caution / informational
        explanation: 1-2 sentences saying why it was flagged
    """

    __tablename__ = "vote_flags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vote_id = Column(Integer, ForeignKey("votes.vote_id"), nullable=False)
    flag_name = Column(Text)
    severity = Column(Text)
    explanation = Column(Text)

class SponsoredLegislation(Base):
    """
    Represents a single instance of a representative sponsoring a bill

    Attributes:
        member_id (str): Taken from the members table
        legislation_number (str): Bill identifier (e.g. 'HR 1234').
        legislation_type (str): Type of legislation (e.g. 'HR', 'S').
        policy_area (str): Policy area of the legislation (e.g. 'Environmental Protection'). May be None.
    """

    __tablename__ = "sponsored_legislation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String, ForeignKey("members.member_id"), nullable=False)
    legislation_number = Column(String, nullable=False)
    legislation_type = Column(Text, nullable=False)
    policy_area = Column(Text)


class CosponsoredLegislation(Base):
    """
    Represents a single instance of a representative cosponsoring a bill

    Attributes:
        member_id (str): Taken from the members table
        legislation_number (str): Bill identifier (e.g. 'HR 1234').
        legislation_type (str): Type of legislation (e.g. 'HR', 'S').
        policy_area (str): Policy area of the legislation (e.g. 'Environmental Protection'). May be None.
    """

    __tablename__ = "cosponsored_legislation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String, ForeignKey("members.member_id"), nullable=False)
    legislation_number = Column(String, nullable=False)
    legislation_type = Column(Text, nullable=False)
    policy_area = Column(Text)
