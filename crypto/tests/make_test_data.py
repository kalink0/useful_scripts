#!/usr/bin/env python3
"""Synthetic test extractions for SALT, with real (valid, randomly generated) seed phrases.

Creates FFS ZIPs in the layouts of Cellebrite (Android "Dump/"), GrayKey (Android "/data/", with the
duplicate data/user/0; iOS "/private/var/") and a GrayKey keychain plist. Seeds, keys and addresses
are placed where they turn up in real cases (notes, messengers, SMS, clipboard, downloads, wallet
apps, Apple Notes gzip blobs, deleted SQLite rows, keychain), plus negative samples that must NOT
give seeds (CSS, JS, English text, word lists, repeated words). expected.json lists what SALT has to
find.

The seeds are random: valid checksums, but no wallet behind them. Same --seed, same data.

Usage:
  make_test_data.py OUTDIR [--seed N]        create the test data
  salt.py OUTDIR -r -o OUTDIR/out            scan it
  make_test_data.py --check OUTDIR/out       compare salt_findings.csv / salt_apps.csv with expected.json
"""
import argparse
import csv
import gzip
import hashlib
import hmac
import json
import os
import plistlib
import random
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from salt import BIP39_EN  # noqa: E402  (the word list, checked by its hash in salt.py)

WORDS = BIP39_EN.split()
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class Gen:
    def __init__(self, seed):
        self.rnd = random.Random(seed)
        self.expected = []  # dicts: file, kind, verified, value, path
        self.negative = []  # (file, path): no seed may be found there
        self.apps = []  # (file, app_id)

    # ---- values
    def bip39(self, n=12):
        nb = n * 4 // 3
        e = bytes(self.rnd.getrandbits(8) for _ in range(nb))
        cs = nb * 8 // 32
        v = int.from_bytes(e, "big") << cs | hashlib.sha256(e).digest()[0] >> (8 - cs)
        ws = [WORDS[v >> (11 * (n - 1 - i)) & 2047] for i in range(n)]
        if n - len(set(ws)) > 1:  # keep test seeds clearly seed-like
            return self.bip39(n)
        return " ".join(ws)

    def bad_checksum(self, n=12):
        while True:
            ws = self.rnd.sample(WORDS, n)
            idx = [WORDS.index(w) for w in ws]
            v = 0
            for i in idx:
                v = v << 11 | i
            cs = n // 3
            ent = (v >> cs).to_bytes((n * 11 - cs) // 8, "big")
            if hashlib.sha256(ent).digest()[0] >> (8 - cs) != v & ((1 << cs) - 1) and not self._electrum(ws):
                return " ".join(ws)

    @staticmethod
    def _electrum(ws):
        h = hmac.new(b"Seed version", " ".join(ws).encode(), hashlib.sha512).hexdigest()
        return h.startswith(("01", "100", "101", "102"))

    def electrum(self):
        while True:  # Electrum 2.0+ standard seed: version prefix "01", and not also a valid BIP39 seed
            ws = self.rnd.sample(WORDS, 12)
            if self._electrum(ws) and self.bad_or_valid(ws) == "bad":
                return " ".join(ws)

    @staticmethod
    def bad_or_valid(ws):
        v = 0
        for w in ws:
            v = v << 11 | WORDS.index(w)
        ent = (v >> 4).to_bytes(16, "big")
        return "valid" if hashlib.sha256(ent).digest()[0] >> 4 == v & 15 else "bad"

    def b58check(self, payload):
        raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        n = int.from_bytes(raw, "big")
        s = ""
        while n:
            n, r = divmod(n, 58)
            s = B58[r] + s
        return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + s

    def btc_address(self):
        return self.b58check(b"\x00" + bytes(self.rnd.getrandbits(8) for _ in range(20)))

    def wif(self):
        return self.b58check(b"\x80" + bytes(self.rnd.getrandbits(8) for _ in range(32)) + b"\x01")

    def xprv(self):
        body = bytes.fromhex("0488ade4") + bytes(9) + bytes(self.rnd.getrandbits(8) for _ in range(32)) + b"\0" + \
            bytes(self.rnd.getrandbits(8) for _ in range(32))
        return self.b58check(body)

    def eth(self):
        return "0x" + "".join(self.rnd.choice("0123456789abcdef") for _ in range(40))

    def uuid(self):
        h = "%032X" % self.rnd.getrandbits(128)
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

    # ---- bookkeeping
    def expect(self, file, kind, verified, value, path):
        self.expected.append(dict(file=file, kind=kind, verified=verified, value=value, path=path))


def sqlite_bytes(statements, delete=None):
    """SQLite database as bytes; delete: SQL run afterwards (the row stays in a free page)."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td, "x.db")
        con = sqlite3.connect(p)
        con.execute("PRAGMA secure_delete = OFF")
        for sql, args in statements:
            con.execute(sql, args)
        con.commit()
        if delete:
            con.execute(delete)
            con.commit()
        con.close()
        return p.read_bytes()


def add_android(g, z, file, prefix, dup_user0=False):
    """Android user data: messengers, notes, SMS, clipboard, downloads, wallet apps + negatives."""
    def put(path, data):
        z.writestr(prefix + path, data)
        if dup_user0 and path.startswith("data/data/"):
            z.writestr(prefix + "data/user/0/" + path[len("data/data/"):], data)  # GrayKey duplicate

    s = g.bip39(12)  # Google Keep note
    p = "data/data/com.google.android.keep/databases/keep.db"
    put(p, sqlite_bytes([("CREATE TABLE text_search_note_content (_id INTEGER PRIMARY KEY, title TEXT, text TEXT)", ()),
                         ("INSERT INTO text_search_note_content VALUES (1, ?, ?)", ("Wallet backup", s + "\nnicht verlieren!"))]))
    g.expect(file, "seed", "yes", s, p)

    s, deleted = g.bip39(12), g.bip39(24)  # WhatsApp message + a deleted one (free page)
    p = "data/data/com.whatsapp/databases/msgstore.db"
    put(p, sqlite_bytes([
        ("CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER, from_me INTEGER, text_data TEXT)", ()),
        ("INSERT INTO message VALUES (1, 1, 1, ?)", ("hier mein seed: " + s,)),
        ("INSERT INTO message VALUES (2, 1, 0, ?)", ("ok danke",)),
        ("INSERT INTO message VALUES (3, 1, 1, ?)", (deleted + " - bitte gleich löschen",)),
    ], delete="DELETE FROM message WHERE _id = 3"))
    g.expect(file, "seed", "yes", s, p)
    g.expect(file, "seed", "yes", deleted, p)

    s = g.bip39(24)  # SMS, numbered
    p = "data/data/com.android.providers.telephony/databases/mmssms.db"
    numbered = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(s.split()))
    put(p, sqlite_bytes([("CREATE TABLE sms (_id INTEGER PRIMARY KEY, address TEXT, body TEXT)", ()),
                         ("INSERT INTO sms VALUES (1, '+4915100000000', ?)", (numbered,))]))
    g.expect(file, "seed", "yes", s, p)

    s = g.bip39(18)  # Gboard clipboard
    p = "data/data/com.google.android.inputmethod.latin/databases/gboard_clipboard.db"
    put(p, sqlite_bytes([("CREATE TABLE clips (_id INTEGER PRIMARY KEY, text TEXT, timestamp INTEGER)", ()),
                         ("INSERT INTO clips VALUES (1, ?, 1700000000000)", (s,))]))
    g.expect(file, "seed", "yes", s, p)

    s = g.bip39(12)  # download, file name says what it is
    p = "data/media/0/Download/recovery phrase.txt"
    put(p, "\r\n".join(s.split()))
    g.expect(file, "seed", "yes", s, p)
    g.expect(file, "wallet_file", "", "recovery phrase.txt", p)

    s = g.bip39(15)  # JSON backup of a notes app, upper case
    p = "data/data/com.example.notes/files/backup.json"
    put(p, json.dumps({"notes": [{"title": "PHRASE", "words": s.upper().split()}]}))
    g.expect(file, "seed", "yes", s, p)

    s = g.electrum()  # Electrum seed in a text note
    p = "data/media/0/Documents/electrum.txt"
    put(p, "Electrum wallet\nseed: " + s + "\n")
    g.expect(file, "seed", "yes", s, p)

    s = g.bad_checksum(12)  # typed wrong: no checksum -> unverified
    p = "data/data/com.samsung.android.app.notes/databases/sdoc.db"
    put(p, sqlite_bytes([("CREATE TABLE sdoc (_id INTEGER PRIMARY KEY, content TEXT)", ()),
                         ("INSERT INTO sdoc VALUES (1, ?)", (s,))]))
    g.expect(file, "seed", "no", s, p)

    wif, xprv, btc, eth = g.wif(), g.xprv(), g.btc_address(), g.eth()  # keys / addresses
    p = "data/media/0/Download/keys.txt"
    put(p, f"wif {wif}\nxprv {xprv}\nbtc {btc}\neth {eth}\n")
    g.expect(file, "private_key", "yes", wif, p)
    g.expect(file, "private_key", "yes", xprv, p)
    g.expect(file, "address", "yes", btc, p)
    g.expect(file, "address", "", eth, p)

    # wallet app: folder + Ethereum keystore file
    g.apps.append((file, "com.wallet.crypto.trustapp"))
    put("data/data/com.wallet.crypto.trustapp/shared_prefs/prefs.xml", f'<map><string name="addr">{eth}</string></map>')
    ks = f"data/data/com.wallet.crypto.trustapp/files/UTC--2024-05-01T10-00-00.000Z--{eth[2:]}"
    put(ks, json.dumps({"address": eth[2:], "crypto": {"cipher": "aes-128-ctr", "ciphertext": "00" * 32}}))
    g.expect(file, "wallet_file", "", ks.rsplit("/", 1)[1], ks)
    g.apps.append((file, "com.coinbase.android"))
    put("data/data/com.coinbase.android/shared_prefs/x.xml", "<map/>")

    # negatives: code, CSS, prose, word lists, repetitions - no seed may be found here
    neg = {
        "data/data/com.android.chrome/cache/Cache/Cache_Data/1a2b_0":
            "top:0;right:0;bottom:0;left:0;margin:auto;right:auto;bottom:auto;top:-2px}.list-group .list-group-item"
            ":first-child{border-top-width:0}.panel>.table{margin-bottom:0}" * 20,
        "data/data/com.discord/files/index.android.bundle":
            "function tc(a){switch(a&-a){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;"
            "case 16:return 16}}return this.height=(this.width=(this.top=Math.round(this.left)))" * 20,
        "data/data/com.example.reader/files/book.txt":
            "You can adjust media volume, call volume, ring volume and alarm volume in this menu. " * 20,
        "data/data/com.example.game/files/words.txt": "\n".join(WORDS[:300]),  # a word list: wordlist, no seed
        "data/data/com.example.app/files/repeat.txt": " ".join(["case", "return"] * 12),
    }
    for p, data in neg.items():
        put(p, data)
        g.negative.append((file, p))


def ios_container(g, put, kind, ident):
    u = g.uuid()
    base = f"private/var/mobile/Containers/{kind}/{u}/"
    put(base + ".com.apple.mobile_container_manager.metadata.plist",
        plistlib.dumps({"MCMMetadataIdentifier": ident, "MCMMetadataContentClass": 2}, fmt=plistlib.FMT_BINARY))
    return base


def add_ios(g, z, file, prefix):
    def put(path, data):
        z.writestr(prefix + path, data)

    s = g.bip39(12)  # Apple Notes: note body gzip-compressed in ZICNOTEDATA.ZDATA
    notes = ios_container(g, put, "Shared/AppGroup", "group.com.apple.notes")
    p = notes + "NoteStore.sqlite"
    blob = gzip.compress(b"\x08\x00\x12\x80\x01\x08\x00\x10\x00\x1a\x7a\x12" + s.encode() + b"\x1a\x10\x08\x00")
    put(p, sqlite_bytes([("CREATE TABLE ZICNOTEDATA (Z_PK INTEGER PRIMARY KEY, ZNOTE INTEGER, ZDATA BLOB)", ()),
                         ("INSERT INTO ZICNOTEDATA VALUES (1, 1, ?)", (blob,))]))
    g.expect(file, "seed", "yes", s, p)

    s = g.bip39(24)  # iMessage
    p = "private/var/mobile/Library/SMS/sms.db"
    put(p, sqlite_bytes([("CREATE TABLE message (ROWID INTEGER PRIMARY KEY, text TEXT, is_from_me INTEGER)", ()),
                         ("INSERT INTO message VALUES (1, ?, 1)", ("Backup: " + s,))]))
    g.expect(file, "seed", "yes", s, p)

    tw = ios_container(g, put, "Data/Application", "com.sixdays.trust")  # Trust Wallet container
    g.apps.append((file, "com.sixdays.trust"))
    put(tw + "Library/Preferences/com.sixdays.trust.plist", plistlib.dumps({"onboarded": True}))
    ios_container(g, put, "Data/Application", "com.apple.mobilenotes")  # no wallet

    p = tw + "Documents/cache.css"  # negative inside the wallet app
    put(p, "top:0;right:0;bottom:0;left:0;margin:auto;right:auto;bottom:auto;top:-2px" * 30)
    g.negative.append((file, p))


def add_keychain(g, path):
    file = path.name
    s = g.bip39(12)
    item = {"agrp": b"ABCDE12345.com.sixdays.trust", "svce": b"wallet", "acct": b"mnemonic",
            "v_Data": s.encode(), "rowid": 42}
    other = {"agrp": b"com.apple.bluetooth", "svce": b"BluetoothGlobal", "acct": b"Identity Root",
             "v_Data": b"<?xml version='1.0'?><plist/>", "rowid": 1}
    path.write_bytes(plistlib.dumps({"genp": [other, item], "inet": [], "keys": [], "cert": []}, fmt=plistlib.FMT_BINARY))
    label = f"keychain/genp/42 agrp=ABCDE12345.com.sixdays.trust svce=wallet acct=mnemonic"
    g.expect(file, "seed", "yes", s, label)
    g.expect(file, "keychain", "", s, label)
    g.apps.append((file, "com.sixdays.trust"))


def create(out, seed):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    g = Gen(seed)
    for name, fn in (("android_cellebrite", lambda z, f: add_android(g, z, f, "Dump/")),
                     ("android_graykey", lambda z, f: add_android(g, z, f, "/", dup_user0=True)),
                     ("ios_graykey", lambda z, f: add_ios(g, z, f, "/"))):
        sub = out / name
        sub.mkdir(exist_ok=True)
        f = sub / ("EXTRACTION_FFS.zip" if "cellebrite" in name else "XXXX_files_full.zip")
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
            fn(z, f.relative_to(out).as_posix())
    kc = out / "ios_graykey" / "XXXX_keychain.plist"
    add_keychain(g, kc)
    for e in g.expected:
        if e["file"] == kc.name:
            e["file"] = kc.relative_to(out).as_posix()
    g.apps = [(kc.relative_to(out).as_posix() if f == kc.name else f, a) for f, a in g.apps]
    (out / "expected.json").write_text(json.dumps(
        {"seed": seed, "expected": g.expected, "negative": g.negative, "apps": g.apps}, indent=1))
    print(f"{len(g.expected)} expected findings, {len(g.negative)} negative samples, {len(g.apps)} wallet apps -> {out}")


def check(outdir):
    outdir = Path(outdir)
    data = outdir.parent / "expected.json"
    if not data.exists():
        data = Path(outdir) / "expected.json"
    exp = json.loads(data.read_text())
    root = data.parent

    def rel(src):
        try:
            return Path(src).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return src

    with open(outdir / "salt_findings.csv", encoding="utf-8-sig") as fh:
        found = [dict(r, file=rel(r["source"])) for r in csv.DictReader(fh, delimiter=";")]
    with open(outdir / "salt_apps.csv", encoding="utf-8-sig") as fh:
        apps = {(rel(r["source"]), r["app_id"]) for r in csv.DictReader(fh, delimiter=";")}
    bad = 0
    for e in exp["expected"]:
        hits = [r for r in found if r["file"] == e["file"] and r["kind"] == e["kind"] and r["value"] == e["value"]
                and r["path"] == e["path"] and r["verified"] == e["verified"]]
        ok = len(hits) == 1 and int(hits[0]["count"]) >= 1
        bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {e['kind']:12} {e['verified'] or '-':3} {e['file']}: {e['path'][-55:]}"
              + ("" if ok else f"   (found {len(hits)}x)"))
    for f, p in exp["negative"]:
        hits = [r for r in found if r["file"] == f and r["path"] == p and r["kind"] == "seed"]
        bad += bool(hits)
        print(f"{'FAIL' if hits else 'OK  '} no seed      -   {f}: {p[-55:]}" + (f"   ({len(hits)} false)" if hits else ""))
    for f, a in exp["apps"]:
        ok = (f, a) in apps
        bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'} wallet app       {f}: {a}")
    known = {(e["file"], e["kind"], e["value"], e["path"]) for e in exp["expected"]}
    extra = [r for r in found if r["kind"] in ("seed", "private_key", "xpub")
             and (r["file"], r["kind"], r["value"], r["path"]) not in known]
    for r in extra:
        print(f"FAIL unexpected {r['kind']} {r['verified']} in {r['file']}: {r['path']}  {r['value'][:60]}")
    bad += len(extra)
    print(f"\n{'ALL OK' if not bad else f'{bad} FAILED'}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="Synthetic test extractions for SALT (valid random seeds).")
    ap.add_argument("out", help="output folder (create) or SALT result folder (--check)")
    ap.add_argument("--seed", type=int, default=1, help="random seed (same seed: same data)")
    ap.add_argument("--check", action="store_true", help="check SALT's CSVs in OUT against expected.json")
    a = ap.parse_args()
    if a.check:
        return check(a.out)
    create(a.out, a.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
