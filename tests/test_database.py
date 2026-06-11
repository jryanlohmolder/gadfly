import unittest
import tempfile

from datetime import date
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base, Vote, Member, MemberVote, Category, VoteFlag, SponsoredLegislation, CosponsoredLegislation, ZipDistrict
from database import store_vote, store_member, store_member_vote, store_category, store_vote_flag, store_vote_summary, store_sponsored_legislation, store_cosponsored_legislation, vote_exists, get_unanalyzed_votes, member_exists, load_zip_districts


# Helpers

def make_vote(engine):
    """Inserts a minimal valid Vote row and returns its vote_id."""
    with Session(engine) as session:
        vote = Vote(
            congress=118,
            session=1,
            roll_call_number=42,
            legislation_number="HR 1234",
            legislation_type="HR",
            result="Passed",
            date=date(2024, 1, 15),
        )
        session.add(vote)
        session.commit()
        session.refresh(vote)
        return vote.vote_id


def make_member(engine, member_id="A000001"):
    """Inserts a minimal valid Member row and returns its member_id."""
    with Session(engine) as session:
        member = Member(
            member_id=member_id,
            name="Smith, John",
            state="CA",
            chamber="House",
        )
        session.add(member)
        session.commit()
        return member.member_id


# Tests

class TestStoreVote(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_store_vote_inserts_row(self):
        """Verifies store_vote() inserts a single row into votes with correct values."""
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
        with Session(self.engine) as session:
            result = session.query(Vote).first()
        self.assertEqual(result.congress, 118)
        self.assertEqual(result.legislation_number, "HR 1234")
        self.assertEqual(result.result, "Passed")

    def test_store_vote_returns_id(self):
        """Verifies store_vote() returns the auto-assigned vote_id of the inserted row."""
        metadata = {
            "congress": 118,
            "session": 1,
            "roll_call_number": 42,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
        }
        vote_id = store_vote(metadata, engine=self.engine)
        self.assertIsNotNone(vote_id)
        self.assertIsInstance(vote_id, int)

    def test_store_vote_filters_extra_keys(self):
        """Verifies store_vote() ignores keys not in VOTE_FIELDS."""
        metadata = {
            "congress": 118,
            "session": 1,
            "roll_call_number": 1,
            "legislation_number": "HR 1",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
            "extra_field": "should be ignored",
        }
        store_vote(metadata, engine=self.engine)
        with Session(self.engine) as session:
            result = session.query(Vote).first()
        self.assertIsNotNone(result)

    def test_store_vote_multiple_rows(self):
        """Verifies store_vote() can insert multiple votes."""
        for i in range(3):
            store_vote({
                "congress": 118,
                "session": 1,
                "roll_call_number": i,
                "legislation_number": f"HR {i}",
                "legislation_type": "HR",
                "result": "Passed",
                "date": date(2024, 1, 15),
            }, engine=self.engine)
        with Session(self.engine) as session:
            count = session.query(Vote).count()
        self.assertEqual(count, 3)

    def test_store_vote_nullable_fields_accepted(self):
        """Verifies store_vote() succeeds when optional fields are absent."""
        store_vote({
            "congress": 118,
            "session": 1,
            "legislation_type": "HR",
            "result": "Passed",
        }, engine=self.engine)
        with Session(self.engine) as session:
            result = session.query(Vote).first()
        self.assertIsNone(result.legislation_number)


class TestStoreMember(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_store_member_inserts_row(self):
        """Verifies store_member() inserts a single row into members with correct values."""
        store_member(
            member_id="A000001",
            name="Smith, John",
            state="CA",
            district=12,
            party="Democrat",
            chamber="House",
            picture_url="https://example.com/photo.jpg",
            photo_cred=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Member, "A000001")
        self.assertEqual(result.name, "Smith, John")
        self.assertEqual(result.state, "CA")
        self.assertEqual(result.district, 12)

    def test_store_member_null_district_for_senator(self):
        """Verifies store_member() accepts null district for senators."""
        store_member(
            member_id="B000001",
            name="Jones, Mary",
            state="TX",
            district=None,
            party="Republican",
            chamber="Senate",
            picture_url=None,
            photo_cred=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Member, "B000001")
        self.assertIsNone(result.district)
        self.assertEqual(result.chamber, "Senate")

    def test_store_member_nullable_fields_accepted(self):
        """Verifies store_member() succeeds when all optional fields are None."""
        store_member(
            member_id="C000001",
            name="Lee, Alex",
            state="NY",
            district=None,
            party=None,
            chamber="House",
            picture_url=None,
            photo_cred=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.get(Member, "C000001")
        self.assertIsNotNone(result)

    def test_store_member_multiple_rows(self):
        """Verifies store_member() can insert multiple members."""
        for i in range(3):
            store_member(
                member_id=f"D00000{i}",
                name=f"Rep {i}",
                state="CA",
                district=i,
                party="Democrat",
                chamber="House",
                picture_url=None,
                photo_cred=None,
                engine=self.engine,
            )
        with Session(self.engine) as session:
            count = session.query(Member).count()
        self.assertEqual(count, 3)


class TestStoreMemberVote(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.vote_id = make_vote(self.engine)
        self.member_id = make_member(self.engine)

    def test_store_member_vote_inserts_row(self):
        """Verifies store_member_vote() inserts a single row with correct values."""
        store_member_vote(
            member_id=self.member_id,
            vote_id=self.vote_id,
            position="Yea",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(MemberVote).first()
        self.assertEqual(result.member_id, self.member_id)
        self.assertEqual(result.vote_id, self.vote_id)
        self.assertEqual(result.position, "Yea")

    def test_store_member_vote_all_positions(self):
        """Verifies store_member_vote() correctly stores Yea, Nay, and Not Voting positions."""
        for i, position in enumerate(["Yea", "Nay", "Not Voting"]):
            member_id = make_member(self.engine, member_id=f"X00000{i}")
            store_member_vote(
                member_id=member_id,
                vote_id=self.vote_id,
                position=position,
                engine=self.engine,
            )
        with Session(self.engine) as session:
            results = session.query(MemberVote).all()
        positions = [r.position for r in results]
        self.assertIn("Yea", positions)
        self.assertIn("Nay", positions)
        self.assertIn("Not Voting", positions)

    def test_store_member_vote_multiple_rows(self):
        """Verifies store_member_vote() can insert multiple member votes for the same vote."""
        for i in range(3):
            member_id = make_member(self.engine, member_id=f"Y00000{i}")
            store_member_vote(
                member_id=member_id,
                vote_id=self.vote_id,
                position="Yea",
                engine=self.engine,
            )
        with Session(self.engine) as session:
            count = session.query(MemberVote).count()
        self.assertEqual(count, 3)


class TestStoreCategory(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.vote_id = make_vote(self.engine)

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


def make_sponsored_bill(engine, member_id="A000001"):
    """Inserts a minimal valid SponsoredLegislation row and returns its id."""
    with Session(engine) as session:
        bill = SponsoredLegislation(
            member_id=member_id,
            legislation_number="508",
            legislation_type="S",
            policy_area="Environmental Protection",
        )
        session.add(bill)
        session.commit()
        return bill.id


def make_cosponsored_bill(engine, member_id="A000001"):
    """Inserts a minimal valid CosponsoredLegislation row and returns its id."""
    with Session(engine) as session:
        bill = CosponsoredLegislation(
            member_id=member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
        )
        session.add(bill)
        session.commit()
        return bill.id


class TestStoreSponsoredLegislation(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.member_id = make_member(self.engine)

    def test_inserts_row(self):
        """Verifies store_sponsored_legislation() inserts a row with correct field values."""
        store_sponsored_legislation(
            member_id=self.member_id,
            legislation_number="508",
            legislation_type="S",
            policy_area="Environmental Protection",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(SponsoredLegislation).first()
        self.assertEqual(result.member_id, self.member_id)
        self.assertEqual(result.legislation_number, "508")
        self.assertEqual(result.legislation_type, "S")
        self.assertEqual(result.policy_area, "Environmental Protection")

    def test_inserts_multiple_rows(self):
        """Verifies store_sponsored_legislation() correctly inserts multiple bills for one member."""
        store_sponsored_legislation(
            member_id=self.member_id,
            legislation_number="508",
            legislation_type="S",
            policy_area="Environmental Protection",
            engine=self.engine,
        )
        store_sponsored_legislation(
            member_id=self.member_id,
            legislation_number="4616",
            legislation_type="S",
            policy_area="Taxation",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            count = session.query(SponsoredLegislation).count()
        self.assertEqual(count, 2)

    def test_policy_area_none(self):
        """Verifies store_sponsored_legislation() stores None for policy_area when not provided."""
        store_sponsored_legislation(
            member_id=self.member_id,
            legislation_number="192",
            legislation_type="SJRES",
            policy_area=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(SponsoredLegislation).first()
        self.assertIsNone(result.policy_area)

    def test_other_fields_unchanged(self):
        """Verifies store_sponsored_legislation() does not modify member_id or legislation_type."""
        store_sponsored_legislation(
            member_id=self.member_id,
            legislation_number="508",
            legislation_type="S",
            policy_area="Environmental Protection",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(SponsoredLegislation).first()
        self.assertEqual(result.member_id, self.member_id)
        self.assertEqual(result.legislation_type, "S")


class TestStoreCosponsoredLegislation(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.member_id = make_member(self.engine)

    def test_inserts_row(self):
        """Verifies store_cosponsored_legislation() inserts a row with correct field values."""
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(CosponsoredLegislation).first()
        self.assertEqual(result.member_id, self.member_id)
        self.assertEqual(result.legislation_number, "1234")
        self.assertEqual(result.legislation_type, "HR")
        self.assertEqual(result.policy_area, "Health")

    def test_inserts_multiple_rows(self):
        """Verifies store_cosponsored_legislation() correctly inserts multiple bills for one member."""
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
            engine=self.engine,
        )
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="5678",
            legislation_type="S",
            policy_area="Taxation",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            count = session.query(CosponsoredLegislation).count()
        self.assertEqual(count, 2)

    def test_multiple_members_same_bill(self):
        """Verifies store_cosponsored_legislation() allows multiple members to cosponsor the same bill."""
        second_member_id = make_member(self.engine, member_id="B000002")
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
            engine=self.engine,
        )
        store_cosponsored_legislation(
            member_id=second_member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            count = session.query(CosponsoredLegislation).count()
        self.assertEqual(count, 2)

    def test_policy_area_none(self):
        """Verifies store_cosponsored_legislation() stores None for policy_area when not provided."""
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="192",
            legislation_type="HJRES",
            policy_area=None,
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(CosponsoredLegislation).first()
        self.assertIsNone(result.policy_area)

    def test_other_fields_unchanged(self):
        """Verifies store_cosponsored_legislation() does not modify member_id or legislation_type."""
        store_cosponsored_legislation(
            member_id=self.member_id,
            legislation_number="1234",
            legislation_type="HR",
            policy_area="Health",
            engine=self.engine,
        )
        with Session(self.engine) as session:
            result = session.query(CosponsoredLegislation).first()
        self.assertEqual(result.member_id, self.member_id)
        self.assertEqual(result.legislation_type, "HR")


class TestVoteExists(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.metadata = {
            "congress": 118,
            "session": 1,
            "roll_call_number": 412,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
        }

    def test_vote_does_not_exist(self):
        """Verifies vote_exists() returns False when no matching vote is in the table."""
        result = vote_exists(118, 1, 412, engine=self.engine)
        self.assertFalse(result)

    def test_vote_exists(self):
        """Verifies vote_exists() returns True after a matching vote is stored."""
        store_vote(self.metadata, engine=self.engine)
        result = vote_exists(118, 1, 412, engine=self.engine)
        self.assertTrue(result)

    def test_vote_exists_wrong_congress(self):
        """Verifies vote_exists() returns False when congress does not match."""
        store_vote(self.metadata, engine=self.engine)
        result = vote_exists(119, 1, 412, engine=self.engine)
        self.assertFalse(result)

    def test_vote_exists_wrong_session(self):
        """Verifies vote_exists() returns False when session does not match."""
        store_vote(self.metadata, engine=self.engine)
        result = vote_exists(118, 2, 412, engine=self.engine)
        self.assertFalse(result)

    def test_vote_exists_wrong_roll_call(self):
        """Verifies vote_exists() returns False when roll_call_number does not match."""
        store_vote(self.metadata, engine=self.engine)
        result = vote_exists(118, 1, 413, engine=self.engine)
        self.assertFalse(result)


class TestGetUnanalyzedVotes(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.metadata = {
            "congress": 118,
            "session": 1,
            "roll_call_number": 412,
            "legislation_number": "HR 1234",
            "legislation_type": "HR",
            "result": "Passed",
            "date": date(2024, 1, 15),
        }

    def test_returns_empty_when_no_votes(self):
        """Verifies get_unanalyzed_votes() returns empty list when table is empty."""
        result = get_unanalyzed_votes(engine=self.engine)
        self.assertEqual(result, [])

    def test_returns_vote_with_no_summary(self):
        """Verifies get_unanalyzed_votes() returns votes where summary is None."""
        store_vote(self.metadata, engine=self.engine)
        result = get_unanalyzed_votes(engine=self.engine)
        self.assertEqual(len(result), 1)

    def test_excludes_already_analyzed_votes(self):
        """Verifies get_unanalyzed_votes() skips votes that already have a summary."""
        vote_id = store_vote(self.metadata, engine=self.engine)
        store_vote_summary(vote_id, "A summary", 3, engine=self.engine)
        result = get_unanalyzed_votes(engine=self.engine)
        self.assertEqual(result, [])

    def test_returns_correct_keys(self):
        """Verifies each returned dict contains vote_id and bill_text."""
        store_vote(self.metadata, engine=self.engine)
        result = get_unanalyzed_votes(engine=self.engine)
        self.assertIn("vote_id", result[0])
        self.assertIn("bill_text", result[0])

    def test_mixed_analyzed_and_not(self):
        """Verifies only unanalyzed votes are returned when both exist."""
        vote_id = store_vote(self.metadata, engine=self.engine)
        store_vote_summary(vote_id, "A summary", 3, engine=self.engine)
        self.metadata["roll_call_number"] = 413
        store_vote(self.metadata, engine=self.engine)
        result = get_unanalyzed_votes(engine=self.engine)
        self.assertEqual(len(result), 1)


class TestMemberExists(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.member_kwargs = {
            "member_id": "W000779",
            "name": "Wyden, Ron",
            "state": "Oregon",
            "district": None,
            "party": "Democratic",
            "chamber": "Senate",
            "picture_url": "https://example.com/wyden.jpg",
            "photo_cred": "Senate Photo Studio",
        }

    def test_member_does_not_exist(self):
        """Verifies member_exists() returns False when no matching member is in the table."""
        result = member_exists("W000779", engine=self.engine)
        self.assertFalse(result)

    def test_member_exists(self):
        """Verifies member_exists() returns True after a matching member is stored."""
        store_member(**self.member_kwargs, engine=self.engine)
        result = member_exists("W000779", engine=self.engine)
        self.assertTrue(result)

    def test_member_exists_wrong_id(self):
        """Verifies member_exists() returns False when member_id does not match."""
        store_member(**self.member_kwargs, engine=self.engine)
        result = member_exists("P000197", engine=self.engine)
        self.assertFalse(result)


class TestLoadZipDistricts(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.tmp_dir.name) / "fake_crosswalk.txt"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_happy_path(self):
        """Verifies load_zip_districts() parses valid rows and stores zcta, state, and district correctly."""

        # Build fake crosswalk file
        self.file_path.write_text(
            "h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h\n"                
            "x|0101|x|x|x|x|x|x|36009|x|x|x|x|x|x|x|x\n"    
            "x|3610|x|x|x|x|x|x|10001|x|x|x|x|x|x|x|x\n"         
        )

        # Run loader against it
        load_zip_districts(str(self.file_path), engine=self.engine)

        with Session(self.engine) as session:
            rows = session.query(ZipDistrict).all()
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].zcta, "36009")
        self.assertEqual(rows[0].state, "01")
        self.assertEqual(rows[0].district, 1)

    def test_skips_invalid_rows(self):
        """Verifies load_zip_districts() skips rows with no ZCTA and rows with district 'ZZ'."""
        
        # Build fake file: one good row, one empty-zcta row, one ZZ row
        self.file_path.write_text(
            "h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h\n"
            "x|0101|x|x|x|x|x|x|36009|x|x|x|x|x|x|x|x\n"
            "x|0101|x|x|x|x|x|x||x|x|x|x|x|x|x|x\n"
            "x|01ZZ|x|x|x|x|x|x|36011|x|x|x|x|x|x|x|x\n"
        )
        # Run loader against it
        load_zip_districts(str(self.file_path), engine=self.engine)
        # Assert only the good row landed
        with Session(self.engine) as session:
            rows = session.query(ZipDistrict).all()
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].zcta, "36009")

    def test_idempotency(self):
        """Verifies load_zip_districts() does not double the count if there are two loads of a file"""

        # Build fake crosswalk file
        self.file_path.write_text(
            "h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h\n"                
            "x|0101|x|x|x|x|x|x|36009|x|x|x|x|x|x|x|x\n"    
            "x|3610|x|x|x|x|x|x|10001|x|x|x|x|x|x|x|x\n"         
        )


        # Run loader against
        load_zip_districts(str(self.file_path), engine=self.engine)

        # Run loader against a second time
        load_zip_districts(str(self.file_path), engine=self.engine)

        # Assert the was not a double count
        with Session(self.engine) as session:
            rows = session.query(ZipDistrict).all()

        self.assertEqual(len(rows), 2)

    def test_at_large_conversion(self):
        """Verifies district is stored correctly"""

        self.file_path.write_text(
            "h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h\n"                
            "x|0200|x|x|x|x|x|x|97009|x|x|x|x|x|x|x|x\n"             
        )


        # Run loader against
        load_zip_districts(str(self.file_path), engine=self.engine)
        # Assert only the good row landed
        with Session(self.engine) as session:
            rows = session.query(ZipDistrict).all()

        self.assertEqual(rows[0].district, 0)
        self.assertIsInstance(rows[0].district, int)

if __name__ == "__main__":
    unittest.main()
