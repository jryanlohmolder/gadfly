import unittest
from unittest.mock import patch, MagicMock
from app import app

class TestHomeRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_get_home(self):
        """
        Test home route GET request renders home page.
        Asserts:
            Returns 200 status code.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    @patch("app.lookup_representative")
    def test_post_error(self, mock_lookup):
        """
        Test home route POST renders error on invalid zip.
        Asserts:
            Returns 200 and error message in response.
        """
        mock_lookup.return_value = [{"error": "Please enter a valid 5-digit zip code"}]
        response = self.client.post("/", data={"zip_code": "abcde"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter a valid 5-digit zip code", response.data)

    @patch("app.lookup_representative")
    def test_post_vacant(self, mock_lookup):
        """
        Test home route POST renders vacant message.
        Asserts:
            Returns 200 and vacant message in response.
        """
        mock_lookup.return_value = [{"vacant": True, "message": "This congressional seat is currently vacant"}]
        response = self.client.post("/", data={"zip_code": "20001"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This congressional seat is currently vacant", response.data)

    @patch("app.lookup_representative")
    def test_post_happy_path(self, mock_lookup):
        """
        Test home route POST renders results page on valid zip.
        Asserts:
            Returns 200 status code.
        """
        mock_lookup.return_value = [
            {"member_id": "N000002", "name": "Nadler, Jerrold", "party": "D", "chamber": "House of Representatives", "image": "", "attribution": ""},
            {"member_id": "S000001", "name": "Schumer, Chuck", "party": "D", "chamber": "Senate", "image": "", "attribution": ""},
            {"member_id": "G000002", "name": "Gillibrand, Kirsten", "party": "D", "chamber": "Senate", "image": "", "attribution": ""}
        ]
        response = self.client.post("/", data={"zip_code": "10001"})
        self.assertEqual(response.status_code, 200)


class TestMemberProfileRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    @patch("app.get_member_category_scores")
    @patch("app.get_engine")
    def test_member_profile(self, mock_engine, mock_scores):
        """
        Test member profile route renders with valid member_id.
        Asserts:
            Returns 200 status code.
        """
        mock_session = MagicMock()
        mock_engine.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_scores.return_value = {}
        response = self.client.get("/member/N000002")
        self.assertEqual(response.status_code, 200)