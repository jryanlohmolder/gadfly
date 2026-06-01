import json
import unittest
from unittest.mock import MagicMock, patch
import requests

import anthropic

from anthropic_api import parse_bill_text, merge_chunks, strip_absent, CHUNK_SIZE

class TestParseBillText(unittest.TestCase):
    @patch("anthropic_api.Anthropic")
    def test_happy_path_single_bill(self, mock_anthropic_class):
        """
        Test parse_bill_text() with a single bill that fits within the token limit.
    
        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.
    
        Asserts:
            Result is a dict.
            Flags contain expected severity and present values.
            Categories contain expected direction and flagged values.
            Summary matches mocked response.
        """

        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value
        
        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 100
        mock_client.messages.count_tokens.return_value = mock_count_response
        
        # Create the mock response object structure that mimics Claude's actual SDK return layout
        mock_response = MagicMock()
        
        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block = MagicMock()
        mock_block.text = json.dumps({
            "flags": {
                "misleading_title": {
                    "severity": "red",
                    "present": True,
                    "explanation": "test explanation"
                }
            },
            "categories": {
                "Individual Rights & Civil Liberties" : {
                    "direction": "Strengthen rights / protections",
                    "flagged": False, 
                }
            },
            "summary": "test summary",
        })
        mock_response.content = [mock_block]
        
        # Attach this structured response to the .create() API call
        mock_client.messages.create.return_value = mock_response

        # Run the function
        result = parse_bill_text("text")

        # Assertions (Fixed a typo in your "flags" assertion key)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["flags"]["misleading_title"]["severity"], "red")
        self.assertEqual(result["categories"]["Individual Rights & Civil Liberties"]["flagged"], False)
        self.assertEqual(result["summary"], "test summary")

    @patch("anthropic_api.Anthropic")
    def test_happy_path_chunked_bill(self, mock_anthropic_class):
        """
        Test parse_bill_text() with a bill that exceeds the token limit and requires chunking.
    
        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.
    
        Asserts:
            Result is a dict.
            Flags from chunk 1 are present in merged result.
            Categories from both chunks are present in merged result.
            Summary matches synthesized response.
            messages.create is called once per chunk plus once for synthesis.
        """

        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value

        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 500_000
        mock_client.messages.count_tokens.return_value = mock_count_response

        # Create two mock chunk responses
        mock_chunk_1 = MagicMock()
        mock_chunk_2 = MagicMock()

        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block_1 = MagicMock()
        mock_block_1.text = json.dumps({
            "flags": {
                "misleading_title": {
                    "severity": "red",
                    "present": True,
                    "explanation": "test explanation"
                },
                "restricts_individual_rights": {"severity": "red", "present": False, "explanation": None},
                "corruption_or_reduced_oversight": {"severity": "red", "present": False, "explanation": None},
                "obfuscation_by_verbosity": {"severity": "red", "present": False, "explanation": None},
                "riders": {"severity": "caution", "present": False, "explanation": None},
                "cross_referencing_obfuscation": {"severity": "caution", "present": False, "explanation": None},
                "internal_contradiction": {"severity": "informational", "present": False, "explanation": None},
                "sunset_clauses": {"severity": "informational", "present": False, "explanation": None},
            },
            "categories": {
                "Individual Rights & Civil Liberties": {"direction": "Strengthen rights / protections", "flagged": False},
                "Economy & Cost of Living": {"direction": "Not present", "flagged": False},
                "Immigration & Border Security": {"direction": "Not present", "flagged": False},
                "Democracy & Governance": {"direction": "Not present", "flagged": False},
                "Housing & Affordability": {"direction": "Not present", "flagged": False},
                "Healthcare": {"direction": "Not present", "flagged": False},
                "Crime & Public Safety": {"direction": "Not present", "flagged": False},
                "Corruption & Government Accountability": {"direction": "Not present", "flagged": False},
                "Social Programs & Safety Net": {"direction": "Not present", "flagged": False},
                "Environment & Energy": {"direction": "Not present", "flagged": False},
                "Foreign Policy, War & National Security": {"direction": "Not present", "flagged": False},
            },
            "summary": "test summary chunk 1",
        })


        mock_block_2 = MagicMock()
        mock_block_2.text = json.dumps({
            "flags": {
                "misleading_title": {"severity": "red", "present": False, "explanation": None},
                "restricts_individual_rights": {"severity": "red", "present": False, "explanation": None},
                "corruption_or_reduced_oversight": {"severity": "red", "present": False, "explanation": None},
                "obfuscation_by_verbosity": {"severity": "red", "present": False, "explanation": None},
                "riders": {"severity": "caution", "present": False, "explanation": None},
                "cross_referencing_obfuscation": {"severity": "caution", "present": False, "explanation": None},
                "internal_contradiction": {"severity": "informational", "present": False, "explanation": None},
                "sunset_clauses": {"severity": "informational", "present": False, "explanation": None},
            },
            "categories": {
                "Individual Rights & Civil Liberties": {"direction": "Not present", "flagged": False},
                "Economy & Cost of Living": {"direction": "Not present", "flagged": False},
                "Immigration & Border Security": {"direction": "Not present", "flagged": False},
                "Democracy & Governance": {"direction": "Not present", "flagged": False},
                "Housing & Affordability": {"direction": "Not present", "flagged": False},
                "Healthcare": {"direction": "Expand access / coverage", "flagged": False},
                "Crime & Public Safety": {"direction": "Not present", "flagged": False},
                "Corruption & Government Accountability": {"direction": "Not present", "flagged": False},
                "Social Programs & Safety Net": {"direction": "Not present", "flagged": False},
                "Environment & Energy": {"direction": "Not present", "flagged": False},
                "Foreign Policy, War & National Security": {"direction": "Not present", "flagged": False},
            },
            "summary": "test summary chunk 2",
        })
        
        # Set mock chunk responses
        mock_chunk_1.content = [mock_block_1]
        mock_chunk_2.content = [mock_block_2]

        # Create mock synthesis
        mock_synthesis = MagicMock()
        mock_block_synthesis = MagicMock()
        mock_block_synthesis.text = json.dumps({
            "flags": {
                "misleading_title": {
                    "severity": "red",
                    "present": True,
                    "explanation": "test explanation"
                },
                "restricts_individual_rights": {"severity": "red", "present": False, "explanation": None},
                "corruption_or_reduced_oversight": {"severity": "red", "present": False, "explanation": None},
                "obfuscation_by_verbosity": {"severity": "red", "present": False, "explanation": None},
                "riders": {"severity": "caution", "present": False, "explanation": None},
                "cross_referencing_obfuscation": {"severity": "caution", "present": False, "explanation": None},
                "internal_contradiction": {"severity": "informational", "present": False, "explanation": None},
                "sunset_clauses": {"severity": "informational", "present": False, "explanation": None},
            },
            "categories": {
                "Individual Rights & Civil Liberties": {"direction": "Strengthen rights / protections", "flagged": False},
                "Economy & Cost of Living": {"direction": "Not present", "flagged": False},
                "Immigration & Border Security": {"direction": "Not present", "flagged": False},
                "Democracy & Governance": {"direction": "Not present", "flagged": False},
                "Housing & Affordability": {"direction": "Not present", "flagged": False},
                "Healthcare": {"direction": "Expand access / coverage", "flagged": False},
                "Crime & Public Safety": {"direction": "Not present", "flagged": False},
                "Corruption & Government Accountability": {"direction": "Not present", "flagged": False},
                "Social Programs & Safety Net": {"direction": "Not present", "flagged": False},
                "Environment & Energy": {"direction": "Not present", "flagged": False},
                "Foreign Policy, War & National Security": {"direction": "Not present", "flagged": False},
            },
            "summary": "synthesized summary",
        })

        mock_synthesis.content = [mock_block_synthesis]

        # Create Side Effect
        mock_client.messages.create.side_effect = [mock_chunk_1, mock_chunk_2, mock_synthesis]

        # Run the function
        text = "a" * (CHUNK_SIZE + 1)
        result = parse_bill_text(text)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn("misleading_title", result["flags"])
        self.assertIn("Healthcare", result["categories"])
        self.assertEqual(result["summary"], "synthesized summary")
        self.assertEqual(mock_client.messages.create.call_count, 3)

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_single_bill(self, mock_anthropic_class):
        """
        Test parse_bill_text() when Claude returns something that isn't valid JSON

        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.

        Asserts:
            JSONDecodeError is raised
        """
        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value
        
        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 100
        mock_client.messages.count_tokens.return_value = mock_count_response
        
        # Create the mock response object structure that mimics Claude's actual SDK return layout
        mock_response = MagicMock()
        
        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block = MagicMock()
        mock_block.text = "this is not valid json"

        # Set Mock response
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        # Assertions
        with self.assertRaises(json.JSONDecodeError):
            parse_bill_text("text")

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_on_single_chunk(self, mock_anthropic_class):
        """
        Test parse_bill_text() will handle one bad chunk and synthesize remaining

        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.

        Asserts:
            Result is a dict
            Summary is just a summary of the good chunk
            Category from the good chunk is present
            There are 3 API calls made
        """
        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value

        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 500_000
        mock_client.messages.count_tokens.return_value = mock_count_response

        # Create two mock chunk responses
        mock_chunk_1 = MagicMock()
        mock_chunk_2 = MagicMock()

        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block_1 = MagicMock()
        mock_block_1.text = "this is not valid json"

        mock_block_2 = MagicMock()
        mock_block_2.text = json.dumps({
            "flags": {
                "misleading_title": {"severity": "red", "present": False, "explanation": None},
                "restricts_individual_rights": {"severity": "red", "present": False, "explanation": None},
                "corruption_or_reduced_oversight": {"severity": "red", "present": False, "explanation": None},
                "obfuscation_by_verbosity": {"severity": "red", "present": False, "explanation": None},
                "riders": {"severity": "caution", "present": False, "explanation": None},
                "cross_referencing_obfuscation": {"severity": "caution", "present": False, "explanation": None},
                "internal_contradiction": {"severity": "informational", "present": False, "explanation": None},
                "sunset_clauses": {"severity": "informational", "present": False, "explanation": None},
            },
            "categories": {
                "Individual Rights & Civil Liberties": {"direction": "Not present", "flagged": False},
                "Economy & Cost of Living": {"direction": "Not present", "flagged": False},
                "Immigration & Border Security": {"direction": "Not present", "flagged": False},
                "Democracy & Governance": {"direction": "Not present", "flagged": False},
                "Housing & Affordability": {"direction": "Not present", "flagged": False},
                "Healthcare": {"direction": "Expand access / coverage", "flagged": False},
                "Crime & Public Safety": {"direction": "Not present", "flagged": False},
                "Corruption & Government Accountability": {"direction": "Not present", "flagged": False},
                "Social Programs & Safety Net": {"direction": "Not present", "flagged": False},
                "Environment & Energy": {"direction": "Not present", "flagged": False},
                "Foreign Policy, War & National Security": {"direction": "Not present", "flagged": False},
            },
            "summary": "test summary chunk 2",
        })
        
        # Set mock chunk responses
        mock_chunk_1.content = [mock_block_1]
        mock_chunk_2.content = [mock_block_2]

        # Create mock synthesis
        mock_synthesis = MagicMock()
        mock_block_synthesis = MagicMock()
        mock_block_synthesis.text = json.dumps({
            "flags": {
                "misleading_title": {"severity": "red", "present": False, "explanation": None},
                "restricts_individual_rights": {"severity": "red", "present": False, "explanation": None},
                "corruption_or_reduced_oversight": {"severity": "red", "present": False, "explanation": None},
                "obfuscation_by_verbosity": {"severity": "red", "present": False, "explanation": None},
                "riders": {"severity": "caution", "present": False, "explanation": None},
                "cross_referencing_obfuscation": {"severity": "caution", "present": False, "explanation": None},
                "internal_contradiction": {"severity": "informational", "present": False, "explanation": None},
                "sunset_clauses": {"severity": "informational", "present": False, "explanation": None},
            },
            "categories": {
                "Individual Rights & Civil Liberties": {"direction": "Strengthen rights / protections", "flagged": False},
                "Economy & Cost of Living": {"direction": "Not present", "flagged": False},
                "Immigration & Border Security": {"direction": "Not present", "flagged": False},
                "Democracy & Governance": {"direction": "Not present", "flagged": False},
                "Housing & Affordability": {"direction": "Not present", "flagged": False},
                "Healthcare": {"direction": "Expand access / coverage", "flagged": False},
                "Crime & Public Safety": {"direction": "Not present", "flagged": False},
                "Corruption & Government Accountability": {"direction": "Not present", "flagged": False},
                "Social Programs & Safety Net": {"direction": "Not present", "flagged": False},
                "Environment & Energy": {"direction": "Not present", "flagged": False},
                "Foreign Policy, War & National Security": {"direction": "Not present", "flagged": False},
            },
            "summary": "chunk 2 summary",
        })

        mock_synthesis.content = [mock_block_synthesis]

        # Create Side Effect
        mock_client.messages.create.side_effect = [mock_chunk_1, mock_chunk_2, mock_synthesis]

        # Run the function
        text = "a" * (CHUNK_SIZE + 1)
        result = parse_bill_text(text)

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result["summary"], "chunk 2 summary")
        self.assertIn("Expand access / coverage", result["categories"]["Healthcare"]["direction"])
        self.assertEqual(mock_client.messages.create.call_count, 3)

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_on_all_chunks(self, mock_anthropic_class):
        """
        Test parse_bill_text() will raise value error if all chunks are not valid JSON

        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.

        Asserts:
            ValueError is raised when no chunks return valid JSON
        """
        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value

        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 500_000
        mock_client.messages.count_tokens.return_value = mock_count_response

        # Create two mock chunk responses
        mock_chunk_1 = MagicMock()
        mock_chunk_2 = MagicMock()

        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block_1 = MagicMock()
        mock_block_1.text = "this is not valid json"

        mock_block_2 = MagicMock()
        mock_block_2.text = "this is not valid json"

        # Set mock chunk responses
        mock_chunk_1.content = [mock_block_1]
        mock_chunk_2.content = [mock_block_2]

        # Create side effect
        mock_client.messages.create.side_effect = [mock_chunk_1, mock_chunk_2]

        # Assertions
        text = "a" * (CHUNK_SIZE + 1)

        with self.assertRaises(ValueError):
            parse_bill_text(text)

    @patch("anthropic_api.Anthropic")
    def test_one_rate_limit_then_200(self, mock_anthropic_class):
        """
        Test parse_bill_text() will handle one RateLimitError

        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.

        Asserts:
            Result is a dict
            Summary is correct value
            Two API calls are made
        """
        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value
        
        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 100
        mock_client.messages.count_tokens.return_value = mock_count_response
        
        # Create the mock response object structure that mimics Claude's actual SDK return layout
        mock_200 = MagicMock()
        
        # Claude SDK returns content as a list of blocks, where content[0].text is the raw string
        mock_block = MagicMock()
        mock_block.text = json.dumps({
            "flags": {
                "misleading_title": {
                    "severity": "red",
                    "present": True,
                    "explanation": "test explanation"
                }
            },
            "categories": {
                "Individual Rights & Civil Liberties" : {
                    "direction": "Strengthen rights / protections",
                    "flagged": False, 
                }
            },
            "summary": "test summary",
        })
        mock_200.content = [mock_block]

        # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create Rate Limit Error
        rate_limit_error = anthropic.RateLimitError("rate limit hit", response=mock_429, body={})

        # Create Side Effect
        mock_client.messages.create.side_effect = [rate_limit_error, mock_200]

        # Run the function
        result = parse_bill_text("text")

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertEqual(result["summary"], "test summary")
        self.assertEqual(mock_client.messages.create.call_count, 2)

    @patch("anthropic_api.Anthropic")
    def test_rate_limit_exhaustion(self, mock_anthropic_class):
        """
        Test parse_bill_text() will handle RateLimitError exhaustion

        Args:
            mock_anthropic_class: Mocked Anthropic class injected by @patch decorator.

        Asserts:
            requests.exceptions.RetryError is raised
            A total of 5 API calls are made
        """
        
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value
        
        # Mock count_tokens to return an integer so it passes the token check
        mock_count_response = MagicMock()
        mock_count_response.input_tokens = 100
        mock_client.messages.count_tokens.return_value = mock_count_response

         # Create mock 429
        mock_429 = MagicMock()
        mock_429.status_code = 429

        # Create Rate Limit Error
        rate_limit_error = anthropic.RateLimitError("rate limit hit", response=mock_429, body={})

        # Set Return Value
        mock_client.messages.create.side_effect = [rate_limit_error] * 5

        # Assertions
        with self.assertRaises(requests.exceptions.RetryError):
            parse_bill_text("text")
        
        self.assertEqual(mock_client.messages.create.call_count, 5)


    @patch("anthropic_api.Anthropic")
    def test_non_rate_limit_api_error(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_empty_list(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_any_true_flag_wins(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_single_direction_across_chunks(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_interal_contradiction_across_chunks(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_all_chunks_not_present(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_false_flags_removed(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_not_present_categories_removed(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_all_flags_removed(self, mock_anthropic_lass):
        pass
