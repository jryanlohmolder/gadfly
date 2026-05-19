import unittest
from unittest.mock import MagicMock, patch
from congress_api import get_total_votes, get_vote_data, check_legislation_type, get_vote_metadata, fetch_member_positions


class TestGetTotalVotes(unittest.TestCase):
    @patch("congress_api.requests.get")
    def test_returns_correct_count(self, mock_get):
        """
        Tests get_total_votes() in congress_api.py. Verifies the function
        returns an integer greater than 0 and correctly extracts the count
        from the mocked API response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create an instance of mock HTTP call and set value
        mock_response = MagicMock()
        mock_response.json.return_value = {"pagination": {"count": 500}}

        # Set the get call
        mock_get.return_value = mock_response

        # fake HTTP call
        n = get_total_votes("test_key", 119)

        # Assertions
        assert type(n) == int
        assert n > 0
        assert n == 500


class TestGetVoteData(unittest.TestCase):
    @patch("congress_api.requests.get")
    def test_returns_flat_dict(self, mock_get):
        """
        Tests get_vote_data() in congress_api.py. Verifies the function
        returns a flat dict with correct snake_case keys, types, and values
        extracted from the mocked API response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create an instance of mock HTTP call and set value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vote": {
                "congress": 118,
                "session": 1,
                "rollCallNumber": 42,
                "result": "Passed",
                "date": "2023-01-09",
                "bill": {"number": "5", "type": "HR"}
            }
        }

        # Set the get call
        mock_get.return_value = mock_response

        # fake HTTP call
        result = get_vote_data("test_key", 118, 1, 42)

        # Type assertions
        assert type(result) == dict
        assert type(result["congress"]) == int
        assert type(result["session"]) == int
        assert type(result["roll_call_number"]) == int
        assert type(result["legislation_number"]) == str
        assert type(result["legislation_type"]) == str
        assert type(result["result"]) == str
        assert type(result["date"]) == str

        # Value assertions
        assert result["congress"] == 118
        assert result["session"] == 1
        assert result["roll_call_number"] == 42
        assert result["legislation_number"] == "5"
        assert result["legislation_type"] == "HR"
        assert result["result"] == "Passed"
        assert result["date"] == "2023-01-09"


class TestCheckLegislationType(unittest.TestCase):
    def test_valid_type(self):
        """
        Tests check_legislation_type() in congress_api. Verifies the function
        returns True when legislation_type is in LEGISLATION_TYPES
        """

        # Create fake vote
        fake_vote = {"legislation_type": "HR"}
        # Pass to check_legislation_type
        result = check_legislation_type(fake_vote)

        self.assertTrue(result)

    def test_invalid_type(self):
        """
        Tests check_legislation_type() in congress_api. Verifies the function
        returns False when legislation_type is not in LEGISLATION_TYPES
        """

        # Create fake vote
        fake_vote = {"legislation_type": "Not_valid"}
        # Pass to check_legislation_type
        result = check_legislation_type(fake_vote)

        self.assertFalse(result)

    def test_missing_type(self):
        """
        Tests check_legislation_type() in congress_api. Verifies the function
        returns False when legislation_type is not present in dict
        """

        # Create fake vote
        fake_vote = {"not_legislaiton_type": "HR"}
        # Pass to check_legislation_type
        result = check_legislation_type(fake_vote)

        self.assertFalse(result)

class TestGetVoteMetadata(unittest.TestCase):
    def test_valid_result_type(self):
        """ 
        Tests get_vote_metadata() in congress_api. Verifies the function
        returns the exact same dict when the keys match.
        """

        # Create dict from get_vote_meta_data
        meta_data = {
                "congress": 118,
                "session": 1,
                "roll_call_number": 42,
                "legislation_number": "5",
                "legislation_type": "HR",
                "result": "Passed",
                "date": "2023-01-09",
            }
        
        result = get_vote_metadata(meta_data)

        assert set(result.keys()) == {
            "congress", 
            "session", 
            "roll_call_number",
            "legislation_number",
            "legislation_type",
            "result",
            "date", 
        }

    def test_extra_result_type(self):
        """ 
        Tests get_vote_metadata() in congress_api. Verifies the function
        returns the appropriate keys and leaves out the extras.
        """
         
        meta_data = {
                "extra_one": 2,
                "congress": 118,
                "session": 1,
                "roll_call_number": 42,
                "legislation_number": "5",
                "extra_two": "extra",
                "legislation_type": "HR",
                "result": "Passed",
                "date": "2023-01-09",
                "extra_three": "extra",
            }
        
        result = get_vote_metadata(meta_data)
    
        assert set(result.keys()) == {
            "congress", 
            "session", 
            "roll_call_number",
            "legislation_number",
            "legislation_type",
            "result",
            "date", 
        }

    def test_invalid_return_type(self):
        """
        Tests get_vote_metadata() in crongress_api.py. Verifies the function
        returns a KeyError when all keys are not present.
        """

        with self.assertRaises(KeyError):
            get_vote_metadata({"congress": 118})


class TestFetchMemberPositions(unittest.TestCase):
    @patch("congress_api.requests.get")
    def test_correct_data_return(self, mock_get):
        """
        Tests get_member_votes() in congress_api to ensure that a list of dicts containing
        representatives and their votes are returned.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """
        
        # Create mock vote
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "houseRollCallVoteMemberVotes": {"results": 
                [
                    {"firstName": "John", "lastName": "Smith", "voteCast": "Aye"},
                    {"firstName": "Jane", "lastName": "Doe", "voteCast": "No"},
                    {"firstName": "King", "lastName": "Billy", "voteCast": "Aye"},
                ]
            }
        }

        # Set the get call
        mock_get.return_value = mock_response

        # Pass mock data to fetch_member_positions()
        result = fetch_member_positions("test_key", 118, 1, 42)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)
        self.assertIn(result[1]["voteCast"], {"Aye", "No"})
