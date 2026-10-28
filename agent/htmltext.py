"""Turn a fetched HTML page into plain text for extraction.

Keeps everything a reader or a crawler could see in the source, including
HTML comments and hidden elements, so a prompt-injection attempt still reaches
the extractor and can be flagged. Drops <script> and <style> bodies, but counts
scripts so a JavaScript-only site can be spotted.
"""

import base64
import json
import re
from html.parser import HTMLParser

BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article",
    "header", "footer", "nav", "main", "aside", "h1", "h2", "h3", "h4", "h5", "h6",
    "dt", "dd", "dl", "blockquote", "td", "th", "title", "form", "hr",
}


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.skip = 0
        self.in_script = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self.skip += 1
            if tag == "script":
                self.in_script = True
                self.scripts.append("")
            return
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(f" [image: {alt}] ")
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template"):
            self.skip = max(0, self.skip - 1)
            if tag == "script":
                self.in_script = False
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data
        if self.skip:
            return
        self.parts.append(data)

    def handle_comment(self, data):
        if data.strip():
            self.parts.append(f"\n[html comment: {data.strip()}]\n")


def _clean(text):
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _script_payload(script):
    """Some vendor sites ship the whole page as a base64 JSON blob that a script
    decodes into the page ({"t": title, "h": html}). Decode it with plain code,
    without running any JavaScript. Returns the HTML or None."""
    for blob in re.findall(r'"([A-Za-z0-9+/=]{200,})"', script):
        try:
            data = json.loads(base64.b64decode(blob).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("h"), str):
            return data["h"]
    return None


def html_to_text(html):
    """Return (text, links, info).

    info says how much text the page shows without JavaScript and whether it
    needs JavaScript to show its content (js_only). For a js_only page whose
    content is embedded in a script, the text is the decoded content, marked so.
    """
    p = _TextParser()
    p.feed(html)
    p.close()
    text = _clean("".join(p.parts))
    links = p.links
    info = {"text_chars": len(text), "scripts": len(p.scripts),
            "script_chars": sum(len(s) for s in p.scripts), "js_only": False}

    if p.scripts and len(text) < 200:
        info["js_only"] = True
        for script in p.scripts:
            inner = _script_payload(script)
            if inner:
                q = _TextParser()
                q.feed(inner)
                q.close()
                decoded = _clean("".join(q.parts))
                info["decoded_from_script"] = True
                text = (text + "\n\n[This page shows nothing without JavaScript. "
                        "The content below was decoded from the page's script.]\n\n" + decoded)
                links = links + q.links
                break
    return text, links, info
