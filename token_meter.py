#!/usr/bin/env python3
"""TokenMeter - OpenAI API call logger and cost estimator"""
import sqlite3, os, hashlib, argparse, datetime

DB = os.path.join(os.path.dirname(__file__), "token_meter.db")

def dbc():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS c("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "ph TEXT, pt INT, ct INT, m TEXT, cost REAL, ts TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS xph ON c(ph)")
    conn.execute("CREATE INDEX IF NOT EXISTS xm ON c(m)")
    return conn

def h(t):
    return hashlib.sha256(t.encode()).hexdigest()[:16]

PRICES = {
    "gpt-5.5": {"i": 15.0, "o": 60.0},
    "gpt-5.5-pro": {"i": 30.0, "o": 120.0},
    "gpt-5.4": {"i": 10.0, "o": 40.0},
    "gpt-5.4-mini": {"i": 1.5, "o": 6.0},
    "deepseek-chat": {"i": 0.14, "o": 0.28},
    "deepseek-reasoner": {"i": 0.55, "o": 2.19},
    "deepseek-chat": {"i": 0.14, "o": 0.28},
}

def cost(m, pt, ct):
    p = PRICES.get(m, {"i": 10.0, "o": 40.0})
    return (pt/1e6*p["i"]) + (ct/1e6*p["o"])

def rec(t, pt, ct, m):
    c = cost(m, pt, ct)
    conn = dbc()
    conn.execute("INSERT INTO c VALUES(?,?,?,?,?,?,?)",
        (None, h(t), pt, ct, m, c, datetime.datetime.now().isoformat()))
    conn.commit(); conn.close()
    return c

def est(t, m="gpt-5.5"):
    ph = h(t)
    conn = dbc()
    rows = conn.execute("SELECT pt, ct, cost FROM c WHERE ph=? AND m=?", (ph, m)).fetchall()
    if rows:
        ac = sum(r[2] for r in rows)/len(rows)
        conn.close()
        return {"s":"exact","n":len(rows),"c":round(ac,4),"pt":int(sum(r[0] for r in rows)/len(rows)),"ct":int(sum(r[1] for r in rows)/len(rows))}
    ept = max(1, len(t)//4)
    conn.close()
    return {"s":"est","c":round(cost(m,ept,ept),4),"pt":ept,"ct":ept}

def sts():
    conn = dbc()
    r = conn.execute("SELECT COUNT(*),SUM(cost),SUM(pt),SUM(ct) FROM c").fetchone()
    conn.close()
    return {"n":r[0] or 0,"c":round(r[1] or 0,4),"pt":r[2] or 0,"ct":r[3] or 0}

if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["rec","est","sts"])
    p.add_argument("--t", help="text")
    p.add_argument("--pt", type=int)
    p.add_argument("--ct", type=int)
    p.add_argument("--m", default="gpt-5.5")
    a = p.parse_args()
    if a.cmd == "rec":
        c = rec(a.t, a.pt, a.ct, a.m)
        print(f"OK: {a.m} in {a.pt}+out{a.ct}=${c:.4f}")
    elif a.cmd == "est":
        r = est(a.t, a.m)
        rs,rpt,rct,rc=r["s"],r["pt"],r["ct"],r["c"];print(f"[{rs}] in {rpt}+out{rct}=${rc}")
    elif a.cmd == "sts":
        s = sts()
        sn,sc,spt,sct=s["n"],s["c"],s["pt"],s["ct"];print(f"calls:{sn} cost:${sc} pt:{spt} ct:{sct}")

import urllib.request, json

def _post(url, body, key):
    """Internal: HTTP POST with urllib (no requests dependency needed)."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def call_chat(prompt, model="deepseek-chat", api_key=None, system=None, **kw):
    """Call OpenAI Chat Completions with auto-record."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key: raise ValueError("Set OPENAI_API_KEY or pass api_key")
    msgs = []
    if system: msgs.append({"role":"system","content":system})
    msgs.append({"role":"user","content":prompt})
    body = {"model":model,"messages":msgs}
    body.update(kw)
    d = _post("https://api.deepseek.com/v1/chat/completions" if model.startswith("deepseek") else "https://api.openai.com/v1/chat/completions", body, key)
    if "error" in d: raise Exception("API error: "+json.dumps(d["error"]))
    u = d.get("usage",{})
    pt = u.get("prompt_tokens",0)
    ct = u.get("completion_tokens",0)
    c = rec(prompt, pt, ct, model)
    t = d["choices"][0]["message"]["content"]
    return t, {"cost":c,"pt":pt,"ct":ct,"model":model}

def call_responses(prompt, model="gpt-5.5", api_key=None, **kw):
    """Call OpenAI Responses API with auto-record."""
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key: raise ValueError("Set OPENAI_API_KEY or pass api_key")
    body = {"model":model,"input":prompt}
    body.update(kw)
    d = _post("https://api.openai.com/v1/responses", body, key)
    if "error" in d: raise Exception("API error: "+json.dumps(d["error"]))
    u = d.get("usage",{})
    pt = u.get("input_tokens",0) or u.get("prompt_tokens",0)
    ct = u.get("output_tokens",0) or u.get("completion_tokens",0)
    c = rec(prompt, pt, ct, model)
    t = d.get("output_text","") or d.get("choices",[{}])[0].get("message",{}).get("content","")
    return t, {"cost":c,"pt":pt,"ct":ct,"model":model}