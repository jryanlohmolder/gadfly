import json
import unittest
from unittest.mock import MagicMock, patch
import requests

from anthropic_api import parse_bill_text, merge_chunks, strip_absent

class TestParseBillText(unittest.TestCase):
    @patch("anthropic_api.Anthropic")
    def test_happy_path_single_bill(self, mock_anthropic_class):
        # Get the instance of the client that is created by Anthropic()
        mock_client = mock_anthropic_class.return_value
        
        # Mock count_tokens to return an integer so it passes the token check
        mock_client.messages.count_tokens.return_value = 100
        
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
        pass

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_single_bill(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_on_single_chunk(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_json_parse_error_on_all_chunks(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_one_rate_limit_then_200(self, mock_anthropic_class):
        pass

    @patch("anthropic_api.Anthropic")
    def test_rate_limit_exhaustion(self, mock_anthropic_class):
        pass

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
