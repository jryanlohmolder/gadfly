import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Vote, Category, VoteFlag
from database import store_category, store_vote_flag, store_vote_summary
 
 
def make_vote(engine):
    """Helper: inserts a minimal valid Vote row and returns its vote_id."""
    metadata = {
        "congress": 118,
        "session": 1,
        "roll_call_number": 42,
        "legislation_number": "HR 1234",
        "legislation_type": "HR",
        "result": "Passed",
        "date": date(2024, 1, 15),
    }
    with Session(engine) as session:
        vote = Vote(**{k: v for k, v in metadata.items()})
        session.add(vote)
        session.commit()
        return vote.vote_id
 
 
class TestStoreCategory(unittest.TestCase):
 
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.vote_id = make_vote(self.engine)
 
    def tearDown(self):
        with Session(self.engine) as session:
            session.close()
 
    def test_store_category_inserts_row(self):
        """Verifies store_category() inserts a single row into vote_categories with correct values."""
        store_category(
            vote_id=self.vote_id,
            category="Healthcare",
            direction=True,
            flagged=False,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(Category).first()
        self.assertEqual(result.vote_id, self.vote_id)
        self.assertEqual(result.category, "Healthcare")
        self.assertEqual(result.direction, True)
        self.assertEqual(result.flagged, False)
 
    def test_store_category_flagged_true(self):
        """Verifies store_category() correctly stores flagged=True for a flagged category."""
        store_category(
            vote_id=self.vote_id,
            category="Corruption & Government Accountability",
            direction=False,
            flagged=True,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(Category).first()
        self.assertTrue(result.flagged)
 
    def test_store_category_multiple_rows(self):
        """Verifies store_category() can insert multiple categories for the same vote_id."""
        categories = [
            ("Healthcare", True, False),
            ("Economy & Cost of Living", False, False),
            ("Individual Rights & Civil Liberties", False, True),
        ]
        for category, direction, flagged in categories:
            store_category(
                vote_id=self.vote_id,
                category=category,
                direction=direction,
                flagged=flagged,
                engine=self.engine,
            )
        with Session(self.engine) as session:
            results = session.query(Category).all()
        self.assertEqual(len(results), 3)
 
    def test_store_category_correct_vote_id(self):
        """Verifies store_category() associates the category with the correct vote_id."""
        store_category(
            vote_id=self.vote_id,
            category="Environment & Energy",
            direction=True,
            flagged=False,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(Category).first()
        self.assertEqual(result.vote_id, self.vote_id)
 
 
class TestStoreVoteFlag(unittest.TestCase):
 
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.vote_id = make_vote(self.engine)
 
    def tearDown(self):
        with Session(self.engine) as session:
            session.close()
 
    def test_store_vote_flag_inserts_row(self):
        """Verifies store_vote_flag() inserts a single row into vote_flags with correct values."""
        store_vote_flag(
            vote_id=self.vote_id,
            flag_name="misleading_title",
            severity="red",
            explanation="The title says 'Protect Children Act' but the body restricts voting access.",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(VoteFlag).first()
        self.assertEqual(result.vote_id, self.vote_id)
        self.assertEqual(result.flag_name, "misleading_title")
        self.assertEqual(result.severity, "red")
        self.assertIn("title", result.explanation)
 
    def test_store_vote_flag_all_severities(self):
        """Verifies store_vote_flag() correctly stores each severity tier: red, caution, informational."""
        flags = [
            ("misleading_title", "red", "Title does not match content."),
            ("riders", "caution", "Unrelated provision attached to bill."),
            ("sunset_clauses", "informational", "Provision expires in 2 years without notice."),
        ]
        for flag_name, severity, explanation in flags:
            store_vote_flag(
                vote_id=self.vote_id,
                flag_name=flag_name,
                severity=severity,
                explanation=explanation,
                engine=self.engine,
            )
        with Session(self.engine) as session:
            results = session.query(VoteFlag).all()
        severities = [r.severity for r in results]
        self.assertIn("red", severities)
        self.assertIn("caution", severities)
        self.assertIn("informational", severities)
 
    def test_store_vote_flag_multiple_flags_same_vote(self):
        """Verifies store_vote_flag() can insert multiple flags for the same vote_id."""
        for i in range(3):
            store_vote_flag(
                vote_id=self.vote_id,
                flag_name=f"flag_{i}",
                severity="red",
                explanation=f"Explanation {i}",
                engine=self.engine,
            )
        with Session(self.engine) as session:
            results = session.query(VoteFlag).all()
        self.assertEqual(len(results), 3)
 
    def test_store_vote_flag_null_explanation(self):
        """Verifies store_vote_flag() accepts a null explanation without error."""
        store_vote_flag(
            vote_id=self.vote_id,
            flag_name="sunset_clauses",
            severity="informational",
            explanation=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(VoteFlag).first()
        self.assertIsNone(result.explanation)
 
 
class TestStoreVoteSummary(unittest.TestCase):
 
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.vote_id = make_vote(self.engine)
 
    def tearDown(self):
        with Session(self.engine) as session:
            session.close()
 
    def test_store_vote_summary_updates_row(self):
        """Verifies store_vote_summary() updates summary and chunk_count on an existing vote row."""
        store_vote_summary(
            vote_id=self.vote_id,
            summary="This bill expands healthcare access for low-income families.",
            chunk_count=3,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Vote, self.vote_id)
        self.assertEqual(result.summary, "This bill expands healthcare access for low-income families.")
        self.assertEqual(result.chunk_count, 3)
 
    def test_store_vote_summary_does_not_create_new_row(self):
        """Verifies store_vote_summary() updates in place and does not insert a new row."""
        store_vote_summary(
            vote_id=self.vote_id,
            summary="Summary text.",
            chunk_count=2,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            count = session.query(Vote).count()
        self.assertEqual(count, 1)
 
    def test_store_vote_summary_overwrites_existing(self):
        """Verifies store_vote_summary() overwrites a previously stored summary."""
        store_vote_summary(
            vote_id=self.vote_id,
            summary="First summary.",
            chunk_count=1,
            engine=self.engine,
        )
        store_vote_summary(
            vote_id=self.vote_id,
            summary="Updated summary.",
            chunk_count=2,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Vote, self.vote_id)
        self.assertEqual(result.summary, "Updated summary.")
        self.assertEqual(result.chunk_count, 2)
 
    def test_store_vote_summary_other_fields_unchanged(self):
        """Verifies store_vote_summary() does not modify other fields on the vote row."""
        store_vote_summary(
            vote_id=self.vote_id,
            summary="Summary.",
            chunk_count=1,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Vote, self.vote_id)
        self.assertEqual(result.congress, 118)
        self.assertEqual(result.legislation_type, "HR")
        self.assertEqual(result.result, "Passed")
 
 
if __name__ == "__main__":
    unittest.main()
