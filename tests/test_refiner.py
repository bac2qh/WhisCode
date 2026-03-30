import http.client
import json
from unittest.mock import MagicMock, patch

from whiscode.refiner import _strip_think_tags, refine


class TestStripThinkTags:
    def test_no_think_tags(self):
        assert _strip_think_tags("Hello world") == "Hello world"

    def test_strips_think_block(self):
        text = "<think>some reasoning</think>Polished text."
        assert _strip_think_tags(text) == "Polished text."

    def test_strips_multiline_think_block(self):
        text = "<think>\nstep 1\nstep 2\n</think>Final answer."
        assert _strip_think_tags(text) == "Final answer."

    def test_no_content_after_think(self):
        text = "<think>reasoning only</think>"
        assert _strip_think_tags(text) == ""

    def test_think_with_surrounding_text(self):
        text = "Before.<think>internal</think>After."
        assert _strip_think_tags(text) == "Before.After."


class TestRefine:
    def _make_response(self, content: str, status: int = 200):
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.read.return_value = json.dumps({
            "message": {"content": content}
        }).encode()
        return mock_response

    def test_successful_refinement(self):
        mock_response = self._make_response("This is polished text.")
        with patch("http.client.HTTPConnection") as mock_conn_cls:
            mock_conn = MagicMock()
            mock_conn_cls.return_value = mock_conn
            mock_conn.getresponse.return_value = mock_response

            result = refine("uh so like this is some raw text you know")
            assert result == "This is polished text."

    def test_connection_refused_returns_original(self):
        with patch("http.client.HTTPConnection") as mock_conn_cls:
            mock_conn = MagicMock()
            mock_conn_cls.return_value = mock_conn
            mock_conn.request.side_effect = ConnectionRefusedError()

            original = "raw dictated text"
            result = refine(original)
            assert result == original

    def test_http_error_returns_original(self):
        mock_response = self._make_response("", status=500)
        with patch("http.client.HTTPConnection") as mock_conn_cls:
            mock_conn = MagicMock()
            mock_conn_cls.return_value = mock_conn
            mock_conn.getresponse.return_value = mock_response

            original = "raw dictated text"
            result = refine(original)
            assert result == original

    def test_empty_input_passthrough(self):
        result = refine("")
        assert result == ""

    def test_whitespace_only_passthrough(self):
        result = refine("   ")
        assert result == "   "

    def test_strips_think_tags_from_response(self):
        mock_response = self._make_response("<think>reasoning</think>Clean output.")
        with patch("http.client.HTTPConnection") as mock_conn_cls:
            mock_conn = MagicMock()
            mock_conn_cls.return_value = mock_conn
            mock_conn.getresponse.return_value = mock_response

            result = refine("some input text")
            assert result == "Clean output."

    def test_general_exception_returns_original(self):
        with patch("http.client.HTTPConnection") as mock_conn_cls:
            mock_conn_cls.side_effect = OSError("Network error")

            original = "raw dictated text"
            result = refine(original)
            assert result == original
