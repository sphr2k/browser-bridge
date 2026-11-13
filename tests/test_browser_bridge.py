"""Dependency-free unit and socket tests."""
from pathlib import Path
import json
import runpy
import socket
import threading
import tempfile
import unittest
from unittest.mock import patch

bridge = runpy.run_path(str(Path(__file__).resolve().parents[1] / "bin" / "browser-bridge"))


class ValidationTests(unittest.TestCase):
    def test_supported_urls_and_paths(self):
        valid = [
            ("open", "https://github.com/login/device"),
            ("open", "http://127.0.0.1:3333/callback?state=abc"),
            ("open", "/Users/somebody/project"),
            ("open", "file:///Users/somebody/My%20Project"),
            ("reveal", "/Users/somebody/file.txt"),
        ]
        for action, target in valid:
            with self.subTest(action=action, target=target):
                self.assertTrue(bridge["valid_target"](action, target))

    def test_rejected_requests(self):
        invalid = [
            ("open", "javascript:alert(1)"),
            ("open", "https://"),
            ("open", "https://foo:99999"),
            ("open", "https://a.com\nx"),
            ("open", "https://a.com/a b"),
            ("open", "file://remote-host/private"),
            ("open", "file:///Users/somebody/%0Acommand"),
            ("open", "ssh://host"),
            ("reveal", "https://github.com"),
            ("exec", "/usr/bin/id"),
            ("open", "a" * 8193),
        ]
        for action, target in invalid:
            with self.subTest(action=action, target=target):
                self.assertFalse(bridge["valid_target"](action, target))

    def test_relative_path_normalization(self):
        self.assertEqual(bridge["normalize_target"]("."), str(Path.cwd()))
        self.assertEqual(bridge["normalize_target"]("https://example.org"), "https://example.org")
        self.assertEqual(bridge["path_from_target"]("file:///Users/a/hello%20world"), "/Users/a/hello world")

    def test_no_client_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.sock"
            self.assertEqual(bridge["send_request"]("open", "https://example.org", missing), 1)

    def test_invalid_client_target(self):
        self.assertEqual(bridge["send_request"]("open", "javascript:alert(1)"), 2)


class SocketTests(unittest.TestCase):
    def invoke_host(self, message):
        conn, server = socket.socketpair()
        with patch("subprocess.run") as run:
            thread = threading.Thread(target=bridge["handle_connection"], args=(server,))
            thread.start()
            with conn:
                conn.settimeout(5)
                conn.sendall((json.dumps(message) + "\n").encode("utf-8"))
                with conn.makefile("rb") as stream:
                    response = stream.readline()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            return response, run

    def test_url(self):
        response, run = self.invoke_host({"action": "open", "target": "https://example.org"})
        self.assertEqual(response, b"OK\n")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/open", "https://example.org"])

    def test_finder_directory(self):
        response, run = self.invoke_host({"action": "open", "target": "/Users/person/project"})
        self.assertEqual(response, b"OK\n")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/open", "/Users/person/project"])

    def test_finder_reveal(self):
        response, run = self.invoke_host({"action": "reveal", "target": "file:///Users/person/a%20b.txt"})
        self.assertEqual(response, b"OK\n")
        self.assertEqual(run.call_args.args[0], ["/usr/bin/open", "-R", "/Users/person/a b.txt"])

    def test_invalid_action_never_executes(self):
        response, run = self.invoke_host({"action": "shell", "target": "https://example.org"})
        self.assertTrue(response.startswith(b"ERR"))
        run.assert_not_called()

    def test_bad_protocol_never_executes(self):
        response, run = self.invoke_host({"action": "reveal", "target": "https://example.org"})
        self.assertTrue(response.startswith(b"ERR"))
        run.assert_not_called()

    def test_client_server_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "bridge.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(socket_path))
                listener.listen(1)
                received = []

                def accept_once():
                    connection, _ = listener.accept()
                    with connection:
                        with connection.makefile("rb") as stream:
                            received.append(json.loads(stream.readline()))
                        connection.sendall(b"OK\n")

                thread = threading.Thread(target=accept_once)
                thread.start()
                self.assertEqual(bridge["send_request"]("open", "https://example.org", socket_path), 0)
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
            self.assertEqual(received, [{"action": "open", "target": "https://example.org"}])


if __name__ == "__main__":
    unittest.main()
