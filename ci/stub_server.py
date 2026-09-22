import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765

PLAN = {
    "status": "ready",
    "plan": {
        "project_name": "stub demo",
        "summary": "A command-line tool.",
        "stack": ["Python 3.11", "argparse"],
        "label": {"language": "python", "kind": "cli"},
        "phases": [{"name": "Core", "steps": ["do the thing"]}],
        "manual_checklist": [],
    },
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if "response_format" not in body:
            self.send_error(400, "request carried no response_format")
            return
        payload = json.dumps(
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": json.dumps(PLAN)},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
