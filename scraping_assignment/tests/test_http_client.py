"""Runs HttpClient against a tiny local server (no internet needed)."""
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from scrapers.http_client import HttpClient


class Handler(BaseHTTPRequestHandler):
    hits = {}

    def do_GET(self):
        Handler.hits[self.path] = Handler.hits.get(self.path, 0) + 1
        if self.path == "/flaky" and Handler.hits[self.path] < 3:
            self.send_response(503)
        elif self.path == "/missing":
            self.send_response(404)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write("<p>\u00a351.77</p>".encode("utf-8"))

    def log_message(self, *args):
        pass


class HttpClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.hits = {}
        self.client = HttpClient(delay=0, timeout=2, max_retries=3, backoff=0.01)

    def test_success_decodes_utf8(self):
        self.assertIn("\u00a351.77", self.client.get_html(self.base + "/ok"))

    def test_retries_5xx_then_succeeds(self):
        self.assertIsNotNone(self.client.get_html(self.base + "/flaky"))
        self.assertEqual(Handler.hits["/flaky"], 3)

    def test_404_is_not_retried(self):
        self.assertIsNone(self.client.get_html(self.base + "/missing"))
        self.assertEqual(Handler.hits["/missing"], 1)

    def test_connection_refused_returns_none(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()  # nothing is listening on this port now
        self.assertIsNone(self.client.get_html(f"http://127.0.0.1:{port}/"))

    def test_get_soup_returns_none_on_failure(self):
        self.assertIsNone(self.client.get_soup(self.base + "/missing"))


if __name__ == "__main__":
    unittest.main()
