import unittest
from unittest.mock import MagicMock, patch
import requests

from congress_api import get_total_votes, get_vote_data, check_legislation_type, get_vote_metadata, fetch_member_positions, fetch_bill_url, fetch_bill_text, get_all_members, get_sponsored_leg, get_cosponsored_leg


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

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_total_votes() retries once on a 429 and succeeds on the subsequent 200.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If result is not a int, result is not 500, or call_count is not 2.
        """

        # Create mock call with 429 respone
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock call with 200 response
        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_200.json.return_value = {"pagination": {"count": 500}}

        # Set the get call
        mock_get.side_effect = [mock_429, mock_200]

        # Assertions
        result = get_total_votes("test_key", 119)

        self.assertIsInstance(result, int)
        self.assertEqual(result, 500)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_total_votes() raises RetryError after 5 consecutive 429 responses.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RetryError is not raised or call_count is not 5.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set the get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_total_votes("test_key", 118)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_total_votes() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock call with 403 response
        mock_403 = MagicMock()
        mock_403.status_code = 403

        # Make mock response return HTTPError
        mock_403.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set get call
        mock_get.return_value = mock_403

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_total_votes("test_key", 118)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests get_total_votes() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.RequestException):
            get_total_votes("test_key", 118)
        self.assertEqual(mock_get.call_count, 1)


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
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["congress"], int)
        self.assertIsInstance(result["session"], int)
        self.assertIsInstance(result["roll_call_number"], int)
        self.assertIsInstance(result["legislation_number"], str)
        self.assertIsInstance(result["legislation_type"], str)
        self.assertIsInstance(result["result"], str)
        self.assertIsInstance(result["date"], str)

        # Value assertions
        self.assertEqual(result["congress"], 118)
        self.assertEqual(result["session"], 1)
        self.assertEqual(result["roll_call_number"], 42)
        self.assertEqual(result["legislation_number"], "5")
        self.assertEqual(result["legislation_type"], "HR")
        self.assertEqual(result["result"], "Passed")
        self.assertEqual(result["date"], "2023-01-09")

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_vote_data() retries once on a 429 and succeeds on the subsequent 200.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If result is not a int, result is not 500, or call_count is not 2.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock call with 200 response
        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_200.json.return_value = {
            "vote": {
                "congress": 118,
                "session": 1,
                "rollCallNumber": 42,
                "result": "Passed",
                "date": "2023-01-09",
                "bill": {"number": "5", "type": "HR"}
            }
        }

        mock_get.side_effect = [mock_429, mock_200]

        # fake HTTP call
        result = get_vote_data("test_key", 118, 1, 42)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["congress"], int)
        self.assertEqual(result["congress"], 118)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_vote_data() raises RetryError after 5 consecutive 429 responses.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RetryError is not raised or call_count is not 5.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set the get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_vote_data("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_vote_data() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock response with 401 HTTP error
        mock_401 = MagicMock()
        mock_401.status_code = 401

        # Have mock respones return an HTTP Error
        mock_401.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set mock call
        mock_get.return_value = mock_401

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_vote_data("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests get_vote_data() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.RequestException):
            get_vote_data("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 1)



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
        Tests fetch_member_positions() in congress_api to ensure that a list of dicts containing
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

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests fetch_member_positions() retries once on a 429 and succeeds on the subsequent 200.

        Args:
        mock_get: Patched requests.get injected by @patch decorator.

        Returns:
        None

        Raises:
        AssertionError: If result is not a list, length is not 3, or call_count is not 2.
        """
        
        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429
        
        # Create mock call with 200 response
        mock_200 = MagicMock()
        mock_200.status_code = 200
        
        mock_200.json.return_value = {
        "houseRollCallVoteMemberVotes": {"results": [
            {"firstName": "John", "lastName": "Smith", "voteCast": "Aye"},
            {"firstName": "Jane", "lastName": "Doe", "voteCast": "No"},
            {"firstName": "King", "lastName": "Billy", "voteCast": "Aye"},
        ]}
        }
        
        # Set the get call
        mock_get.side_effect = [mock_429, mock_200]

        # Pass mock data to fetch_member_positions()
        result = fetch_member_positions("test_key", 118, 1, 42)
        
        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests fetch_member_positions() raises RetryError after 5 consecutive 429 responses.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RetryError is not raised or call_count is not 5.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set the get call
        mock_get.return_value = mock_429
        
        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            fetch_member_positions("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests fetch_member_positions() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 404 error
        mock_404 = MagicMock()
        mock_404.status_code = 404
        
        # Make mock response return HTTPError
        mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError
        
        # Set the get call
        mock_get.return_value = mock_404
        
        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            fetch_member_positions("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests fetch_member_positions() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.RequestException):
            fetch_member_positions("test_key", 118, 1, 42)
        self.assertEqual(mock_get.call_count, 1)


class TestFetchBillURL(unittest.TestCase):
    @patch("congress_api.requests.get")
    def happy_path(self, mock_get):
        """
        Tests fetch_bill_url() returns HTM URL when Formatted Text format is available.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Returns:
            None
        
        Raises:
            AssertionError: If result is not a string or does not match expected HTM URL.
        """

        # Create mock URL
        mock_response = MagicMock()        
        mock_response.json.return_value = {
            "textVersions": [
                {
                    "formats": [
                        {"type": "Formatted Text", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.htm"},
                        {"type": "PDF", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.pdf"},
                        {"type": "Formatted XML", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.xml"}
                    ]
                }
            ]
        }

        # Set get call
        mock_get.return_value = mock_response

        # Have fetch_bill_url get mock url
        result = fetch_bill_url("test_key", 118, "hr", 3076)

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.htm")

    @patch("congress_api.requests.get")
    def xml_fallback(self, mock_get):
        """
        Tests fetch_bill_url() returns XML URL when Formatted Text format is unavailable.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Returns:
            None
        
        Raises:
            AssertionError: If result is not a string or does not match expected XML URL.
        """
    
        # Create mock URL - XML
        mock_XML = MagicMock()
        mock_XML.json.return_value = {
        "textVersions": [
                {
                "formats": [
                    {"type": "PDF", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.pdf"},
                    {"type": "Formatted XML", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.xml"}
                    ]
                }
            ]
        }

        # Set get call
        mock_get.return_value = mock_XML

        # Have fetch_bill_url get mock url (XML)
        result = fetch_bill_url("test_key", 118, "hr", 3076)

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.xml")

    @patch("congress_api.requests.get")
    def no_htm_xml(self, mock_get):
        """
        Tests fetch_bill_url() returns ValueError when HTM & XML formats are unavailable.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Returns:
            None
        
        Raises:
            AssertionError: If result does not raise a ValueError.
        """
        
        # Create mock URL - no htm or xml
        mock_url = MagicMock()
        mock_url.json.return_value = {
        "textVersions": [
                {
                "formats": [
                    {"type": "PDF", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.pdf"},
                    ]
                }
            ]
        }

        # Set get call
        mock_get.return_value = mock_url

        # Raise ValueError
        with self.assertRaises(ValueError):
            fetch_bill_url("test_key", 118, "hr", 3076)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests fetch_bill_url() retries once on a 429 and succeeds on the subsequent 200.

        Args:
        mock_get: Patched requests.get injected by @patch decorator.

        Returns:
        None

        Raises:
        AssertionError: If result is not a string or does not match expected HTM URL, or call_count is not 2.
        """

        # Create mock 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock 200 response
        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_200.json.return_value = {
            "textVersions": [
                {
                    "formats": [
                        {"type": "Formatted Text", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.htm"},
                        {"type": "PDF", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.pdf"},
                        {"type": "Formatted XML", "url": "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.xml"}
                    ]
                }
            ]
        }

        # Set get call
        mock_get.side_effect = [mock_429, mock_200]

        # Have fetch_bill_url get mock url (XML)
        result = fetch_bill_url("test_key", 118, "hr", 3076)

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "https://www.congress.gov/118/bills/hr3076/BILLS-118hr3076ih.htm")
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests fetch_bill_url() retries a total of 5 times on a 429 error.

        Args:
        mock_get: Patched requests.get injected by @patch decorator.

        Returns:
        None

        Raises:
        AssertionError: If RetryError is not raised or call_count is not 5.
        """

        # Create mock 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            fetch_bill_url("test_key", 118, "hr", 3076)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests fetch_bill_url() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 403 error
        mock_403 = MagicMock()
        mock_403.status_code = 403

        mock_403.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set the get call
        mock_get.return_value = mock_403

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            fetch_bill_url("test_key", 118, "hr", 3076)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests fetch_bill_url() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.RequestException):
            fetch_bill_url("test_key", 118, "hr", 3076)
        self.assertEqual(mock_get.call_count, 1)


class TestFetchBillText(unittest.TestCase):
    @patch("congress_api.requests.get")
    def test_happy_path(self, mock_get):
        """
        Tests fetch_bill_text() returns readable text.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Returns:
            None
        
        Raises:
            AssertionError: If result is not a string.
        """

        # Create mock string
        mock_response = MagicMock()
        mock_response.text = "<html> Some bill text here </html>"

        # Set get call
        mock_get.return_value = mock_response

        # Pass mock data to fetch_bill_text()
        result = fetch_bill_text("test_url")

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "<html> Some bill text here </html>")

    @patch("congress_api.requests.get")
    def test_empty_bill(self, mock_get):
        """
        Tests fetch_bill_text() returns a ValueError if there is no text.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Returns:
            None
        
        Raises:
            AssertionError: If result is not a ValueError.
        """

        # Create an empty mock response
        empty_mock = MagicMock()
        empty_mock.text = ""

        # Set get call
        mock_get.return_value = empty_mock

        # Assertions
        with self.assertRaises(ValueError):
            fetch_bill_text("test_url")

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests fetch_bill_text() retries once on a 429 and succeeds on the subsequent 200.

        Args:
        mock_get: Patched requests.get injected by @patch decorator.

        Returns:
        None

        Raises:
        AssertionError: If result is not a string or does not match expected HTM URL, or call_count is not 2.
        """

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock 200
        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_200.text = "<html> Some bill text here </html>"

        # Set get call
        mock_get.side_effect = [mock_429, mock_200]

        # Pass mock data to fetch_bill_text()
        result = fetch_bill_text("test_url")

        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "<html> Some bill text here </html>")
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests fetch_bill_text() retries a total of 5 times on a 429 error.

        Args:
        mock_get: Patched requests.get injected by @patch decorator.

        Returns:
        None

        Raises:
        AssertionError: If RetryError is not raised or call_count is not 5.
        """

        # Create mock 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            fetch_bill_text("test_url")
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests fetch_bill_url() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 404 response
        mock_404 = MagicMock()
        mock_404.status_code = 404

        # Create 404 HTTP error for mock_404
        mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set the get call
        mock_get.return_value = mock_404

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            fetch_bill_text("test_url")
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests fetch_bill_url() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.ConnectionError):
            fetch_bill_text("test_url")
        self.assertEqual(mock_get.call_count, 1)


class TestGetAllMembers(unittest.TestCase):

    @patch("congress_api.requests.get")
    def test_happy_path_single_page(self, mock_get):
        """
        Tests get_all_members() returns a list of correctly parsed member dicts when 
        the API returns a single page with no next URL.
        
        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Raises:
            AssertionError: If result is not a list, or member fields are incorrect.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "members": [
                {
                    "bioguideId": "B001288",
                    "name": "Booker, Cory A.",
                    "state": "New Jersey",
                    "partyName": "Democratic",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/b001288_200.jpg",
                        "attribution": "Courtesy U.S. Senate"
                    },
                    "terms": {"item": [{"chamber": "Senate", "startYear": 2013}]}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.return_value = mock_response

        # Call the function
        result = get_all_members("test_key", 119)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["member_id"], "B001288")
        self.assertEqual(result[0]["name"], "Booker, Cory A.")
        self.assertEqual(result[0]["chamber"], "Senate")

    @patch("congress_api.requests.get")
    def test_happy_path_multiple_pages(self, mock_get):
        """
        Tests get_all_members() returns a list of correctly parsed member dicts when 
        the API returns a multiple pages with one having a next URL.
        
        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Raises:
            AssertionError: If result is not a list, member fields are incorrect, or two 
            calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "members": [
                {
                    "bioguideId": "B001288",
                    "name": "Booker, Cory A.",
                    "state": "New Jersey",
                    "partyName": "Democratic",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/b001288_200.jpg",
                        "attribution": "Courtesy U.S. Senate"
                    },
                    "terms": {"item": [{"chamber": "Senate", "startYear": 2013}]}
                }
            ],
            "pagination": {"count": 1, "next": "https://api.congress.gov/v3/member/congress/119?offset=20&limit=20&format=json"}
        }

        MOCK_PAGE_2 = {
            "members": [
                {
                    "bioguideId": "W000779",
                    "name": "Wyden, Ron",
                    "state": "Oregon",
                    "partyName": "Democratic",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/w000779_200.jpg",
                        "attribution": "Courtesy U.S. Senate Historical Office"
                    },
                    "terms": {"item": [{"chamber": "House of Representatives", "endYear": 1996, "startYear": 1981}, {"chamber": "Senate", "startYear": 1996}]}
                }
            ],
            "pagination": {"count": 2, "next": None}
        }

        # Create two mock responses
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = MOCK_PAGE_1

        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = MOCK_PAGE_2

        # Set get call
        mock_get.side_effect = [mock_response_1, mock_response_2]

        # Call function
        result = get_all_members("test_key", 119)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["party"], "Democratic")
        self.assertEqual(result[1]["chamber"], "Senate")
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_all_members() continues to run after one 429 error and returns correct values
        after one 200 response.
        
        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Raises:
            AssertionError: If result is not a list, if the list doesn't have one element
            and if two calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "members": [
                {
                    "bioguideId": "B001288",
                    "name": "Booker, Cory A.",
                    "state": "New Jersey",
                    "partyName": "Democratic",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/b001288_200.jpg",
                        "attribution": "Courtesy U.S. Senate"
                    },
                    "terms": {"item": [{"chamber": "Senate", "startYear": 2013}]}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock 200
        mock_200 = MagicMock()
        mock_200.status_code = 200

        mock_200.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.side_effect = [mock_429, mock_200]

        # Call function
        result = get_all_members("test_key", 119)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_all_members() gives requests.exception.RetryError if 5 429 errors received.
        
        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Raises:
            AssertionError: If a total of 5 calls aren't made.
        """
        
        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_all_members("test_url", 119)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_all_members() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 404 response
        mock_404 = MagicMock()
        mock_404.status_code = 404

        # Create 404 HTTP error for mock_404
        mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set the get call
        mock_get.return_value = mock_404

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_all_members("test_url", 119)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_network_error(self, mock_get):
        """
        Tests get_all_members() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Returns:
            None

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.ConnectionError):
            get_all_members("test_url", 119)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_member_picture_missing(self, mock_get):
        """
        Tests get_all_members() returns None for picture_url and photo_cred 
        when a member has no depiction field.
        
        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        
        Raises:
            AssertionError: If picture_url or photo_cred are not None.
        """

        # Mock Data
        MOCK_NO_DEPICTION = {
            "members": [
                {
                    "bioguideId": "A000383",
                    "name": "Armstrong, Alan",
                    "state": "Oklahoma",
                    "partyName": "Republican",
                    "terms": {"item": [{"chamber": "Senate", "startYear": 2026}]}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Set mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_NO_DEPICTION

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_all_members("test_key", 119)

        # Assertions
        self.assertEqual(result[0]["picture_url"], None)

    @patch("congress_api.requests.get")
    def test_all_terms_have_end_year(self, mock_get):
        """
        Tests get_all_members() excludes members where all terms have an endYear.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result list is not empty.
        """
        MOCK_ALL_ENDED = {
            "members": [
                {
                    "bioguideId": "M001190",
                    "name": "Mullin, Markwayne",
                    "state": "Oklahoma",
                    "partyName": "Republican",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/m001190_200.jpg",
                        "attribution": "Official U.S. Senate Photo"
                    },
                    "terms": {"item": [
                        {"chamber": "House of Representatives", "endYear": 2023, "startYear": 2013},
                        {"chamber": "Senate", "endYear": 2026, "startYear": 2023}
                    ]}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ALL_ENDED
        mock_get.return_value = mock_response

        result = get_all_members("test_key", 119)

        self.assertEqual(len(result), 0)

    @patch("congress_api.requests.get")
    def test_multiple_terms_one_without_end_year(self, mock_get):
        """
        Tests get_all_members() correctly extracts the current chamber for a member
        with multiple terms where only one lacks an endYear.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If chamber is not correctly identified as Senate.
        """
        MOCK_MULTI_TERM = {
            "members": [
                {
                    "bioguideId": "W000779",
                    "name": "Wyden, Ron",
                    "state": "Oregon",
                    "partyName": "Democratic",
                    "depiction": {
                        "imageUrl": "https://www.congress.gov/img/member/w000779_200.jpg",
                        "attribution": "Courtesy U.S. Senate Historical Office"
                    },
                    "terms": {"item": [
                        {"chamber": "House of Representatives", "endYear": 1996, "startYear": 1981},
                        {"chamber": "Senate", "startYear": 1996}
                    ]}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_MULTI_TERM
        mock_get.return_value = mock_response

        result = get_all_members("test_key", 119)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["chamber"], "Senate")


class TestGetSponsoredLeg(unittest.TestCase):

    @patch("congress_api.requests.get")
    def test_happy_path_single_page(self, mock_get):
        """
        Tests get_sponsored_leg() returns a list of correctly parsed legislation dicts when
        the API returns a single page with no next URL.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, or legislation fields are incorrect.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "sponsoredLegislation": [
                {
                    "number": "508",
                    "type": "S",
                    "policyArea": {"name": "Environmental Protection"}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.return_value = mock_response

        # Call the function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["legislation_number"], "508")
        self.assertEqual(result[0]["policy_area"], "Environmental Protection")

    @patch("congress_api.requests.get")
    def test_happy_path_multiple_pages(self, mock_get):
        """
        Tests get_sponsored_leg() returns a list of correctly parsed legislation dicts when
        the API returns multiple pages with one having a next URL.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, legislation fields are incorrect, or
            two calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "sponsoredLegislation": [
                {
                    "number": "508",
                    "type": "S",
                    "policyArea": {"name": "Environmental Protection"}
                }
            ],
            "pagination": {"count": 2, "next": "https://api.congress.gov/v3/member/W000779/sponsored-legislation?offset=20&limit=20&format=json"}
        }

        MOCK_PAGE_2 = {
            "sponsoredLegislation": [
                {
                    "number": "4616",
                    "type": "S",
                    "policyArea": {"name": "Taxation"}
                }
            ],
            "pagination": {"count": 2, "next": None}
        }

        # Create two mock responses
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = MOCK_PAGE_1

        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = MOCK_PAGE_2

        # Set get call
        mock_get.side_effect = [mock_response_1, mock_response_2]

        # Call function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["legislation_number"], "508")
        self.assertEqual(result[1]["legislation_number"], "4616")
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.requests.get")
    def test_filters_non_target_types(self, mock_get):
        """
        Tests get_sponsored_leg() excludes legislation whose type is not in LEGISLATION_TYPES,
        including amendments with null type.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result list is not empty.
        """

        # Mock data with amendment (null type) and SRES (not in LEGISLATION_TYPES)
        MOCK_FILTERED = {
            "sponsoredLegislation": [
                {
                    "amendmentNumber": "5784",
                    "type": None,
                    "policyArea": None
                },
                {
                    "number": "734",
                    "type": "SRES",
                    "policyArea": {"name": "Public Lands and Natural Resources"}
                }
            ],
            "pagination": {"count": 2, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_FILTERED

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result, [])

    @patch("congress_api.requests.get")
    def test_policy_area_missing(self, mock_get):
        """
        Tests get_sponsored_leg() returns None for policy_area when policyArea field
        is absent from the API response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If policy_area is not None.
        """

        # Mock data with no policyArea field
        MOCK_NO_POLICY_AREA = {
            "sponsoredLegislation": [
                {
                    "number": "192",
                    "type": "SJRES"
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_NO_POLICY_AREA

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result[0]["policy_area"], None)

    @patch("congress_api.requests.get")
    def test_policy_area_name_null(self, mock_get):
        """
        Tests get_sponsored_leg() returns None for policy_area when policyArea exists
        but name is null.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If policy_area is not None.
        """

        # Mock data with policyArea present but name is null
        MOCK_NULL_NAME = {
            "sponsoredLegislation": [
                {
                    "number": "4594",
                    "type": "S",
                    "policyArea": {"name": None}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_NULL_NAME

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result[0]["policy_area"], None)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_sponsored_leg() continues to run after one 429 error and returns
        correct values after one 200 response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, if the list doesn't have one element,
            or if two calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "sponsoredLegislation": [
                {
                    "number": "508",
                    "type": "S",
                    "policyArea": {"name": "Environmental Protection"}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock 200
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.side_effect = [mock_429, mock_200]

        # Call function
        result = get_sponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_sponsored_leg() raises requests.exceptions.RetryError if 5 429 errors
        are received.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If RetryError is not raised or a total of 5 calls aren't made.
        """

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_sponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_sponsored_leg() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 404 response
        mock_404 = MagicMock()
        mock_404.status_code = 404

        # Create 404 HTTP error for mock_404
        mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set get call
        mock_get.return_value = mock_404

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_sponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_network_error(self, mock_get):
        """
        Tests get_sponsored_leg() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.ConnectionError):
            get_sponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 1)


class TestGetCosponsoredLeg(unittest.TestCase):

    @patch("congress_api.requests.get")
    def test_happy_path_single_page(self, mock_get):
        """
        Tests get_cosponsored_leg() returns a list of correctly parsed legislation dicts when
        the API returns a single page with no next URL.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, or legislation fields are incorrect.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "cosponsoredLegislation": [
                {
                    "number": "1234",
                    "type": "HR",
                    "policyArea": {"name": "Health"}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.return_value = mock_response

        # Call the function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["legislation_number"], "1234")
        self.assertEqual(result[0]["policy_area"], "Health")

    @patch("congress_api.requests.get")
    def test_happy_path_multiple_pages(self, mock_get):
        """
        Tests get_cosponsored_leg() returns a list of correctly parsed legislation dicts when
        the API returns multiple pages with one having a next URL.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, legislation fields are incorrect, or
            two calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "cosponsoredLegislation": [
                {
                    "number": "1234",
                    "type": "HR",
                    "policyArea": {"name": "Health"}
                }
            ],
            "pagination": {"count": 2, "next": "https://api.congress.gov/v3/member/W000779/cosponsored-legislation?offset=20&limit=20&format=json"}
        }

        MOCK_PAGE_2 = {
            "cosponsoredLegislation": [
                {
                    "number": "5678",
                    "type": "S",
                    "policyArea": {"name": "Taxation"}
                }
            ],
            "pagination": {"count": 2, "next": None}
        }

        # Create two mock responses
        mock_response_1 = MagicMock()
        mock_response_1.json.return_value = MOCK_PAGE_1

        mock_response_2 = MagicMock()
        mock_response_2.json.return_value = MOCK_PAGE_2

        # Set get call
        mock_get.side_effect = [mock_response_1, mock_response_2]

        # Call function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["legislation_number"], "1234")
        self.assertEqual(result[1]["legislation_number"], "5678")
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.requests.get")
    def test_filters_non_target_types(self, mock_get):
        """
        Tests get_cosponsored_leg() excludes legislation whose type is not in LEGISLATION_TYPES,
        including amendments with null type.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result list is not empty.
        """

        # Mock data with amendment (null type) and SRES (not in LEGISLATION_TYPES)
        MOCK_FILTERED = {
            "cosponsoredLegislation": [
                {
                    "amendmentNumber": "5784",
                    "type": None,
                    "policyArea": None
                },
                {
                    "number": "734",
                    "type": "SRES",
                    "policyArea": {"name": "Public Lands and Natural Resources"}
                }
            ],
            "pagination": {"count": 2, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_FILTERED

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result, [])

    @patch("congress_api.requests.get")
    def test_policy_area_missing(self, mock_get):
        """
        Tests get_cosponsored_leg() returns None for policy_area when policyArea field
        is absent from the API response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If policy_area is not None.
        """

        # Mock data with no policyArea field
        MOCK_NO_POLICY_AREA = {
            "cosponsoredLegislation": [
                {
                    "number": "192",
                    "type": "HJRES"
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_NO_POLICY_AREA

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result[0]["policy_area"], None)

    @patch("congress_api.requests.get")
    def test_policy_area_name_null(self, mock_get):
        """
        Tests get_cosponsored_leg() returns None for policy_area when policyArea exists
        but name is null.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If policy_area is not None.
        """

        # Mock data with policyArea present but name is null
        MOCK_NULL_NAME = {
            "cosponsoredLegislation": [
                {
                    "number": "4594",
                    "type": "S",
                    "policyArea": {"name": None}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_NULL_NAME

        # Set get call
        mock_get.return_value = mock_response

        # Call function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertEqual(result[0]["policy_area"], None)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_cosponsored_leg() continues to run after one 429 error and returns
        correct values after one 200 response.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If result is not a list, if the list doesn't have one element,
            or if two calls aren't made.
        """

        # Mock data
        MOCK_PAGE_1 = {
            "cosponsoredLegislation": [
                {
                    "number": "1234",
                    "type": "HR",
                    "policyArea": {"name": "Health"}
                }
            ],
            "pagination": {"count": 1, "next": None}
        }

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock 200
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = MOCK_PAGE_1

        # Set get call
        mock_get.side_effect = [mock_429, mock_200]

        # Call function
        result = get_cosponsored_leg("test_key", "W000779")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_cosponsored_leg() raises requests.exceptions.RetryError if 5 429 errors
        are received.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If RetryError is not raised or a total of 5 calls aren't made.
        """

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_cosponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_cosponsored_leg() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If HTTPError is not raised or call_count is not 1.
        """

        # Create mock 404 response
        mock_404 = MagicMock()
        mock_404.status_code = 404

        # Create 404 HTTP error for mock_404
        mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set get call
        mock_get.return_value = mock_404

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_cosponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_network_error(self, mock_get):
        """
        Tests get_cosponsored_leg() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.

        Raises:
            AssertionError: If RequestException is not raised or call_count is not 1.
        """

        # Set get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.ConnectionError):
            get_cosponsored_leg("test_key", "W000779")
        self.assertEqual(mock_get.call_count, 1)