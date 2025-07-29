import os, sys, html
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs
from dotenv import load_dotenv
from openai import OpenAI
import markdown2

load_dotenv()
api_key = os.getenv("GITHUB_TOKEN")
base_url = os.getenv("GITHUB_BASE_URL")
if not api_key or not base_url:
    print("Missing GITHUB_TOKEN or GITHUB_BASE_URL in .env")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url=base_url)

def clean_heading_spaces(text):
    # Ensure '# ' instead of '#**' or '#-nbsp'
    lines = text.splitlines()
    fixed = []
    for line in lines:
        if line.startswith('#') and len(line) > 1 and line[1] not in (' '):
            # Insert a proper space
            # e.g. '#**History' => '# **History'
            nohash = line.lstrip('#')
            fixed.append(line[:len(line) - len(nohash)] + ' ' + nohash)
        else:
            fixed.append(line)
    return '\n'.join(fixed)

def render_page(prompt, prompt_html, answer_html=""):
    return f"""
<!DOCTYPE html><html>
<head><meta charset="utf-8"><title>Markdown Chat</title>
<style>
body{{font-family:sans-serif; margin:20px;}}
h1,h2,h3{{margin-top:1em;}}
.box{{border:1px solid #ccc; padding:10px; margin:10px 0; background:#f9f9f9;}}
textarea{{width:90%; height:100px;}}
</style>
</head><body>
<h1>Ask GPT‑4o Markdown-style</h1>
<form method="POST" action="/">
  <textarea name="prompt">{html.escape(prompt)}</textarea><br>
  <button type="submit">Send</button>
</form>
<hr>
<div><strong>Your input (rendered):</strong></div>
<div class="box">{prompt_html}</div>
<hr>
<div><strong>Assistant answer:</strong></div>
<div class="box">{answer_html}</div>
</body></html>
"""

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(render_page("", "", "").encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        prompt = data.get('prompt', [''])[0]

        fixed_input = clean_heading_spaces(prompt)
        prompt_html = markdown2.markdown(fixed_input, extras=["fenced-code-blocks", "tables", "header-ids"])

        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                  {"role":"system", "content":"You are a helpful assistant."},
                  {"role":"user","content":fixed_input}
                ],
            )
            ans = resp.choices[0].message.content
            fixed_ans = clean_heading_spaces(ans)
            answer_html = markdown2.markdown(fixed_ans, extras=["fenced-code-blocks","tables","header-ids"])
        except Exception as e:
            answer_html = f"<p><em>Error: {html.escape(str(e))}</em></p>"

        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(render_page(prompt, prompt_html, answer_html).encode("utf-8"))

if __name__=='__main__':
    print("Starting at http://localhost:8000")
    HTTPServer(('',8000), Handler).serve_forever()
