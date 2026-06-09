import unittest
from unittest.mock import MagicMock, patch
import requests

from congress_api import get_all_votes, fetch_member_positions, fetch_bill_url, fetch_bill_text, get_all_members, get_sponsored_leg, get_cosponsored_leg

from datetime import date

class TestGetAllVotes(unittest.TestCase):

    @patch("congress_api.requests.get")
    def test_returns_correct_votes(self, mock_get):
        """
        Tests get_all_votes() returns a list of dicts containing only votes
        with legislation types in LEGISLATION_TYPES, with correct field mapping.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create an instance of mock HTTP call and set value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "houseRollCallVotes": [
                {
                    "congress": 119,
                    "sessionNumber": 2,
                    "rollCallNumber": 78,
                    "legislationNumber": "4758",
                    "legislationType": "HR",
                    "result": "Passed",
                    "startDate": "2026-02-25T10:40:00-05:00",
                },
                {
                    "congress": 119,
                    "sessionNumber": 2,
                    "rollCallNumber": 79,
                    "legislationNumber": "1234",
                    "legislationType": "HCONRES",  # not in LEGISLATION_TYPES
                    "result": "Failed",
                    "startDate": "2026-02-25T11:00:00-05:00",
                },
            ],
            "pagination": {"next": None},
        }

        # Set the get call
        mock_get.return_value = mock_response

        # Make the call
        result = get_all_votes("test_key", 119)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["congress"], 119)
        self.assertEqual(result[0]["session"], 2)
        self.assertEqual(result[0]["roll_call_number"], 78)
        self.assertEqual(result[0]["legislation_number"], "4758")
        self.assertEqual(result[0]["legislation_type"], "hr")
        self.assertEqual(result[0]["result"], "Passed")
        self.assertEqual(result[0]["date"], date(2026, 2, 25))

    @patch("congress_api.requests.get")
    def test_paginates_correctly(self, mock_get):
        """
        Tests get_all_votes() follows pagination and collects votes across
        multiple pages.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create mock responses for two pages
        mock_page_1 = MagicMock()
        mock_page_1.status_code = 200
        mock_page_1.json.return_value = {
            "houseRollCallVotes": [
                {
                    "congress": 119,
                    "sessionNumber": 1,
                    "rollCallNumber": 1,
                    "legislationNumber": "100",
                    "legislationType": "HR",
                    "result": "Passed",
                    "startDate": "2025-01-10T10:00:00-05:00",
                }
            ],
            "pagination": {"next": "https://api.congress.gov/v3/house-vote/119?offset=20"},
        }

        mock_page_2 = MagicMock()
        mock_page_2.status_code = 200
        mock_page_2.json.return_value = {
            "houseRollCallVotes": [
                {
                    "congress": 119,
                    "sessionNumber": 1,
                    "rollCallNumber": 2,
                    "legislationNumber": "200",
                    "legislationType": "S",
                    "result": "Failed",
                    "startDate": "2025-01-11T10:00:00-05:00",
                }
            ],
            "pagination": {"next": None},
        }

        # Set the get call
        mock_get.side_effect = [mock_page_1, mock_page_2]

        # Make the call
        result = get_all_votes("test_key", 119)

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(result[0]["roll_call_number"], 1)
        self.assertEqual(result[1]["roll_call_number"], 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_one_429_then_200(self, mock_get, mock_backoff):
        """
        Tests get_all_votes() retries once on a 429 and succeeds on the
        subsequent 200.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
            mock_backoff: Patched exponential_backoff injected by @patch decorator.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create mock call with 200 response
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "houseRollCallVotes": [
                {
                    "congress": 119,
                    "sessionNumber": 1,
                    "rollCallNumber": 1,
                    "legislationNumber": "100",
                    "legislationType": "HR",
                    "result": "Passed",
                    "startDate": "2025-01-10T10:00:00-05:00",
                }
            ],
            "pagination": {"next": None},
        }

        # Set the get call
        mock_get.side_effect = [mock_429, mock_200]

        # Make the call
        result = get_all_votes("test_key", 119)

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(mock_get.call_count, 2)

    @patch("congress_api.exponential_backoff")
    @patch("congress_api.requests.get")
    def test_429_exhaustion(self, mock_get, mock_backoff):
        """
        Tests get_all_votes() raises RetryError after 5 consecutive 429 responses.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
            mock_backoff: Patched exponential_backoff injected by @patch decorator.
        """

        # Create mock call with 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Set the get call
        mock_get.return_value = mock_429

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            get_all_votes("test_key", 119)
        self.assertEqual(mock_get.call_count, 5)

    @patch("congress_api.requests.get")
    def test_non_429_http_error(self, mock_get):
        """
        Tests get_all_votes() raises HTTPError immediately on a non-429 HTTP error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create mock call with 403 response
        mock_403 = MagicMock()
        mock_403.status_code = 403
        mock_403.raise_for_status.side_effect = requests.exceptions.HTTPError

        # Set the get call
        mock_get.return_value = mock_403

        # Assertions
        with self.assertRaises(requests.exceptions.HTTPError):
            get_all_votes("test_key", 119)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_connection_error(self, mock_get):
        """
        Tests get_all_votes() raises RequestException immediately on a network error.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Set the get call
        mock_get.side_effect = requests.exceptions.ConnectionError

        # Assertions
        with self.assertRaises(requests.exceptions.RequestException):
            get_all_votes("test_key", 119)
        self.assertEqual(mock_get.call_count, 1)

    @patch("congress_api.requests.get")
    def test_filters_out_irrelevant_legislation_types(self, mock_get):
        """
        Tests get_all_votes() returns an empty list when all votes have
        legislation types not in LEGISLATION_TYPES.

        Args:
            mock_get: Patched requests.get injected by @patch decorator.
        """

        # Create mock response with only irrelevant legislation types
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "houseRollCallVotes": [
                {
                    "congress": 119,
                    "sessionNumber": 1,
                    "rollCallNumber": 5,
                    "legislationNumber": "10",
                    "legislationType": "HCONRES",
                    "result": "Passed",
                    "startDate": "2025-01-10T10:00:00-05:00",
                }
            ],
            "pagination": {"next": None},
        }

        # Set the get call
        mock_get.return_value = mock_response

        # Make the call
        result = get_all_votes("test_key", 119)

        # Assertions
        self.assertEqual(result, [])


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
                    {"bioguideID": "W0001456", "voteCast": "Aye"},
                    {"bioguideID": "B0000757", "voteCast": "No"},
                    {"bioguideID": "P0051484", "voteCast": "Aye"},
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
        self.assertIn(result[1]["position"], {"Aye", "No"})

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
            "houseRollCallVoteMemberVotes": {"results": 
                [
                    {"bioguideID": "W0001456", "voteCast": "Aye"},
                    {"bioguideID": "B0000757", "voteCast": "No"},
                    {"bioguideID": "P0051484", "voteCast": "Aye"},
                ]
            }
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