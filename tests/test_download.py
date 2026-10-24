import hashlib
import http.server
import threading

import pytest

from dropatlas.fetch import ChecksumError, download

PAYLOAD = bytes(range(256)) * 16_000  # ~4 MB, so whole 1 MB chunks land before the drop


class FlakyHandler(http.server.BaseHTTPRequestHandler):
    drops_left = 1  # the first full download dies halfway through
    ranges: list[str] = []

    def do_GET(self):
        start = 0
        if rng := self.headers.get("Range"):
            FlakyHandler.ranges.append(rng)
            start = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
        else:
            self.send_response(200)
        body = PAYLOAD[start:]
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if start == 0 and FlakyHandler.drops_left:
            FlakyHandler.drops_left -= 1
            self.wfile.write(body[: len(body) // 2])
            self.close_connection = True
            return
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    FlakyHandler.drops_left = 1
    FlakyHandler.ranges = []
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FlakyHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/file.bin"
    httpd.shutdown()


def test_download_resumes_after_dropped_connection(server, tmp_path):
    expected = hashlib.sha256(PAYLOAD).hexdigest()
    path = download(server, tmp_path / "file.bin", expected_sha256=expected, sleep=lambda s: None)
    assert path.read_bytes() == PAYLOAD
    assert not (tmp_path / "file.bin.part").exists()
    assert FlakyHandler.ranges, "the second attempt should ask only for the missing bytes"


def test_bad_checksum_is_refused(server, tmp_path):
    with pytest.raises(ChecksumError):
        download(server, tmp_path / "file.bin", expected_sha256="0" * 64, sleep=lambda s: None)
    assert not (tmp_path / "file.bin").exists()
