import unittest

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Vote, MemberVote
from database import store_vote, store_member_vote

class TestStoreVote(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()

    def test_store_vote_inserts_row(self):
        """Verifies store_vote() inserts a valid metadata dict as a single database row."""

        metadata = {
            "congress": 118,
            "session": 1,
            "roll_call_number": 42,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
        }
        store_vote(metadata, engine=self.engine)
        result = self.session.query(Vote).first()
        self.assertEqual(result.congress, 118)
        self.assertEqual(result.result, "Passed")

    def test_store_vote_extra_data(self):
        """Verifies store_vote() ignores extra keys not corresponding to Vote columns."""
        
        metadata = {
            "extra_one": 42,
            "congress": 119,
            "session": 2,
            "extra_two": "extra",
            "roll_call_number": 24,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2025, 2, 13),
            "extra_three": "extra",
        }
        store_vote(metadata, engine=self.engine)
        with Session(self.engine) as session:
            result = session.query(Vote).first()
        self.assertFalse(hasattr(result, "extra_one"))
        self.assertFalse(hasattr(result, "extra_two"))
        self.assertFalse(hasattr(result, "extra_three"))

    def test_store_vote_missing_field(self):
        """Verifies store_vote() raises an exception when a required field is missing."""

        # congress intentionally missing
        metadata = {
            "session": 1,
            "roll_call_number": 42,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
        }

        with self.assertRaises(Exception):
            store_vote(metadata, engine=self.engine)


class TestStoreMemberVote(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()

    def test_store_member_vote(self):
        """Verifies store_member_vote inserts a valid member_id, vote_id, and vote_cast as single database row"""

        member_id = 5
        vote_id = 11
        position = "No"

        # Create member vote
        store_member_vote(member_id=member_id, vote_id=vote_id, position=position, engine=self.engine)

        # 
        with Session(self.engine) as session:
            result = session.query(MemberVote).first()

        # Assertions
        self.assertEqual(result.member_id, 5)
        self.assertEqual(result.vote_id, 11)
        self.assertEqual(result.position, "No")
