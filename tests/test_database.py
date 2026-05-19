import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Vote
from database import store_vote

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
            "date": "2024-01-15",
        }
        store_vote(metadata)
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
            "date": "2025-03-13",
            "extra_three": "extra",
        }
        store_vote(metadata)
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
            "date": "2024-01-15",
        }

        with self.assertRaises(Exception):
            store_vote(metadata)