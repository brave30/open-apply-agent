import hashlib
import json
import secrets
from urllib.parse import urlsplit


def local_origin(url):
    p = urlsplit(url)
    if p.scheme != "http" or p.hostname != "127.0.0.1" or not p.port or p.username or p.password:
        raise ValueError("MVP only permits an explicit http://127.0.0.1:PORT local fixture.")
    return f"http://127.0.0.1:{p.port}"


async def snapshot(page):
    return await page.evaluate("""async () => await Promise.all([...document.querySelectorAll('input,textarea,select')]
      .map(async e=>({id:e.id,name:e.name,type:e.type,disabled:e.disabled,value:e.value,checked:e.checked,
      files:e.files?await Promise.all([...e.files].map(async f=>({name:f.name,size:f.size,
      sha256:[...new Uint8Array(await crypto.subtle.digest('SHA-256',await f.arrayBuffer()))]
      .map(b=>b.toString(16).padStart(2,'0')).join('')}))):[]})))""")


def digest(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def payload_digest(parts):
    normalized = sorted(parts, key=lambda part: json.dumps(part, sort_keys=True))
    return digest(normalized)


def reviewed_payload_digest(state):
    parts = []
    for field in state:
        if not field["name"] or field["disabled"] or (field["type"] in {"checkbox", "radio"} and not field["checked"]):
            continue
        if field["type"] == "file":
            for file in field["files"] or [{"name": "", "sha256": hashlib.sha256(b"").hexdigest()}]:
                parts.append({"name": field["name"], "filename": file["name"], "sha256": file["sha256"]})
        else:
            parts.append({"name": field["name"], "value": field["value"].replace("\r\n", "\n").replace("\r", "\n")})
    return payload_digest(parts)


class SubmissionGuard:
    """Fail closed. Approval is created only by the trusted terminal review path."""
    def __init__(self, origin, server_token):
        self.origin = local_origin(origin)
        self.server_token = server_token
        self.approved_digest = None
        self.approved_payload = None
        self.blocked = []
        self.nonce = secrets.token_hex(4)
        self.consumed = False

    async def install(self, context):
        # Request interception is not bypassed by service workers.
        await context.route("**/*", self.route)
        if hasattr(context, "route_web_socket"):
            await context.route_web_socket("**/*", lambda ws: ws.close())

    async def approve_from_terminal(self, page, reader=input):
        self.approved_digest = None
        self.approved_payload = None
        self.nonce = secrets.token_hex(4)
        state = await snapshot(page)
        print(json.dumps(state, indent=2))
        phrase = f"APPROVE LOCAL APPLICATION {self.nonce}"
        reply = reader(f"Review the exact synthetic application above. Type '{phrase}' to submit: ")
        if reply != phrase or digest(await snapshot(page)) != digest(state):
            return False
        self.approved_digest = digest(state)
        self.approved_payload = reviewed_payload_digest(state)
        self.consumed = False
        return True

    async def route(self, route):
        req = route.request
        p = urlsplit(req.url)
        same = f"{p.scheme}://{p.netloc}" == self.origin
        allowed = same and req.method == "GET" and p.path in {"/apply", "/smoke", "/favicon.ico"} and not p.query
        if same and req.method == "POST" and p.path == "/submit" and not p.query:
            if self.approved_payload and not self.consumed:
                self.consumed = True
                await route.continue_(headers={**req.headers, "x-human-approval": self.server_token,
                                              "x-approved-payload-sha256": self.approved_payload})
                return
        if allowed:
            await route.continue_()
        else:
            self.blocked.append({"method": req.method, "url": req.url})
            await route.abort("blockedbyclient")
