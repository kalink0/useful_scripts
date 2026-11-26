#!/usr/bin/env python3
# ------------------------------------------------------------------------------
# AUTHOR:         kalink0 (Marco Neumann)
# CREATION DATE:  2026-11-25
#
# LICENSE:        CC0-1.0
#
# TITLE:          basil.py
#
# DESCRIPTION:    BASIL - crypto wallets, seeds and keys in mobile extractions (formerly SALT)
# ------------------------------------------------------------------------------
"""BASIL - Blockchain Assets, Seeds, Identifiers & Ledgers: crypto wallets, seeds and keys in mobile extractions.

Scans full file system extractions (ZIP from Cellebrite, GrayKey, Magnet, ...), iTunes backups,
extracted dumps and GrayKey keychain plists, directly (nothing is unpacked), for:
  - wallet / exchange apps (Android package, iOS bundle id, keychain access group)
  - wallet files by name (wallet.dat, Ethereum keystore UTC--..., *seed phrase*, ...)
  - seed phrases: 12-24 BIP39 words in a row, BIP39 checksum / Electrum version checked
  - private keys (WIF, xprv), xpub/ypub/zpub, addresses (BTC, LTC, DOGE, TRX, bech32 with
    checksum; ETH by pattern only)
Text, SQLite (incl. free pages / WAL), JSON, plists and gzip blobs in them (e.g. Apple Notes) are
searched as raw bytes. Office documents (docx, xlsx, pptx, odt, ...) are opened and their text is
searched; mails (MIME parts in base64 / quoted-printable, in .eml / .emlx / mbox files or databases)
are decoded, HTML is searched without its tags. Optional (--export): copies the files of the wallet
apps and of the hits, with SHA-256.

Only the standard library is used (GUI: tkinter).

Usage:
  basil.py                              start the GUI
  basil.py <zip|folder|keychain.plist> ... [-r] [-d] [-o DIR] [-x] [-j N] [--max-size MB]
"""
import argparse
import binascii
import csv
import hashlib
import hmac
import html
import io
import os
import plistlib
import quopri
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
import zlib
from collections import Counter
from pathlib import Path

VERSION = "dev"  # set when building: tag basil-v1.0 -> "v1.0"
SIGNATURE = f"BASIL {VERSION}"  # --version, "tool" column of basil_summary.csv
ICON_PNG = (  # 64 px icon: basil sprig (window icon, header)
    "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"
)

# ---- wallet / exchange apps: Android package or iOS bundle id -> name (extensions "<id>.*" match too)
KNOWN_APPS = {
    "com.wallet.crypto.trustapp": "Trust Wallet", "com.sixdays.trust": "Trust Wallet",
    "io.metamask": "MetaMask",
    "com.coinbase.android": "Coinbase", "com.vilcsak.bitcoin2": "Coinbase",
    "org.toshi": "Coinbase Wallet",
    "com.binance.dev": "Binance", "com.czzhao.binance": "Binance",
    "com.kraken.trade": "Kraken",
    "piuk.blockchain.android": "Blockchain.com", "com.rainydayapps.blockchain": "Blockchain.com",
    "de.schildbach.wallet": "Bitcoin Wallet (Schildbach)",
    "com.mycelium.wallet": "Mycelium",
    "exodusmovement.exodus": "Exodus",
    "io.atomicwallet": "Atomic Wallet",
    "com.bitpay.wallet": "BitPay",
    "com.ledger.live": "Ledger Live",
    "com.samourai.wallet": "Samourai",
    "org.electrum.electrum": "Electrum",
    "app.phantom": "Phantom",
    "com.bitcoin.mwallet": "Bitcoin.com Wallet",
    "com.coinomi.wallet": "Coinomi",
    "co.edgesecure.app": "Edge",
    "com.cakewallet.cake_wallet": "Cake Wallet",
    "com.m2049r.xmrwallet": "Monerujo",
    "io.bluewallet.bluewallet": "BlueWallet",
    "com.muun.falcon": "Muun",
    "com.bybit.app": "Bybit",
    "com.okinc.okex.gp": "OKX",
    "co.mona.android": "Crypto.com",
    "com.defi.wallet": "Crypto.com DeFi Wallet",
    "com.bitget.exchange": "Bitget", "com.bitkeep.wallet": "Bitget Wallet",
    "com.kubi.kucoin": "KuCoin",
    "com.bitvavo": "Bitvavo",
    "com.bitpanda.bitpanda": "Bitpanda",
    "com.zengo.wallet": "ZenGo",
    "com.tangem.wallet": "Tangem",
    "io.trezor.suite": "Trezor Suite",
    "me.rainbow": "Rainbow",
    "com.uniswap.mobile": "Uniswap Wallet",
    "io.safepal.wallet": "SafePal",
    "vip.mytokenpocket": "TokenPocket",
    "im.token.app": "imToken",
    "com.greenaddress.greenbits_android_wallet": "Blockstream Green",
    "io.horizontalsystems.bankwallet": "Unstoppable",
    "com.breadwallet": "BRD",
    "com.samsung.android.coldwalletservice": "Samsung Blockchain Keystore",
}
# other apps whose id contains one of these words: listed as "possible" (match "name")
APP_WORDS = re.compile(r"wallet|crypto|coin|bitcoin|btc|metamask|binance|kraken|exodus|ledger|trezor|electrum|"
                       r"monero|xmr|phantom|blockchain|defi|bybit|okex|kucoin|bitpanda|bitvavo|uniswap|tangem|"
                       r"zengo|safepal|tokenpocket|imtoken|bitget|satoshi")
APP_IGNORE = ("com.apple.", "com.android.", "android.", "com.google.android.gms",
              "com.google.android.apps.walletnfcrel", "com.samsung.android.spay")

# ---- what is scanned
# platform -> scanned path prefixes (user data); itunes / unknown layouts: everything
SCAN_ROOTS = {"android": ("data/data/", "data/user/", "data/user_de/", "data/media/"),
              "ios": ("private/var/mobile/",)}
SKIP_EXT = set("jpg jpeg png gif webp heic heif bmp tif tiff ico svg mp4 m4v mov 3gp mkv avi webm mp3 m4a "
               "aac ogg oga opus wav amr flac caf so dex odex oat vdex art apk jar aar ttf otf woff woff2 exo "
               "tflite onnx car ktx astc pdf zip shm mwm hprof lwext4".split())  # media, binaries, maps, heap dumps
SKIP_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF", b"OggS", b"ID3", b"\x7fELF", b"dex\n",
              b"PK\x03\x04", b"%PDF", b"fLaC")
MAX_SIZE_MB = 1024            # larger files are not scanned (still exported with --export); messenger DBs can be ~1 GB
CHUNK = 16 << 20              # files are scanned in chunks of this size ...
OVERLAP, GUARD = 4096, 1024   # ... overlapping, so no hit is cut or found twice
GZ_MAX = 4 << 20              # max. unpacked size of an embedded gzip blob / a decoded mail part
# Office / ODF / epub: ZIP containers whose XML text is searched (iWork .pages etc.: snappy, not readable)
OFFICE_EXT = set("docx docm dotx dotm xlsx xlsm xltx xltm pptx pptm potx potm ppsx odt ott ods ots odp otp odg "
                 "epub".split())
HTML_EXT = {"html", "htm", "xhtml", "enex"}  # also searched without their tags
DOC_MAX = 64 << 20            # max. size of an HTML file / of one XML file in a document (zip bomb guard)

WALLET_FILE_RE = re.compile(r"^(wallet\.dat|.+\.wallet|default_wallet|UTC--\d{4}-\d\d-\d\dT.+|"
                            r".*(mnemonic|seed[ _.-]?phrase|recovery[ _.-]?phrase|secret[ _.-]?phrase|"
                            r"private[ _.-]?key).*)$", re.I)
EXPORT_KINDS = {"seed", "private_key", "xpub", "wallet_file"}  # members with such hits are exported

APP_RES = [re.compile(r"^data/(?:data|user/\d+|user_de/\d+)/([^/]+)/"),
           re.compile(r"^data/media/\d+/Android/(?:data|media|obb)/([^/]+)/"),
           re.compile(r"^private/var/mobile/Containers/(?:Data/Application|Shared/AppGroup|Data/PluginKitPlugin)/"
                      r"([0-9A-Fa-f-]{36})/"),
           re.compile(r"^AppDomain(?:Group|Plugin)?-([^/]+)/")]
IOS_META = ".com.apple.mobile_container_manager.metadata.plist"

# ---- patterns (seeds and bech32 on the lower-cased data). No lookbehind / lookahead: they make Python's
# regex engine try every position (5x slower); the token boundaries are checked in free() instead.
SEED_RE = re.compile(rb"[a-z]{3,8}(?:[^a-z]{1,12}[a-z]{3,8}){11,}")
WORD_RE = re.compile(rb"[a-z]+")
# separator between two seed words: spaces / line breaks, numbering ("1. ", "2) ", "\n3: "), list ("," ";" '","')
SEED_SEP = re.compile(rb"""\s{1,4}|\s*[,;]\s*|\s*["']\s*[,;]?\s*["']\s*|\s*\d{1,2}\s*[.):-]?\s+|\s*["']?\s*\d{1,2}\s*[.):-]\s*["']?""")
MAX_REPEATS = 2  # repeated words in a seed: random 24 words repeat one in 13 %, 3+ in 0.04 % (code: many)
B58_RE = re.compile(rb"[13LMDTK5xyztuv][1-9A-HJ-NP-Za-km-z]{25,110}")
BECH_RE = re.compile(rb"(bc|ltc|tb)1([02-9ac-hj-np-z]{39,87})")
ETH_RE = re.compile(rb"0x[0-9a-fA-F]{40}")
LOWER = frozenset(b"abcdefghijklmnopqrstuvwxyz")
ALNUM = frozenset(b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") | LOWER
B64 = ALNUM | frozenset(b"+/=")
GZ_RE = re.compile(rb"\x1f\x8b\x08")
# markup (HTML, Office XML): tags that end a block become a line break, all other tags vanish
BLOCK_TAG_RE = re.compile(rb"</?(?:p|div|li|ul|ol|t[dhr]|h[1-6]|blockquote|pre|table|title|br|hr|"
                          rb"w:p|w:tc|w:br|w:cr|w:tab|a:p|a:br|a:tab|text:p|text:h|text:list-item|"
                          rb"text:line-break|text:tab|text:s|si|c|row)(?=[\s/>])[^>]*>", re.I)
TAG_RE = re.compile(rb"<!--.*?-->|<[!?/]?[A-Za-z][^>]*>", re.S)
ENT_RE = re.compile(rb"&(?:#\d{1,7}|#x[0-9a-fA-F]{1,6}|[A-Za-z]{2,8});")
WS_RE = re.compile(rb"\s*\n\s*|[ \t\r\f\v]{2,}")
# mail (MIME): encoded parts, their header; encoded words in headers (=?utf-8?B?...?=)
MIME_RE = re.compile(rb"content-transfer-encoding:[ \t]*(base64|quoted-printable)")
HDR_END_RE = re.compile(rb"\r?\n\r?\n")
B64_BODY_RE = re.compile(rb"[A-Za-z0-9+/=\s]+")
CTYPE_RE = re.compile(rb"content-type:[ \t]*([a-z0-9.+-]+/[a-z0-9.+-]+)", re.I)
FNAME_RE = re.compile(rb"name\*?=[ \t]*\"?([^\";\r\n]+)", re.I)
ENCWORD = rb"=\?[^?\s]+\?([bq])\?([^?\s]*)\?="
ENCWORD_RE = re.compile(ENCWORD, re.I)
ENCWORDS_RE = re.compile(ENCWORD + rb"(?:\s+" + ENCWORD.replace(b"(", b"(?:") + rb")*", re.I)
TEXT_EXT = {"txt", "csv", "json", "md", "log", "xml", "rtf"}  # attachments searched as text (besides text/*)
SEED_LENS = (24, 21, 18, 15, 12)
B58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
B58_IDX = {c: i for i, c in enumerate(B58)}
ADDR_VER = {0x00: "BTC", 0x05: "BTC", 0x30: "LTC", 0x32: "LTC", 0x1e: "DOGE", 0x41: "TRX"}
EXT_VER = {bytes.fromhex(k): v for k, v in {
    "0488b21e": "xpub", "0488ade4": "xprv", "049d7cb2": "ypub", "049d7878": "yprv",
    "04b24746": "zpub", "04b2430c": "zprv", "043587cf": "tpub", "04358394": "tprv"}.items()}
BECH_CHARS = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
PRINTABLE = bytes(c if 32 <= c < 127 else 46 for c in range(256))

CSV_COLS = {
    "summary": ["label", "source", "kind", "platform", "entries", "scanned_files", "scanned_bytes",
                "skipped_large", "wallet_apps", "seeds_verified", "seeds_unverified", "private_keys", "xpubs",
                "addresses_verified", "addresses_eth", "wallet_files", "keychain_items", "exported_files",
                "errors", "notes", "seconds", "version", "tool"],
    "findings": ["label", "source", "kind", "type", "verified", "value", "app", "app_name", "path", "offset",
                 "count", "context"],
    "apps": ["label", "source", "platform", "app_id", "name", "match", "files", "bytes", "locations"],
    "files": ["label", "source", "member", "exported", "size", "sha256"],
}


# ---------------------------------------------------------------------------------------------- checks
def words():
    global _IDX
    if "_IDX" not in globals():
        w = BIP39_EN.split()
        assert hashlib.sha256(("\n".join(w) + "\n").encode()).hexdigest() == BIP39_SHA256, "BIP39 wordlist damaged"
        _IDX = {x.encode(): i for i, x in enumerate(w)}
    return _IDX


def bip39_ok(idx):
    """BIP39 checksum of a list of word indices (12/15/18/21/24 words)."""
    n = len(idx)
    v = 0
    for i in idx:
        v = v << 11 | i
    cs = n // 3
    ent = (v >> cs).to_bytes((n * 11 - cs) // 8, "big")
    return hashlib.sha256(ent).digest()[0] >> (8 - cs) == v & ((1 << cs) - 1)


def electrum_ok(ws):
    """Electrum 2.0+ seed: version prefix of HMAC-SHA512("Seed version", seed)."""
    h = hmac.new(b"Seed version", b" ".join(ws), hashlib.sha512).hexdigest()
    return h.startswith(("01", "100", "101", "102"))


def b58check(s):
    """Base58Check -> payload, or None if the checksum is wrong."""
    n = 0
    for c in s:
        n = n * 58 + B58_IDX[c]
    raw = b"\0" * (len(s) - len(s.lstrip(b"1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")
    p, ck = raw[:-4], raw[-4:]
    return p if len(raw) > 4 and hashlib.sha256(hashlib.sha256(p).digest()).digest()[:4] == ck else None


def bech32_ok(hrp, data):
    chk = 1
    for v in [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp] + [BECH_CHARS.index(c) for c in data]:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i, g in enumerate((0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)):
            if b >> i & 1:
                chk ^= g
    return chk in (1, 0x2bc830a3)  # bech32 / bech32m


# ---------------------------------------------------------------------------------------------- byte scan
def free(buf, s, e, chars):
    """No character of chars directly before s / at e: the match is a whole token."""
    return (s == 0 or buf[s - 1] not in chars) and (e >= len(buf) or buf[e] not in chars)


def scan_bytes(buf, lo, hi, emit, where, depth=0):
    """Report all hits starting in buf[lo:hi]: emit(kind, type, verified, value, offset, context)."""
    def ctx(s, e, b=buf):
        return b[max(0, s - 40):e + 40].translate(PRINTABLE).decode("ascii")

    low = buf.lower()
    for m in SEED_RE.finditer(low):
        if lo <= m.start() < hi:
            s, e = m.span()
            _seeds(m, s > 0 and low[s - 1] in LOWER, e < len(low) and low[e] in LOWER, emit,
                   lambda s, e: (where(s), ctx(s, e)))
    for m in B58_RE.finditer(buf):
        s = m.group()
        n = len(s)
        if not lo <= m.start() < hi or not (26 <= n <= 35 or n in (51, 52, 111)) or not free(buf, *m.span(), B64):
            continue
        p = b58check(s)
        if p is None:
            continue
        hit = None
        if len(p) == 21 and p[0] in ADDR_VER:
            hit = ("address", ADDR_VER[p[0]])
        elif p[0] == 0x80 and (len(p) == 33 or len(p) == 34 and p[-1] == 1):
            hit = ("private_key", "WIF")
        elif len(p) == 78 and p[:4] in EXT_VER:
            t = EXT_VER[p[:4]]
            hit = ("private_key" if t.endswith("prv") else "xpub", t)
        if hit:
            emit(hit[0], hit[1], "yes", s.decode(), where(m.start()), ctx(m.start(), m.end()))
    for m in BECH_RE.finditer(low):
        hrp, data = m.group(1).decode(), m.group(2).decode()
        if lo <= m.start() < hi and free(low, *m.span(), ALNUM) and bech32_ok(hrp, data):
            emit("address", {"bc": "BTC", "ltc": "LTC", "tb": "BTC testnet"}[hrp], "yes", f"{hrp}1{data}",
                 where(m.start()), ctx(m.start(), m.end()))
    for m in ETH_RE.finditer(buf):
        if lo <= m.start() < hi and free(buf, *m.span(), ALNUM) and len(set(m.group()[2:].lower())) > 4:
            emit("address", "ETH", "", m.group().decode(), where(m.start()), ctx(m.start(), m.end()))
    if depth == 0:  # gzip blobs (e.g. Apple Notes ZICNOTEDATA)
        mv = memoryview(buf)
        for m in GZ_RE.finditer(buf):
            s = m.start()
            if not lo <= s < hi:
                continue
            try:
                out = zlib.decompressobj(31).decompress(mv[s:s + 4 * GZ_MAX], GZ_MAX)
            except zlib.error:
                continue
            if len(out) >= 24:
                scan_bytes(out, 0, len(out), emit, lambda p, s=s: f"{where(s)}+gz:{p}", depth + 1)
        scan_mime(buf, low, lo, hi, emit, where)


# ---------------------------------------------------------------------------------------------- documents, mail
def strip_markup(buf):
    """HTML / XML -> text. Block ends become line breaks, all other tags vanish without a trace (Word
    splits words into runs: <w:t>aban</w:t></w:r><w:r><w:t>don</w:t>), entities are decoded and
    whitespace runs shortened (a seed separator is at most 4 spaces)."""
    buf = TAG_RE.sub(b"", BLOCK_TAG_RE.sub(b"\n", buf))
    buf = ENT_RE.sub(lambda m: html.unescape(m.group().decode()).encode("utf-8", "replace"), buf)
    buf = buf.replace(b"\xc2\xa0", b" ")  # no-break space (&nbsp;)
    return WS_RE.sub(lambda m: b"\n" if b"\n" in m.group() else b" ", buf)


def scan_office(data, emit, where):
    """Office / ODF / epub document (a ZIP, in memory): the text of its XML / HTML files.

    where(member, pos) -> offset, e.g. "word/document.xml:812" (pos in the text without tags).
    """
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for i in z.infolist():
            if i.is_dir() or not i.filename.lower().endswith((".xml", ".xhtml", ".html", ".htm")):
                continue
            with z.open(i) as f:
                t = strip_markup(f.read(DOC_MAX))
            scan_bytes(t, 0, len(t), emit, lambda p, n=i.filename: where(n, p), 1)


def _b64(data):
    """Lenient base64: whitespace ignored, stops at the padding, a cut end is tolerated."""
    c = data.translate(None, b" \t\r\n\f\v").split(b"=")[0]
    if len(c) % 4 == 1:
        c = c[:-1]
    return binascii.a2b_base64(c + b"=" * (-len(c) % 4))


def scan_mime(buf, low, lo, hi, emit, where):
    """Mail parts in base64 / quoted-printable, wherever they are (.eml, .emlx, mbox, mail databases):
    decoded and searched; HTML without its tags, office attachments as documents, images etc. not.
    Encoded headers (Subject: =?UTF-8?B?...?=) too. Offsets: "<offset of the part>+mime:<pos>"."""
    for m in MIME_RE.finditer(low):
        s = m.start()
        if not lo <= s < hi:
            continue
        e = HDR_END_RE.search(low, m.end(), m.end() + 8192)
        if not e:
            continue
        # header of this part: back to the boundary line / the blank line before it (max. 4 KB)
        w = max(0, s - 4096)
        head = buf[max(w, low.rfind(b"\n--", w, s), low.rfind(b"\n\n", w, s), low.rfind(b"\n\r\n", w, s)):e.start()]
        b = e.end()
        try:
            if m.group(1) == b"base64":
                body = B64_BODY_RE.match(buf, b, b + GZ_MAX * 4 // 3 + GZ_MAX // 16)
                dec = _b64(body.group()) if body else b""
            else:
                end = low.find(b"\n--", b, b + GZ_MAX)
                dec = quopri.decodestring(buf[b:end if end >= 0 else b + GZ_MAX])
        except (binascii.Error, ValueError):
            continue
        if len(dec) < 24:
            continue
        ct = CTYPE_RE.search(head)
        ctype = ct.group(1).lower() if ct else b""
        fn = FNAME_RE.search(head)
        fname = fn.group(1).strip().decode("utf-8", "replace") if fn else ""
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        loc = lambda p, s=s: f"{where(s)}+mime:{p}"  # noqa: E731
        if ext in OFFICE_EXT and dec.startswith(b"PK\x03\x04"):
            try:
                scan_office(dec, emit, lambda n, p, s=s: f"{where(s)}+mime:{fname}/{n}:{p}")
            except (zipfile.BadZipFile, EOFError, ValueError, zlib.error):
                pass  # damaged / cut attachment
        elif ctype == b"text/html" or ext in HTML_EXT or not ctype and b"<html" in dec[:2048].lower():
            t = strip_markup(dec)
            scan_bytes(t, 0, len(t), emit, loc, 1)
        elif ctype.startswith(b"text/") or ext in TEXT_EXT or not ctype:
            scan_bytes(dec, 0, len(dec), emit, loc, 1)
    for m in ENCWORDS_RE.finditer(buf):
        s = m.start()
        if not lo <= s < hi:
            continue
        dec = b""
        for x in ENCWORD_RE.finditer(m.group()):
            try:
                dec += _b64(x.group(2)) if x.group(1) in b"bB" else quopri.decodestring(x.group(2), header=True)
            except (binascii.Error, ValueError):
                pass
        if len(dec) >= 24:
            scan_bytes(dec, 0, len(dec), emit, lambda p, s=s: f"{where(s)}+header:{p}", 1)


def _seeds(m, cut_start, cut_end, emit, loc):
    """Runs of >= 12 BIP39 words in a regex match -> seeds (checksum ok) or unverified word runs.

    Words only count as a run when separated like a written seed (SEED_SEP: spaces, line breaks,
    numbering, list commas / quotes) - code and CSS ("top:0;right:0", "case 1:return") are not.
    SQLite stores the columns of a row without separator, so a seed can be glued to the text before
    or after it ("Wallet backupabandon ability ... aboutnicht"): at the edges of a run, a word that
    ends / starts with a BIP39 word is tried as that word too; the checksum decides.
    cut_start / cut_end: the match starts / ends inside a longer word, that token is no word.
    """
    idx = words()
    g = m.group()
    base = m.start()
    toks = list(WORD_RE.finditer(g))
    run, starts = [], [[]]  # starts: alternative first words (suffixes of a glued word)
    for i, t in enumerate(toks + [None]):
        w = t.group() if t is not None else b""
        ok = t is not None and w in idx and not (i == 0 and cut_start or i == len(toks) - 1 and cut_end)
        prev = bool(run) or any(starts)
        if ok and (not prev or SEED_SEP.fullmatch(g, toks[i - 1].end(), t.start())):
            run.append((w, base + t.start(), base + t.end()))
            continue
        # run ends here; t may begin with the last seed word (glued) and end with the next first word
        sep = t is not None and prev and SEED_SEP.fullmatch(g, toks[i - 1].end(), t.start())
        ends = [[]] + ([[(w[:k], base + t.start(), base + t.start() + k)] for k in range(min(8, len(w) - 1), 2, -1)
                        if w[:k] in idx] if t is not None and not ok and sep else [])
        _seed_run([s + run + e for s in starts for e in ends], idx, emit, loc)
        if ok:
            run, starts = [(w, base + t.start(), base + t.end())], [[]]
        else:
            run = []
            starts = [[]] + ([[(w[-k:], base + t.end() - k, base + t.end())] for k in range(min(8, len(w) - 1), 2, -1)
                              if w[-k:] in idx] if t is not None else [])


def _seed_run(variants, idx, emit, loc):
    """Variants of one word run (glued words split or not): report the first with a valid checksum,
    else the plain run (first variant) as unverified."""
    found = None
    for run in sorted(variants, key=len, reverse=True):
        hit = _seed_eval(run, idx)
        if hit and hit[0] in ("seed_ok", "wordlist"):
            found = hit
            break
    if not found:
        plain = min(variants, key=len)
        found = _seed_eval(plain, idx)
    if not found:
        return
    what, typ, run, a, b = found
    ws = b" ".join(w for w, _, _ in run[a:b]).decode()
    if what == "wordlist":
        emit("wordlist", "BIP39", "", f"{len(run)} BIP39 words in a row", *loc(run[0][1], run[0][2]))
    else:
        emit("seed", typ, "yes" if what == "seed_ok" else "no", ws, *loc(run[a][1], run[b - 1][2]))


def _seed_eval(run, idx):
    """-> ("seed_ok" | "seed_unverified" | "wordlist", type, run, start, end) or None."""
    n = len(run)
    if n < 12:
        return None
    ws = [w for w, _, _ in run]
    if n > 48 and len(set(ws)) > 48:  # a word list, not a seed (apps ship it): many different words -
        return "wordlist", "BIP39", run, 0, n  # not [false,false,...] or [true,false,...] in JSON
    if n <= 24 and n - len(set(ws)) > MAX_REPEATS:  # "case case case", "this ... this"
        return None
    wins = [(0, n)] if n in SEED_LENS else [(a, a + k) for k in SEED_LENS if k < n for a in (0, n - k)]
    wins = [(a, b) for a, b in wins if b - a - len(set(ws[a:b])) <= MAX_REPEATS]
    for a, b in wins:
        if bip39_ok([idx[w] for w in ws[a:b]]):
            return "seed_ok", f"BIP39 {b - a} words", run, a, b
    for a, b in [w_ for w_ in ([(0, n)] if n <= 24 else []) + [(0, 12), (n - 12, n)]
                 if w_[1] - w_[0] - len(set(ws[w_[0]:w_[1]])) <= MAX_REPEATS]:
        if electrum_ok(ws[a:b]):
            return "seed_ok", f"Electrum {b - a} words", run, a, b
    if n - len(set(ws)) <= MAX_REPEATS:
        return "seed_unverified", f"{n} BIP39 words", run, 0, n
    return None


# ---------------------------------------------------------------------------------------------- sources
class Source:
    """Read access to a ZIP or a folder: members {name: size}, open(name)."""

    def __init__(self, path):
        self.path = Path(path)
        self.zip = None
        if self.path.is_dir():
            self.members = {}
            for root, _, files in os.walk(self.path):
                for f in files:
                    p = Path(root, f)
                    try:
                        self.members[p.relative_to(self.path).as_posix()] = p.stat().st_size
                    except OSError:
                        pass
        else:
            self.zip = zipfile.ZipFile(self.path)
            self.members = {i.filename: i.file_size for i in self.zip.infolist() if not i.is_dir()}

    def open(self, name):
        return self.zip.open(name) if self.zip else open(self.path / name, "rb")

    def close(self):
        if self.zip:
            self.zip.close()


def layout(src):
    """-> (platform, {member: normalized path}); Cellebrite "Dump/", "filesystem1/", GrayKey "/" etc. stripped."""
    pre = Counter()
    for n in src.members:
        for a in ("data/data/", "private/var/"):
            k = n.find(a)
            if k >= 0 and (k == 0 or n[k - 1] == "/"):
                pre[(n[:k], a)] += 1
                break
    if pre:
        (prefix, anchor), _ = pre.most_common(1)[0]
        return ("ios" if anchor == "private/var/" else "android",
                {n: n[len(prefix):] if n.startswith(prefix) else n.lstrip("/") for n in src.members})
    mdb = sorted((n for n in src.members if n == "Manifest.db" or n.endswith("/Manifest.db")), key=len)
    if mdb:
        return "itunes", itunes_map(src, mdb[0])
    return "unknown", {n: n.lstrip("/") for n in src.members}


def itunes_map(src, mdb):
    """iTunes / Finder backup: hashed file names -> "<domain>/<relativePath>" (Manifest.db)."""
    root = mdb[:-len("Manifest.db")]
    with tempfile.TemporaryDirectory() as td:
        if src.zip:
            db = Path(td, "Manifest.db")
            with src.open(mdb) as s, open(db, "wb") as d:
                shutil.copyfileobj(s, d)
        else:
            db = src.path / mdb
        con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            rows = con.execute("SELECT fileID, domain, relativePath FROM Files WHERE flags = 1").fetchall()
        except sqlite3.DatabaseError as e:
            raise ValueError(f"Manifest.db not readable (encrypted backup?): {e}") from None
        finally:
            con.close()
    out = {n: n for n in src.members}
    for fid, dom, rel in rows:
        name = f"{root}{fid[:2]}/{fid}"
        if name in out:
            out[name] = f"{dom}/{rel}"
    return out


def ios_containers(src, paths):
    """iOS container UUID -> bundle id / app group (from the container metadata plists)."""
    out = {}
    for n, p in paths.items():
        if p.endswith("/" + IOS_META) and p.startswith("private/var/mobile/Containers/"):
            try:
                with src.open(n) as f:
                    ident = plistlib.loads(f.read()).get("MCMMetadataIdentifier")
                if ident:
                    out[p.split("/")[-2]] = ident
            except Exception:  # noqa: BLE001 - damaged plist: container stays unnamed
                pass
    return out


def app_of(path, uuids):
    """-> (app id, container path) for a normalized path, or ("", "")."""
    for r in APP_RES:
        m = r.match(path)
        if m:
            a = m.group(1)
            if len(a) == 36 and a.count("-") == 4:
                a = uuids.get(a, "")
            return a, m.group(0).rstrip("/")
    return "", ""


def wallet_app(app_id):
    """-> (name, "known" | "name") for wallet / exchange apps, else None."""
    a = re.sub(r"^(?:[A-Z0-9]{10}\.)?(?:group\.)?", "", app_id).lower()
    if not a:
        return None
    for k, name in KNOWN_APPS.items():
        if a == k.lower() or a.startswith(k.lower() + "."):
            return name, "known"
    if not a.startswith(APP_IGNORE) and APP_WORDS.search(a):
        return "", "name"
    return None


# ---------------------------------------------------------------------------------------------- scan
class Hits:
    """Findings, counted once per (kind, type, value, path)."""

    def __init__(self):
        self.d = {}

    def emitter(self, app, path):
        def emit(kind, typ, verified, value, offset, context):
            k = (kind, typ, value, path)
            if k in self.d:
                self.d[k]["count"] += 1
            else:
                w = wallet_app(app)
                self.d[k] = dict(kind=kind, type=typ, verified=verified, value=value, app=app,
                                 app_name=w[0] if w else "", path=path, offset=offset, count=1, context=context)
        return emit


def new_result(src, label):
    return dict(label=label, source=src[1], kind=src[0], platform="", entries=0, scanned_files=0, scanned_bytes=0,
                skipped_large=0, apps=[], findings=[], exported=[], errors=[], notes=[], seconds=0.0)


class Cancelled(Exception):
    pass


def scan_source(src, label, opts, log=None, cancel=None):
    """Scan one source ("zip" | "dir", path) or ("keychain", path) -> result dict.

    cancel: optional event (threading / multiprocessing); when set, the scan stops (partial result).
    """
    log = log or say
    t0 = time.time()
    r = new_result(src, label)
    hits = Hits()
    try:
        if src[0] == "keychain":
            scan_keychain(src[1], r, hits)
        else:
            scan_archive(src[1], label, opts, r, hits, log, cancel)
    except Cancelled as e:
        r["errors"].append(f"Cancelled at {e}")
    except Exception as e:  # noqa: BLE001 - damaged / unsupported source: reported, next one
        r["errors"].append(f"{type(e).__name__}: {e}")
    r["findings"] = sorted(hits.d.values(), key=lambda h: (h["kind"], h["type"], h["path"]))
    r["seconds"] = time.time() - t0
    return r


def scan_archive(path, label, opts, r, hits, log, cancel=None):
    src = Source(path)
    try:
        r["platform"], paths = layout(src)
        r["entries"] = len(paths)
        if r["platform"] == "ios":
            if any(p.startswith("extra/KeychainDump/") for p in paths.values()):
                r["notes"].append("keychain in the ZIP is encrypted (not scanned)")
        uuids = ios_containers(src, paths) if r["platform"] in ("ios", "unknown") else {}
        have = set(paths.values())
        roots = SCAN_ROOTS.get(r["platform"])
        apps, todo, export = {}, [], set()
        for name, p in paths.items():
            if p.startswith("data/user/0/") and "data/data/" + p[12:] in have:
                continue  # GrayKey: data/user/0 = data/data
            app, cont = app_of(p, uuids)
            w = wallet_app(app) if app else None
            if w:
                a = apps.setdefault(app, dict(app_id=app, name=w[0], match=w[1], files=0, bytes=0, locations=set()))
                a["files"] += 1
                a["bytes"] += src.members[name]
                a["locations"].add(cont)
                export.add(name)
            if roots and not p.startswith(roots):
                continue
            base = p.rsplit("/", 1)[-1]
            if WALLET_FILE_RE.match(base):
                hits.emitter(app, p)("wallet_file", "file name", "", base, "", "")
            ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
            if ext in SKIP_EXT or src.members[name] == 0:
                continue
            if src.members[name] > opts["max_size"] << 20:
                r["skipped_large"] += 1
                continue
            todo.append((name, p, app, ext))
        r["apps"] = sorted(apps.values(), key=lambda a: (a["match"], a["name"] or a["app_id"]))
        total = sum(src.members[n] for n, *_ in todo)
        log(f"[{label}] {r['platform']}: {len(paths):,} entries, {len(r['apps'])} wallet app(s), "
            f"scanning {len(todo):,} files ({fmt_size(total)}) ...")
        done, last, checked = 0, time.time(), time.time()
        for name, p, app, ext in todo:
            if cancel is not None and time.time() - checked > 1:
                checked = time.time()
                if cancel.is_set():
                    raise Cancelled(f"{done / max(total, 1):.0%}")
            try:
                r["scanned_bytes"] += scan_member(src, name, hits.emitter(app, p), ext)
                r["scanned_files"] += 1
            except Exception as e:  # noqa: BLE001 - one unreadable member: note it, go on
                r["errors"].append(f"{p}: {type(e).__name__}: {e}")
            done += src.members[name]
            if time.time() - last > 5:
                last = time.time()
                log(f"[{label}] {done / max(total, 1):.0%} ({fmt_size(done)} / {fmt_size(total)})")
        if opts.get("export"):
            by_path = {p: n for n, p in paths.items()}
            export |= {by_path[h["path"]] for h in hits.d.values() if h["kind"] in EXPORT_KINDS and h["path"] in by_path}
            export_files(src, paths, sorted(export), Path(opts["out"], "files", label), r)
    finally:
        src.close()


def scan_member(src, name, emit, ext=""):
    """Scan one file in overlapping chunks -> bytes scanned (0: skipped by magic).

    ext: extension of the normalized path (iTunes backups: member names have none). Office documents
    are opened (their text is searched instead of the ZIP), HTML is searched with and without tags.
    """
    with src.open(name) as f:
        buf = f.read(CHUNK)
        if ext in OFFICE_EXT and buf.startswith(b"PK\x03\x04"):
            buf += f.read()
            scan_office(buf, emit, lambda n, p: f"{n}:{p}")
            return len(buf)
        if buf.startswith(SKIP_MAGIC) or buf[4:8] == b"ftyp":
            return 0
        if ext in HTML_EXT and src.members[name] <= DOC_MAX:
            buf += f.read()  # whole file: the raw scan below takes it as one chunk
            t = strip_markup(buf)
            scan_bytes(t, 0, len(t), emit, lambda p: f"text:{p}", 1)
        size, base, first = len(buf), 0, True
        while True:
            nxt = f.read(CHUNK)
            hi = len(buf) if not nxt else len(buf) - OVERLAP + GUARD
            scan_bytes(buf, 0 if first else GUARD, hi, emit, lambda p, b=base: b + p)
            if not nxt:
                return size
            size += len(nxt)
            base += len(buf) - OVERLAP
            buf, first = buf[-OVERLAP:] + nxt, False


def scan_keychain(path, r, hits):
    """Decrypted keychain plist (GrayKey *_keychain.plist): wallet items + seeds/keys in all values."""
    with open(path, "rb") as f:
        kc = plistlib.load(f)
    if not isinstance(kc, dict) or not any(k in kc for k in ("genp", "inet")):
        raise ValueError("unknown keychain format (encrypted?)")
    r["platform"] = "keychain"
    apps = {}

    def s(v):
        return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v or "")

    for table in ("genp", "inet"):
        for it in kc.get(table) or []:
            r["entries"] += 1
            agrp, svce, acct = s(it.get("agrp")), s(it.get("svce") or it.get("srvr")), s(it.get("acct"))
            data = it.get("v_Data") or b""
            data = data if isinstance(data, bytes) else s(data).encode()
            app = re.sub(r"^[A-Z0-9]{10}\.", "", agrp)
            label = f"keychain/{table}/{it.get('rowid', '')} agrp={agrp} svce={svce} acct={acct}"
            emit = hits.emitter(app, label)
            w = wallet_app(app)
            if not w:  # service name: known apps only (e.g. svce "com.google.crypto.tink" is no wallet)
                w = wallet_app(svce)
                w = w if w and w[1] == "known" else None
            if w and data:
                a = apps.setdefault(app, dict(app_id=app, name=w[0], match=w[1], files=0, bytes=0, locations={"keychain"}))
                a["files"] += 1
                a["bytes"] += len(data)
                txt = data.decode("utf-8", "replace")
                value = txt[:1000] if data and txt.isprintable() else "hex:" + data[:1000].hex()
                emit("keychain", table, "", value, "", f"svce={svce} acct={acct}")
            if data:
                scan_bytes(data, 0, len(data), emit, lambda p: p)
                r["scanned_files"] += 1
                r["scanned_bytes"] += len(data)
    r["apps"] = sorted(apps.values(), key=lambda a: (a["match"], a["name"] or a["app_id"]))


def safe_path(p):
    parts = [re.sub(r'[<>:"|?*\x00-\x1f]', "_", x).rstrip(". ") or "_" for x in p.split("/") if x not in ("", ".", "..")]
    return Path(*parts) if parts else Path("_")


def export_files(src, paths, names, out, r):
    for name in names:
        dest = out / safe_path(paths[name])
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            h, size = hashlib.sha256(), 0
            with src.open(name) as s, open(dest, "wb") as d:
                for blk in iter(lambda: s.read(1 << 20), b""):
                    h.update(blk)
                    d.write(blk)
                    size += len(blk)
            r["exported"].append(dict(member=name, exported=str(dest), size=size, sha256=h.hexdigest()))
        except Exception as e:  # noqa: BLE001
            r["errors"].append(f"export {paths[name]}: {type(e).__name__}: {e}")


def export_later(r, out, paths=(), app=""):
    """After a scan (GUI): export files of one source like --export, into out/files/<label>/, with their
    SHA-256 appended to basil_files.csv. paths: normalized paths (the "path" of findings); app: also all
    files of this app / container id. Files already listed in basil_files.csv are skipped.
    -> dict(exported=[...], errors=[...], skipped=n)."""
    if r["kind"] == "keychain":
        raise ValueError("a keychain plist has no files to export")
    out = Path(out)
    csv_path = out / "basil_files.csv"
    done = set()
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            done = {row["member"] for row in csv.DictReader(f, delimiter=";") if row["label"] == r["label"]}
    src = Source(r["source"])
    try:
        platform, pm = layout(src)
        have = set(pm.values())
        want = set(paths)
        uuids = ios_containers(src, pm) if app and platform in ("ios", "unknown") else {}
        names = set()
        for n, p in pm.items():
            if p.startswith("data/user/0/") and "data/data/" + p[12:] in have:
                continue  # GrayKey duplicate (as in the scan)
            if p in want or app and app_of(p, uuids)[0] == app:
                names.add(n)
        todo = sorted(n for n in names if n not in done)
        res = dict(exported=[], errors=[], skipped=len(names) - len(todo))
        export_files(src, pm, todo, out / "files" / r["label"], res)
    finally:
        src.close()
    new = not csv_path.exists() or not csv_path.stat().st_size
    with open(csv_path, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:  # one BOM only
        w = csv.DictWriter(f, CSV_COLS["files"], delimiter=";", extrasaction="ignore")
        if new:
            w.writeheader()
        for e in res["exported"]:
            w.writerow(dict(e, label=r["label"], source=r["source"]))
    r["exported"] += res["exported"]
    return res


# ---------------------------------------------------------------------------------------------- run
def collect(paths, recursive=False, dump=False, exclude=None, progress=None, cancel=None):
    """Inputs -> [(kind, path)]: ZIPs, iTunes backup folders, *keychain*.plist; folders searched (-r: deep).

    progress: optional callback, called about every second with a status text (large folder trees).
    cancel: optional event; when set, the search stops (-> what was found so far).
    """
    out, seen = [], set()
    exclude = Path(exclude).resolve() if exclude else None
    n_dirs, last = 0, time.time()

    def add(kind, p):
        k = Path(p).resolve()
        if k not in seen:
            seen.add(k)
            out.append((kind, str(p)))

    def file_kind(p):
        n = p.name.lower()
        if n.endswith(".zip"):
            return "zip"
        if n.endswith(".plist") and "keychain" in n:
            return "keychain"
        return None

    for p in map(Path, paths):
        if p.is_file():
            if p.name == "Manifest.db":
                add("dir", p.parent)
            elif file_kind(p):
                add(file_kind(p), p)
        elif p.is_dir():
            if dump or (p / "Manifest.db").is_file():
                add("dir", p)
                continue
            for root, dirs, files in os.walk(p):
                rp = Path(root)
                dirs.sort()
                n_dirs += 1
                if time.time() - last > 1:
                    last = time.time()
                    if cancel is not None and cancel.is_set():
                        return out
                    if progress:
                        progress(f"Searching inputs… {n_dirs:,} folders, {len(out)} extraction(s) found  ({rp})")
                if exclude and rp.resolve() == exclude:
                    dirs[:] = []
                    continue
                if rp != p and (rp / "Manifest.db").is_file():
                    add("dir", rp)
                    dirs[:] = []
                    continue
                for f in sorted(files):
                    if file_kind(rp / f):
                        add(file_kind(rp / f), rp / f)
                if not recursive:
                    dirs[:] = []
    return out


def default_jobs():
    return max(1, min(4, os.cpu_count() or 1))


def _worker(src, label, opts, q, cancel):
    return scan_source(src, label, opts, q.put, cancel)


def scan_all(sources, labels, opts, jobs, log, cancel=None):
    """Yield results as they finish; jobs > 1: in parallel processes. cancel: optional threading.Event."""
    if jobs <= 1 or len(sources) <= 1:
        for s, lb in zip(sources, labels):
            if cancel is not None and cancel.is_set():
                return
            yield scan_source(s, lb, opts, log, cancel)
        return
    import multiprocessing
    import queue
    from concurrent.futures import ProcessPoolExecutor, wait
    ctx = multiprocessing.get_context("spawn")  # safe with the GUI thread and in PyInstaller builds
    with ctx.Manager() as m, ProcessPoolExecutor(min(jobs, len(sources)), mp_context=ctx) as ex:
        q, ev = m.Queue(), m.Event()  # ev: cancel, shared with the worker processes
        pending = {ex.submit(_worker, s, lb, opts, q, ev) for s, lb in zip(sources, labels)}
        while pending:
            if cancel is not None and cancel.is_set() and not ev.is_set():
                ev.set()
                for f in pending:
                    f.cancel()  # not started yet
            done, pending = wait(pending, timeout=0.5)
            try:
                while True:
                    log(q.get_nowait())
            except queue.Empty:
                pass
            for f in done:
                if not f.cancelled():
                    yield f.result()


def counts(r):
    f = r["findings"]
    c = Counter()
    for h in f:
        k = h["kind"]
        if k == "seed":
            c["seeds_verified" if h["verified"] == "yes" else "seeds_unverified"] += 1
        elif k == "private_key":
            c["private_keys"] += 1
        elif k == "xpub":
            c["xpubs"] += 1
        elif k == "address":
            c["addresses_verified" if h["verified"] == "yes" else "addresses_eth"] += 1
        elif k in ("wallet_file", "keychain"):
            c[k + ("s" if k == "wallet_file" else "_items")] += 1
    return c


def say(m):
    print(m, flush=True)


def fmt_size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def format_result(r):
    c = counts(r)
    out = [f"[{r['label']}] {r['source']}"]
    out += [f"    ! {e}" for e in r["errors"][:10]]
    if len(r["errors"]) > 10:
        out.append(f"    ! ... {len(r['errors']) - 10} more errors (see summary CSV)")
    out += [f"    i {n}" for n in r["notes"]]
    out.append(f"    {r['platform'] or r['kind']}: {r['entries']:,} entries, scanned {r['scanned_files']:,} files "
               f"({fmt_size(r['scanned_bytes'])}) in {r['seconds']:.0f} s"
               + (f", {r['skipped_large']} too large" if r["skipped_large"] else ""))
    if r["apps"]:
        out.append("    Wallet apps:")
        out += [f"      - {a['name'] or '(possible)'} {a['app_id']}: {a['files']:,} files, {fmt_size(a['bytes'])}"
                for a in r["apps"]]
    else:
        out.append("    Wallet apps: none")
    addr = Counter(h["type"] for h in r["findings"] if h["kind"] == "address")
    out.append(f"    Seeds: {c['seeds_verified']} with checksum, {c['seeds_unverified']} without · "
               f"Private keys: {c['private_keys']} · xpubs: {c['xpubs']} · Wallet files: {c['wallet_files']} · "
               f"Keychain items: {c['keychain_items']}")
    out.append("    Addresses: " + (", ".join(f"{k} {v}" for k, v in sorted(addr.items())) or "none"))
    if r["exported"]:
        out.append(f"    Exported: {len(r['exported']):,} files")
    return "\n".join(out)


def run(paths, out, recursive=False, dump=False, export=False, jobs=1, max_size=MAX_SIZE_MB, log=None,
        on_result=None, cancel=None, sources=None):
    """Scan all inputs, write the CSVs to out -> exit code (0 nothing found, 1 found, 2 errors).

    on_result: optional callback, called with every result dict (GUI).
    cancel: optional threading.Event; when set, running scans stop and no new ones start.
    sources: result of collect() when the caller already searched the inputs (GUI), else searched here.
    """
    log = log or say
    out = Path(out)
    if sources is None:
        sources = collect(paths, recursive, dump, exclude=out)
    if not sources:
        log("No extractions found (ZIP, iTunes backup folder, *keychain*.plist; folders: -r for subfolders).")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    labels = [f"{i + 1:02d}_{safe_path(Path(s[1]).parent.name + '_' + Path(s[1]).stem).name}"
              for i, s in enumerate(sources)]
    opts = dict(out=str(out), export=export, max_size=max_size)
    log(f"BASIL {VERSION}: {len(sources)} source(s) -> {out}")
    files = {k: open(out / f"basil_{k}.csv", "w", newline="", encoding="utf-8-sig") for k in CSV_COLS}
    code = 0
    try:
        w = {k: csv.DictWriter(f, CSV_COLS[k], delimiter=";", extrasaction="ignore") for k, f in files.items()}
        for x in w.values():
            x.writeheader()
        for r in scan_all(sources, labels, opts, jobs, log, cancel):
            c = counts(r)
            base = dict(label=r["label"], source=r["source"])
            w["summary"].writerow(dict(r, **c, wallet_apps=len(r["apps"]), exported_files=len(r["exported"]),
                                       errors=" | ".join(r["errors"]), notes=" | ".join(r["notes"]),
                                       seconds=round(r["seconds"]), version=VERSION, tool=SIGNATURE))
            for h in r["findings"]:
                w["findings"].writerow(dict(h, **base))
            for a in r["apps"]:
                w["apps"].writerow(dict(a, **base, platform=r["platform"], locations=" | ".join(sorted(a["locations"]))))
            for e in r["exported"]:
                w["files"].writerow(dict(e, **base))
            for f in files.values():
                f.flush()
            log(format_result(r))
            if on_result:
                on_result(r)
            found = r["apps"] or any(h["kind"] != "address" or h["verified"] == "yes" for h in r["findings"])
            code = max(code, 2 if r["errors"] else 1 if found else 0)
    finally:
        for f in files.values():
            f.close()
    if cancel is not None and cancel.is_set():
        log("Stopped - the CSVs contain the results up to here.")
    log(f"Results: {out}  (findings with values only in basil_findings.csv)")
    return code


# ---------------------------------------------------------------------------------------------- GUI
NONE, HINTS, KEYS = 0, 1, 2  # result level: nothing / wallet hints / seeds with checksum or private keys


def level(r):
    c = counts(r)
    if c["seeds_verified"] or c["private_keys"]:
        return KEYS
    if r["apps"] or any(c[k] for k in ("seeds_unverified", "xpubs", "addresses_verified", "wallet_files",
                                       "keychain_items")):
        return HINTS
    return NONE


def open_folder(path):
    """Open a folder in the system's file manager."""
    import subprocess
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
        return
    env = dict(os.environ)
    if getattr(sys, "frozen", False):  # PyInstaller: give the file manager the system libraries back
        orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
        env.pop("LD_LIBRARY_PATH", None)
        if orig:
            env["LD_LIBRARY_PATH"] = orig
    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)], env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gui():
    import queue
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter import font as tkfont

    try:  # optional: drag & drop (pip install tkinterdnd2)
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd = True
    except Exception:  # noqa: BLE001
        root = tk.Tk()
        dnd = False

    C = {
        "bg": "#f3f5f8", "card": "#ffffff", "head": "#1e293b", "head_sub": "#94a3b8",
        "text": "#1e293b", "muted": "#64748b", "border": "#d8dee6",
        "accent": "#2563eb", "accent_hover": "#1d4ed8", "accent_off": "#9db7f2",
        "drop": "#f5f8ff", "drop_active": "#dbe7ff",
        "ok": "#15803d", "ok_bg": "#eaf6ee", "bad": "#b91c1c", "bad_bg": "#fdeceb",
        "warn": "#a16207", "warn_bg": "#fff6dd", "err": "#475569", "err_bg": "#eef1f5",
    }
    root.title(f"BASIL {VERSION}")
    root.configure(bg=C["bg"])

    base = tkfont.nametofont("TkDefaultFont")
    base.configure(size=10, family="Segoe UI" if sys.platform == "win32" else base.actual("family"))
    scale = max(1.0, base.metrics("linespace") / 17)  # HiDPI

    def px(n):
        return int(round(n * scale))

    w, h = min(px(1280), int(root.winfo_screenwidth() * 0.9)), min(px(780), int(root.winfo_screenheight() * 0.9))
    root.geometry(f"{w}x{h}")
    root.minsize(min(px(780), w), min(px(560), h))
    for name in ("TkTextFont", "TkHeadingFont", "TkMenuFont"):
        tkfont.nametofont(name).configure(family=base.actual("family"), size=10)
    bold = tkfont.Font(root, family=base.actual("family"), size=10, weight="bold")
    mono = tkfont.nametofont("TkFixedFont").copy()
    mono.configure(size=10)

    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", background=C["bg"], foreground=C["text"], bordercolor=C["border"], focuscolor=C["accent"])
    st.configure("Card.TFrame", background=C["card"])
    st.configure("TScrollbar", arrowsize=px(13))
    st.configure("TEntry", padding=px(3))
    st.configure("Card.TLabel", background=C["card"])
    st.configure("Title.TLabel", background=C["card"], font=bold)
    st.configure("Muted.TLabel", background=C["card"], foreground=C["muted"])
    st.configure("Status.TLabel", foreground=C["muted"])
    st.configure("TCheckbutton", background=C["card"], indicatorsize=px(13), indicatormargin=(0, 0, px(6), 0))
    st.map("TCheckbutton", background=[("active", C["card"])])
    st.configure("TButton", padding=(px(10), px(4)), background="#eef1f5", lightcolor="#eef1f5", darkcolor="#eef1f5")
    st.map("TButton", background=[("active", "#e2e7ee")])
    st.configure("Accent.TButton", padding=(px(22), px(6)), font=bold, foreground="white", background=C["accent"],
                 lightcolor=C["accent"], darkcolor=C["accent"], bordercolor=C["accent"])
    st.map("Accent.TButton",
           background=[("disabled", C["accent_off"]), ("active", C["accent_hover"])],
           lightcolor=[("disabled", C["accent_off"]), ("active", C["accent_hover"])],
           darkcolor=[("disabled", C["accent_off"]), ("active", C["accent_hover"])],
           foreground=[("disabled", "white")])
    st.configure("Treeview", rowheight=px(28), background=C["card"], fieldbackground=C["card"], borderwidth=0)
    st.configure("Treeview.Heading", font=bold, background="#e9edf2", relief="flat", padding=(px(6), px(4)))
    st.map("Treeview", background=[], foreground=[])  # a selected row keeps its color (stronger tag)
    st.configure("Horizontal.TProgressbar", troughcolor="#e2e7ee", background=C["accent"],
                 lightcolor=C["accent"], darkcolor=C["accent"], bordercolor="#e2e7ee", thickness=px(6))

    inputs, results, events = [], [], queue.Queue()
    opt = {k: tk.BooleanVar(value=k == "recursive") for k in ("recursive", "dump", "export")}
    jobs = tk.IntVar(value=default_jobs())
    max_size = tk.IntVar(value=MAX_SIZE_MB)
    out_parent = tk.StringVar()
    last_out = []
    status = tk.StringVar(value="Ready.")

    def card(parent, title=None, **pack):
        outer = tk.Frame(parent, bg=C["border"])  # 1px border
        outer.pack(**pack)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=px(12))
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        if title:
            ttk.Label(inner, text=title, style="Title.TLabel").pack(anchor="w", pady=(0, px(8)))
        return inner

    # ---- header
    head = tk.Frame(root, bg=C["head"])
    head.pack(fill="x")
    logo_pad = px(18)
    try:  # logo: window icon + header
        logo = tk.PhotoImage(data=ICON_PNG)
        root.iconphoto(True, logo)
        small = logo if scale >= 1.5 else logo.subsample(2)
        tk.Label(head, image=small, bg=C["head"]).pack(side="left", padx=(px(16), 0))
        root.logo_refs = (logo, small)  # keep the images alive
        logo_pad = px(10)
    except tk.TclError:
        pass
    tk.Label(head, text="BASIL", bg=C["head"], fg="white",
             font=(base.actual("family"), 17, "bold")).pack(side="left", padx=(logo_pad, px(12)), pady=px(12))
    tk.Label(head, text=f"Blockchain Assets, Seeds, Identifiers & Ledgers {VERSION}  ·  in mobile extractions",
             bg=C["head"], fg=C["head_sub"]).pack(side="left", pady=(px(6), 0))

    body = tk.Frame(root, bg=C["bg"])
    body.pack(fill="both", expand=True, padx=px(14), pady=px(12))

    # ---- input card: drop zone + list
    cin = card(body, "Input", fill="x")
    row = ttk.Frame(cin, style="Card.TFrame")
    row.pack(fill="x")
    row.columnconfigure(0, weight=3, uniform="in")
    row.columnconfigure(1, weight=2, uniform="in")
    drop = tk.Canvas(row, height=px(110), bg=C["drop"], highlightthickness=0, cursor="hand2")
    drop.grid(row=0, column=0, sticky="nsew", padx=(0, px(10)))
    drop_hint = "Drop extractions (ZIP, folders, keychain plist) here" if dnd else \
        "Drag & drop needs: pip install tkinterdnd2"

    def draw_drop(active=False):
        drop.delete("all")
        w, h = drop.winfo_width(), drop.winfo_height()
        drop.configure(bg=C["drop_active"] if active else C["drop"])
        m = px(4)
        drop.create_rectangle(m, m, w - m, h - m, outline=C["accent"], dash=(px(6), px(4)), width=max(1, px(1.5)))
        line = bold.metrics("linespace")
        drop.create_text(w / 2, h / 2 - line * 0.6, text="⇩  " + drop_hint, fill=C["accent"], font=bold)
        drop.create_text(w / 2, h / 2 + line * 0.6, text="or click to choose files", fill=C["muted"])

    drop.bind("<Configure>", lambda e: draw_drop())
    lst_frame = tk.Frame(row, bg=C["border"])
    lst_frame.grid(row=0, column=1, sticky="nsew")
    lst = tk.Listbox(lst_frame, height=4, selectmode="extended", relief="flat", borderwidth=0, highlightthickness=0,
                     activestyle="none", selectbackground=C["accent"], font=base, bg=C["card"])
    lst.pack(fill="both", expand=True, padx=1, pady=1)
    btns = ttk.Frame(cin, style="Card.TFrame")
    btns.pack(fill="x", pady=(px(10), 0))

    def add(paths):
        for p in paths:
            if p and p not in inputs:
                inputs.append(p)
                lst.insert("end", ("📁  " if Path(p).is_dir() else "📄  ") + p)
                if not out_parent.get():
                    out_parent.set(str(Path(p).parent))
        status.set(f"{len(inputs)} input(s) selected.")

    def add_files(_=None):
        add(filedialog.askopenfilenames(title="Select extractions", filetypes=[
            ("Extractions", "*.zip *.ZIP *.plist Manifest.db"), ("All files", "*")]))

    def remove():
        for i in reversed(lst.curselection()):
            lst.delete(i)
            del inputs[i]

    def clear():
        lst.delete(0, "end")
        inputs.clear()

    drop.bind("<Button-1>", add_files)
    for text, cmd in (("Add files…", add_files),
                      ("Add folder…", lambda: add([filedialog.askdirectory(title="Select folder")]))):
        ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=(0, px(6)))
    for text, cmd in (("Clear", clear), ("Remove selected", remove)):
        ttk.Button(btns, text=text, command=cmd).pack(side="right", padx=(px(6), 0))
    if dnd:
        def on_drop(event):
            add(root.tk.splitlist(event.data))
            draw_drop()
            return event.action

        for wdg in (drop, lst):
            wdg.drop_target_register(DND_FILES)
            wdg.dnd_bind("<<Drop>>", on_drop)
            wdg.dnd_bind("<<DropEnter>>", lambda e: (draw_drop(True), e.action)[1])
            wdg.dnd_bind("<<DropLeave>>", lambda e: (draw_drop(), e.action)[1])

    # ---- options card
    copt = card(body, fill="x", pady=(px(10), 0))
    r1 = ttk.Frame(copt, style="Card.TFrame")
    r1.pack(fill="x", pady=(0, px(10)))
    ttk.Label(r1, text="Output folder", style="Muted.TLabel").pack(side="left", padx=(0, px(8)))
    ttk.Entry(r1, textvariable=out_parent).pack(side="left", fill="x", expand=True)
    ttk.Button(r1, text="…", width=3, command=lambda: out_parent.set(
        filedialog.askdirectory(title="Output folder") or out_parent.get())).pack(side="left", padx=(px(4), 0))
    ttk.Label(r1, text="(a basil_<date>_<time> folder is created in it)",
              style="Muted.TLabel").pack(side="left", padx=px(8))
    btn_exp = ttk.Button(r1, text="Open export folder", state="disabled")
    btn_exp.pack(side="right")
    btn_open = ttk.Button(r1, text="Open output folder", state="disabled")
    btn_open.pack(side="right", padx=px(8))
    r2 = ttk.Frame(copt, style="Card.TFrame")
    r2.pack(fill="x")
    ttk.Checkbutton(r2, text="Include subfolders", variable=opt["recursive"]).pack(side="left")
    ttk.Checkbutton(r2, text="Folders are extracted file systems", variable=opt["dump"]).pack(side="left", padx=px(14))
    ttk.Checkbutton(r2, text="Export files of wallet apps and hits (SHA-256)", variable=opt["export"]).pack(side="left")
    ttk.Label(r2, text="Parallel", style="Muted.TLabel").pack(side="left", padx=(px(20), px(6)))
    ttk.Spinbox(r2, from_=1, to=32, textvariable=jobs, width=3).pack(side="left")
    ttk.Label(r2, text="Max. file MB", style="Muted.TLabel").pack(side="left", padx=(px(20), px(6)))
    ttk.Spinbox(r2, from_=1, to=1000000, textvariable=max_size, width=6).pack(side="left")
    btn_run = ttk.Button(r2, text="▶  Run", style="Accent.TButton")
    btn_run.pack(side="right")
    btn_stop = ttk.Button(r2, text="■  Stop", state="disabled")
    btn_stop.pack(side="right", padx=px(8))
    cancel = threading.Event()

    # ---- progress + status
    prog = ttk.Progressbar(body, mode="determinate")
    prog.pack(fill="x", pady=(px(12), px(2)))
    ttk.Label(body, textvariable=status, style="Status.TLabel").pack(anchor="w")
    runbox = tk.Frame(body, bg=C["bg"])  # one row per running scan
    runbox.pack(fill="x")
    running = {}  # label -> dict(row, bar, text, start, frac)
    st.configure("Run.Horizontal.TProgressbar", troughcolor="#e2e7ee", background="#60a5fa",
                 lightcolor="#60a5fa", darkcolor="#60a5fa", bordercolor="#e2e7ee", thickness=px(4))
    re_start = re.compile(r"^\[(.+?)\] .*, scanning [\d,]+ files \((.*)\) \.\.\.$")
    re_prog = re.compile(r"^\[(.+?)\] (\d+)% \((.*)\)$")

    def fmt_eta(s):
        return f"{s / 60:.0f} min" if s >= 90 else f"{s:.0f} s"

    def set_running(label, frac=0.0, size=""):
        if label not in running:
            row = tk.Frame(runbox, bg=C["bg"])
            row.pack(fill="x", pady=(px(2), 0))
            tk.Label(row, text=label, bg=C["bg"], fg=C["text"], anchor="w", width=34).pack(side="left")
            bar = ttk.Progressbar(row, mode="determinate", maximum=100, length=px(220),
                                  style="Run.Horizontal.TProgressbar")
            bar.pack(side="left", padx=px(8))
            text = tk.StringVar()
            tk.Label(row, textvariable=text, bg=C["bg"], fg=C["muted"], anchor="w").pack(side="left")
            running[label] = dict(row=row, bar=bar, text=text, start=time.time(), frac=0.0, size=size)
        e = running[label]
        e["frac"] = frac
        e["size"] = size or e["size"]
        e["bar"]["value"] = frac * 100
        el = time.time() - e["start"]
        eta = f"  ·  ≈ {fmt_eta(el * (1 - frac) / frac)} left" if 0.02 < frac < 1 and el > 10 else ""
        e["text"].set(f"{frac:.0%}  ·  {e['size']}{eta}")

    def update_overall():
        total = int(prog["maximum"]) // 100 or 1
        prog["value"] = (len(results) + sum(e["frac"] for e in running.values())) * 100
        status.set(("Stopping…  ·  " if cancel.is_set() else "") + f"{len(results)}/{total} done  ·  {len(running)} running")

    # ---- results card: table + details
    cres = card(body, "Results", fill="both", expand=True, pady=(px(8), 0))
    pane = ttk.PanedWindow(cres, orient="vertical")
    pane.pack(fill="both", expand=True)
    tframe = ttk.Frame(pane, style="Card.TFrame")
    cols = (("light", "Result", 110, "w"), ("file", "Source", 240, "w"), ("plat", "Type", 80, "center"),
            ("apps", "Wallet apps", 95, "center"), ("seed", "Seeds ✓", 75, "center"),
            ("seedq", "Seeds ?", 70, "center"), ("keys", "Priv. keys", 80, "center"),
            ("xpub", "xpubs", 60, "center"), ("addr", "Addresses", 85, "center"),
            ("wf", "Wallet files", 90, "center"), ("kc", "Keychain", 75, "center"), ("note", "Apps", 300, "w"))
    tree = ttk.Treeview(tframe, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=7)
    for cid, title, width, anchor in cols:
        tree.heading(cid, text=title, anchor=anchor)
        tree.column(cid, width=px(width), anchor=anchor, stretch=cid in ("file", "note"))
    styles = {NONE: (C["ok_bg"], C["ok"], "#bfe6cb", "#0f5f2a"), HINTS: (C["warn_bg"], C["warn"], "#fde58a", "#7a4a00"),
              KEYS: (C["bad_bg"], C["bad"], "#f8c4c0", "#991b1b"), "E": (C["err_bg"], C["err"], "#d5dbe3", "#1e293b")}
    for k, (bg, fg, sel_bg, sel_fg) in styles.items():
        tree.tag_configure(f"L{k}", background=bg, foreground=fg)
        tree.tag_configure(f"L{k}s", background=sel_bg, foreground=sel_fg, font=bold)
    tsb = ttk.Scrollbar(tframe, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tframe, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=tsb.set, xscrollcommand=hsb.set)
    tframe.rowconfigure(0, weight=1)
    tframe.columnconfigure(0, weight=1)
    tree.grid(row=0, column=0, sticky="nsew")
    tsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    pane.add(tframe, weight=3)
    nb = ttk.Notebook(pane)
    dframe = ttk.Frame(nb, style="Card.TFrame")
    detail = tk.Text(dframe, font=mono, relief="flat", wrap="none", height=8, bg="#fafbfc",
                     fg=C["text"], padx=px(10), pady=px(8), highlightthickness=0, state="disabled")
    dsb = ttk.Scrollbar(dframe, orient="vertical", command=detail.yview)
    detail.configure(yscrollcommand=dsb.set)
    for k, (_, fg, _, _) in styles.items():
        detail.tag_configure(k, foreground=fg, font=(mono.actual("family"), 10, "bold"))
    detail.pack(side="left", fill="both", expand=True)
    dsb.pack(side="right", fill="y")
    nb.add(dframe, text="Summary")
    fframe = ttk.Frame(nb, style="Card.TFrame")
    # filter bar: text in any column, kind, checksum only
    fbar = ttk.Frame(fframe, style="Card.TFrame")
    fbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(px(6), px(6)))
    f_text, f_kind, f_ok = tk.StringVar(), tk.StringVar(value="all kinds"), tk.BooleanVar()
    ttk.Label(fbar, text="Filter", style="Muted.TLabel").pack(side="left", padx=(0, px(6)))
    ttk.Entry(fbar, textvariable=f_text, width=40).pack(side="left")
    ttk.Combobox(fbar, textvariable=f_kind, state="readonly", width=14, values=(
        "all kinds", "seed", "private_key", "xpub", "address", "wallet_file", "keychain", "wordlist")).pack(
        side="left", padx=px(10))
    ttk.Checkbutton(fbar, text="Checksum ✓ only", variable=f_ok).pack(side="left")
    f_group = tk.BooleanVar(value=True)
    ttk.Checkbutton(fbar, text="Group by file", variable=f_group).pack(side="left", padx=(px(10), 0))
    f_info = tk.StringVar()
    ttk.Label(fbar, textvariable=f_info, style="Muted.TLabel").pack(side="left", padx=px(12))
    btn_fexp = ttk.Button(fbar, text="Export selected files")
    btn_fexp.pack(side="right")
    ttk.Label(fbar, text="double-click: copy cell / open group  ·  right-click: copy, export  ·  click heading: sort",
              style="Muted.TLabel").pack(side="right", padx=px(10))
    fcols = (("kind", "Kind", 95), ("type", "Type", 120), ("ver", "Checksum", 80), ("value", "Value", 420),
             ("app", "App", 160), ("path", "Path", 360), ("offset", "Offset", 90), ("count", "Count", 60))
    ftree = ttk.Treeview(fframe, columns=[c[0] for c in fcols], show="tree headings", selectmode="extended",
                         height=5)
    ftree.column("#0", width=px(34), minwidth=px(34), stretch=False)  # open / close of a file group
    for cid, title, width in fcols:
        ftree.heading(cid, text=title, anchor="w")
        ftree.column(cid, width=px(width), anchor="w", stretch=cid in ("value", "path"))
    ftree.tag_configure("group", font=bold)
    ftree.tag_configure("hot", foreground=C["bad"])
    ftree.tag_configure("warm", foreground=C["warn"])
    fsb = ttk.Scrollbar(fframe, orient="vertical", command=ftree.yview)
    fhb = ttk.Scrollbar(fframe, orient="horizontal", command=ftree.xview)
    ftree.configure(yscrollcommand=fsb.set, xscrollcommand=fhb.set)
    fframe.rowconfigure(1, weight=1)
    fframe.columnconfigure(0, weight=1)
    ftree.grid(row=1, column=0, sticky="nsew")
    fsb.grid(row=1, column=1, sticky="ns")
    fhb.grid(row=2, column=0, sticky="ew")
    nb.add(fframe, text="Findings")
    pane.add(nb, weight=2)
    root.after(300, lambda: pane.sashpos(0, int(pane.winfo_height() * 0.45)))  # table / details
    FIND_ORDER = {("seed", "yes"): 0, ("private_key", "yes"): 1, ("xpub", "yes"): 2, ("wallet_file", ""): 3,
                  ("keychain", ""): 4, ("seed", "no"): 5, ("wordlist", ""): 6, ("address", "yes"): 7}
    MAX_ROWS = 5000
    cur = {"hits": []}  # findings of the selected source

    def copy(text, what="Value"):
        root.clipboard_clear()
        root.clipboard_append(text)
        short = text if len(text) <= 80 else text[:77] + "…"
        status.set(f"{what} copied: {short}")

    def table_tools(tv, extra=None):
        """Copy (double-click cell, right-click menu, Ctrl+C row) and sort (click heading) for a Treeview.

        tv.full[iid]: full cell values (the display may be shortened); extra(iid): more menu entries
        (label, text to copy | function to call). Rows with children (groups): double-click opens / closes.
        """
        tv.full = {}
        heads = {c: tv.heading(c, "text") for c in tv["columns"]}
        menu = tk.Menu(root, tearoff=0)

        def row_of(iid):
            return [str(v) for v in tv.full.get(iid, tv.item(iid, "values"))]

        def cell_at(ev):
            iid, col = tv.identify_row(ev.y), tv.identify_column(ev.x)
            return (iid, int(col[1:]) - 1) if iid and col else (None, None)

        def on_double(ev):
            iid, ci = cell_at(ev)
            if iid and tv.get_children(iid):
                tv.item(iid, open=not tv.item(iid, "open"))
                return "break"  # no default toggle on top of it
            if iid and ci >= 0:
                copy(row_of(iid)[ci], heads[tv["columns"][ci]])

        def on_menu(ev):
            iid, ci = cell_at(ev)
            if not iid or ci < 0:
                return
            if iid not in tv.selection():  # keep a multiple selection
                tv.selection_set(iid)
            row, name = row_of(iid), heads[tv["columns"][ci]]
            menu.delete(0, "end")
            menu.add_command(label=f"Copy {name}: {row[ci][:50]}", command=lambda: copy(row[ci], name))
            menu.add_command(label="Copy row (tab-separated)", command=lambda: copy("\t".join(row), "Row"))
            for label, what in (extra(iid) if extra else []):
                if label is None:
                    menu.add_separator()
                elif callable(what):
                    menu.add_command(label=label, command=what)
                else:
                    menu.add_command(label=label, command=lambda t_=what, l_=label: copy(t_, l_))
            menu.tk_popup(ev.x_root, ev.y_root)

        def on_copy(_=None):
            sel = tv.selection()
            if sel:
                copy("\t".join(row_of(sel[0])), "Row")

        def sort_by(col, desc):
            ci = list(tv["columns"]).index(col)

            def key(iid):
                v = row_of(iid)[ci]
                try:
                    return 0, float(v.replace(",", "")), ""
                except ValueError:
                    return 1, 0.0, v.lower()
            for parent in ("",) + tv.get_children(""):  # top level, then inside each group
                for n, iid in enumerate(sorted(tv.get_children(parent), key=key, reverse=desc)):
                    tv.move(iid, parent, n)
            for c in tv["columns"]:
                tv.heading(c, text=heads[c] + ((" ▼" if desc else " ▲") if c == col else ""))
            tv.heading(col, command=lambda: sort_by(col, not desc))

        for c in tv["columns"]:
            tv.heading(c, command=lambda c=c: sort_by(c, False))
        tv.bind("<Double-1>", on_double)
        tv.bind("<Button-3>", on_menu)
        tv.bind("<Button-2>" if sys.platform == "darwin" else "<Control-Button-1>", on_menu)
        tv.bind("<Control-c>", on_copy)

    def heat(h):
        k = FIND_ORDER.get((h["kind"], h["verified"]), 9)
        return "hot" if k <= 1 else "warm" if k <= 5 else ""

    def refresh_findings(*_):
        ftree.delete(*ftree.get_children())
        ftree.full.clear()
        ftree.ctx.clear()
        ftree.hits.clear()
        q, kind, ok = f_text.get().strip().lower(), f_kind.get(), f_ok.get()
        shown = [h for h in cur["hits"]
                 if (kind == "all kinds" or h["kind"] == kind) and (not ok or h["verified"] == "yes")
                 and (not q or q in " ".join(str(h[k]) for k in ("kind", "type", "value", "app", "app_name", "path",
                                                                  "context")).lower())][:MAX_ROWS]
        groups = {}  # source file -> its findings (order: most important finding first, as sorted)
        for h in shown:
            groups.setdefault(h["path"], []).append(h)
        grouped = f_group.get()
        for g, (path, hs) in enumerate(groups.items()):
            parent = ""
            if grouped:
                parent = f"g{g}"
                kinds = Counter(h["kind"] + (" ✓" if h["verified"] == "yes" else "") for h in hs)
                summary = "  ·  ".join(f"{n:,} {k}" for k, n in kinds.most_common())
                full = (f"{len(hs):,} finding(s)", "file", "", summary, hs[0]["app_name"] or hs[0]["app"], path, "",
                        sum(h["count"] for h in hs))
                ftree.insert("", "end", iid=parent, open=len(groups) == 1, values=full,
                             tags=("group", next((t for t in ("hot", "warm") if any(heat(h) == t for h in hs)), "")))
                ftree.full[parent] = full
                ftree.hits[parent] = hs
            for h in hs:
                i = str(len(ftree.hits))
                full = (h["kind"], h["type"], {"yes": "✓", "no": "✗"}.get(h["verified"], ""), h["value"],
                        h["app_name"] or h["app"], h["path"], h["offset"], h["count"])
                ftree.insert(parent, "end", iid=i, tags=(heat(h),), values=full[:3] + (h["value"][:300],) + full[4:])
                ftree.full[i] = full
                ftree.ctx[i] = h["context"]
                ftree.hits[i] = [h]
        n = len(cur["hits"])
        f_info.set((f"{len(shown):,} of {n:,} shown" if len(shown) != n else "")
                   + (f"  in {len(groups):,} file(s)" if grouped and groups else "")
                   + (f"  (first {MAX_ROWS:,} listed - all in the CSV)" if len(shown) >= MAX_ROWS < n else ""))

    def show_findings(r):
        cur["r"] = r
        cur["hits"] = sorted(r["findings"], key=lambda h: (FIND_ORDER.get((h["kind"], h["verified"]), 9), h["path"]))
        nb.tab(fframe, text=f"Findings ({len(cur['hits']):,})")
        refresh_findings()

    # ---- export after the scan: files of selected findings / groups, or all files of an app
    exp_events = queue.Queue()

    def export_now(paths=(), app="", what=""):
        r = cur.get("r")
        if not r or not last_out:
            return
        if str(btn_run["state"]) == "disabled":
            status.set("Export: wait until the scan is finished.")
            return
        if r["kind"] == "keychain":
            status.set("Export: a keychain plist has no files to export.")
            return
        btn_fexp.configure(state="disabled")
        status.set(f"Exporting {what} …")

        def work():
            try:
                res = export_later(r, last_out[0], paths, app)
                exp_events.put(("ok", (res, what)))
            except Exception as e:  # noqa: BLE001
                exp_events.put(("err", f"{type(e).__name__}: {e}"))
        threading.Thread(target=work, daemon=True).start()
        export_poll()

    def export_poll():
        try:
            kind, data = exp_events.get_nowait()
        except queue.Empty:
            root.after(100, export_poll)
            return
        btn_fexp.configure(state="normal")
        if kind == "err":
            status.set(f"Export failed: {data}")
            return
        res, what = data
        dest = last_out[0] / "files" / cur["r"]["label"]
        status.set(f"Exported {what}: {len(res['exported'])} file(s) -> {dest}  (SHA-256 in basil_files.csv)"
                   + (f"  ·  {res['skipped']} already exported" if res["skipped"] else "")
                   + (f"  ·  {len(res['errors'])} error(s): {res['errors'][0]}" if res["errors"] else ""))
        if res["exported"]:
            btn_exp.configure(state="normal")

    def selected_paths(iids=None):
        return sorted({h["path"] for i in (iids or ftree.selection()) for h in ftree.hits.get(i, [])})

    def export_selected():
        paths = selected_paths()
        if not paths:
            status.set("Export: select findings or file groups first (Ctrl / Shift + click: several).")
            return
        export_now(paths=paths, what=f"{len(paths)} selected file(s)")

    def finding_menu(iid):
        items = [] if iid not in ftree.ctx else [("Copy context", ftree.ctx[iid])]
        r = cur.get("r")
        if not r or r["kind"] == "keychain":
            return items
        paths = selected_paths()
        hs = ftree.hits.get(iid, [])
        items += [(None, None), (f"Export {'file' if len(paths) == 1 else f'{len(paths)} files'} (selection)",
                                 export_selected)]
        app = hs[0]["app"] if hs else ""
        if app:
            name = hs[0]["app_name"] or app
            items.append((f"Export all files of app {name}",
                          lambda: export_now(app=app, what=f"all files of {name}")))
        return items

    btn_fexp.configure(command=export_selected)
    table_tools(ftree, extra=finding_menu)
    ftree.ctx, ftree.hits = {}, {}
    for v in (f_text, f_kind, f_ok, f_group):
        v.trace_add("write", refresh_findings)

    def tag_of(r):
        return "E" if r["errors"] and not r["scanned_files"] else level(r)

    def show_detail(text, tag=None):
        detail.configure(state="normal")
        detail.delete("1.0", "end")
        first, _, rest = text.partition("\n")
        detail.insert("end", first + "\n", tag)
        detail.insert("end", rest)
        detail.configure(state="disabled")

    def on_select(_=None):
        sel = tree.selection()
        for iid in tree.get_children():
            t = tag_of(results[int(iid)])
            tree.item(iid, tags=(f"L{t}s" if iid in sel else f"L{t}",))
        if sel:
            r = results[int(sel[0])]
            show_detail(format_result(r), tag_of(r))
            show_findings(r)
            if level(r) == KEYS:
                nb.select(fframe)

    tree.bind("<<TreeviewSelect>>", on_select)
    table_tools(tree)
    show_detail("Select a row to see details.")

    def add_row(i, r):
        c = counts(r)
        t = tag_of(r)
        light = {NONE: "●  NOTHING", HINTS: "●  HINTS", KEYS: "●  SEEDS/KEYS", "E": "●  ERROR"}[t]
        apps = ", ".join(dict.fromkeys(a["name"] or a["app_id"] for a in r["apps"]))
        pos = sum(x["label"] < r["label"] for x in results)  # input order, also with parallel scans
        values = [light.split()[-1], r["source"], r["platform"] or r["kind"], len(r["apps"]),
                  c["seeds_verified"], c["seeds_unverified"], c["private_keys"], c["xpubs"],
                  c["addresses_verified"] + c["addresses_eth"], c["wallet_files"], c["keychain_items"],
                  apps or ("; ".join(r["errors"]) if t == "E" else "")]
        tree.full[str(i)] = values
        tree.insert("", pos, iid=str(i), tags=(f"L{t}",), values=[light, Path(r["source"]).name] + values[2:])

    # ---- run
    def run_clicked():
        if not inputs:
            status.set("No inputs: add ZIPs, folders or a keychain plist.")
            return
        tree.delete(*tree.get_children())
        results.clear()
        show_detail("Select a row to see details.")
        cur["hits"], cur["r"] = [], None
        refresh_findings()
        tree.full.clear()
        nb.tab(fframe, text="Findings")
        parent = out_parent.get().strip() or filedialog.askdirectory(title="Output folder")
        if not parent:
            status.set("Cancelled: no output folder chosen.")
            return
        out_parent.set(parent)
        out = Path(parent) / time.strftime("basil_%Y%m%d_%H%M%S")
        last_out[:] = [out]
        try:
            n_jobs, mb = max(1, int(jobs.get())), max(1, int(max_size.get()))
        except (tk.TclError, ValueError):
            n_jobs, mb = default_jobs(), MAX_SIZE_MB
            jobs.set(n_jobs)
            max_size.set(mb)
        prog.configure(maximum=100, value=0)
        for b in (btn_run, btn_open, btn_exp):
            b.configure(state="disabled")
        cancel.clear()
        btn_stop.configure(state="normal")
        status.set("Searching inputs…")
        rec, dump = opt["recursive"].get(), opt["dump"].get()

        def worker():  # the input search too: large folder trees take minutes, the window must stay usable
            code = 2
            try:
                sources = collect(inputs, rec, dump, exclude=out, progress=lambda m: events.put(("status", m)),
                                  cancel=cancel)
                if cancel.is_set():
                    return
                if not sources:
                    events.put(("status", "No extractions found. Add ZIPs or folders "
                                          "(with subfolders: check 'Include subfolders')."))
                    code = None
                    return
                events.put(("sources", (len(sources), out)))
                code = run(list(inputs), out, rec, dump, opt["export"].get(), n_jobs, mb,
                           log=lambda m: events.put(("log", m)), on_result=lambda r: events.put(("result", r)),
                           cancel=cancel, sources=sources)
            except Exception as e:  # noqa: BLE001
                events.put(("log", f"ERROR: {type(e).__name__}: {e}"))
            finally:
                events.put(("done", code))

        threading.Thread(target=worker, daemon=True).start()
        poll()

    def poll():
        try:
            while True:
                kind, data = events.get_nowait()
                if kind == "status":
                    status.set(data)
                elif kind == "sources":
                    prog.configure(maximum=data[0] * 100, value=0)
                    status.set(f"Scanning {data[0]} source(s) -> {data[1]}")
                elif kind == "log" and data.startswith("ERROR"):
                    show_detail(data, "E")
                elif kind == "log":
                    line = data.splitlines()[0]
                    m = re_start.match(line)
                    if m:
                        set_running(m.group(1), 0.0, m.group(2))
                    m = re_prog.match(line)
                    if m:
                        set_running(m.group(1), int(m.group(2)) / 100, m.group(3))
                    update_overall()
                elif kind == "result":
                    results.append(data)
                    add_row(len(results) - 1, data)
                    btn_open.configure(state="normal")
                    if (last_out[0] / "files").exists():
                        btn_exp.configure(state="normal")
                    e = running.pop(data["label"], None)
                    if e:
                        e["row"].destroy()
                    update_overall()
                elif kind == "done":
                    for e in running.values():
                        e["row"].destroy()
                    running.clear()
                    if not cancel.is_set():
                        prog["value"] = prog["maximum"]
                    btn_run.configure(state="normal")
                    btn_stop.configure(state="disabled")
                    btn_open.configure(state="normal" if last_out and last_out[0].exists() else "disabled")
                    btn_exp.configure(state="normal" if last_out and (last_out[0] / "files").exists() else "disabled")
                    if data is None:  # no extractions found: keep that message
                        return
                    n = Counter(tag_of(r) for r in results)
                    status.set(("Stopped" if cancel.is_set() else "Done") + f": {len(results)} source(s)  ·  seeds/keys {n[KEYS]}  ·  hints {n[HINTS]}  ·  "
                               f"nothing {n[NONE]}  ·  errors {n['E']}  ·  CSVs in {last_out[0] if last_out else '-'}")
                    if results:
                        best = max(range(len(results)), key=lambda i: (level(results[i]), -i))
                        tree.selection_set(str(best))
                        tree.see(str(best))
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    def open_out(sub=""):
        try:
            open_folder(last_out[0] / sub)
        except (OSError, IndexError) as e:
            messagebox.showerror("BASIL", f"Could not open the folder:\n{e}")

    def on_close():
        import multiprocessing
        for p in multiprocessing.active_children():  # running parallel scans
            p.terminate()
        root.destroy()
        os._exit(0)  # also ends a running single scan thread

    def stop_clicked():
        cancel.set()
        btn_stop.configure(state="disabled")
        status.set("Stopping… (running scans finish their current file, results so far are kept)")

    btn_run.configure(command=run_clicked)
    btn_stop.configure(command=stop_clicked)
    btn_open.configure(command=open_out)
    btn_exp.configure(command=lambda: open_out("files"))
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main():
    import multiprocessing
    multiprocessing.freeze_support()  # parallel scans in PyInstaller executables
    if len(sys.argv) == 1 or sys.argv[1:] == ["--gui"]:
        return gui()
    ap = argparse.ArgumentParser(description="BASIL - Blockchain Assets, Seeds, Identifiers & Ledgers: crypto wallet apps, seeds, private keys and addresses "
                                             "in mobile extractions (FFS ZIP, iTunes backup, GrayKey keychain).")
    ap.add_argument("inputs", nargs="+", help="ZIP, folder, iTunes backup folder or *keychain*.plist")
    ap.add_argument("-r", "--recursive", action="store_true", help="search subfolders of given folders too")
    ap.add_argument("-d", "--dump", action="store_true", help="given folders are extracted file systems")
    ap.add_argument("-o", "--out", default=time.strftime("basil_%Y%m%d_%H%M%S"),
                    help="output folder for the CSVs / exports (default: basil_<date>_<time>)")
    ap.add_argument("-x", "--export", action="store_true", help="copy wallet app files and files with hits (+ SHA-256)")
    ap.add_argument("-j", "--jobs", type=int, default=default_jobs(),
                    help="sources in parallel (default: CPU cores, max. 4; 1 on a single HDD)")
    ap.add_argument("--max-size", type=int, default=MAX_SIZE_MB, metavar="MB",
                    help=f"do not scan files larger than this (default {MAX_SIZE_MB})")
    ap.add_argument("--version", action="version", version=SIGNATURE)
    a = ap.parse_args()
    return run(a.inputs, a.out, a.recursive, a.dump, a.export, a.jobs, a.max_size)


# ---- BIP39 English word list (github.com/bitcoin/bips/blob/master/bip-0039/english.txt)
BIP39_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
BIP39_EN = """
abandon ability able about above absent absorb abstract absurd abuse access accident account accuse achieve
acid acoustic acquire across act action actor actress actual adapt add addict address adjust admit adult
advance advice aerobic affair afford afraid again age agent agree ahead aim air airport aisle alarm album
alcohol alert alien all alley allow almost alone alpha already also alter always amateur amazing among amount
amused analyst anchor ancient anger angle angry animal ankle announce annual another answer antenna antique
anxiety any apart apology appear apple approve april arch arctic area arena argue arm armed armor army around
arrange arrest arrive arrow art artefact artist artwork ask aspect assault asset assist assume asthma athlete
atom attack attend attitude attract auction audit august aunt author auto autumn average avocado avoid awake
aware away awesome awful awkward axis baby bachelor bacon badge bag balance balcony ball bamboo banana banner
bar barely bargain barrel base basic basket battle beach bean beauty because become beef before begin behave
behind believe below belt bench benefit best betray better between beyond bicycle bid bike bind biology bird
birth bitter black blade blame blanket blast bleak bless blind blood blossom blouse blue blur blush board boat
body boil bomb bone bonus book boost border boring borrow boss bottom bounce box boy bracket brain brand brass
brave bread breeze brick bridge brief bright bring brisk broccoli broken bronze broom brother brown brush
bubble buddy budget buffalo build bulb bulk bullet bundle bunker burden burger burst bus business busy butter
buyer buzz cabbage cabin cable cactus cage cake call calm camera camp can canal cancel candy cannon canoe
canvas canyon capable capital captain car carbon card cargo carpet carry cart case cash casino castle casual
cat catalog catch category cattle caught cause caution cave ceiling celery cement census century cereal
certain chair chalk champion change chaos chapter charge chase chat cheap check cheese chef cherry chest
chicken chief child chimney choice choose chronic chuckle chunk churn cigar cinnamon circle citizen city civil
claim clap clarify claw clay clean clerk clever click client cliff climb clinic clip clock clog close cloth
cloud clown club clump cluster clutch coach coast coconut code coffee coil coin collect color column combine
come comfort comic common company concert conduct confirm congress connect consider control convince cook cool
copper copy coral core corn correct cost cotton couch country couple course cousin cover coyote crack cradle
craft cram crane crash crater crawl crazy cream credit creek crew cricket crime crisp critic crop cross crouch
crowd crucial cruel cruise crumble crunch crush cry crystal cube culture cup cupboard curious current curtain
curve cushion custom cute cycle dad damage damp dance danger daring dash daughter dawn day deal debate debris
decade december decide decline decorate decrease deer defense define defy degree delay deliver demand demise
denial dentist deny depart depend deposit depth deputy derive describe desert design desk despair destroy
detail detect develop device devote diagram dial diamond diary dice diesel diet differ digital dignity dilemma
dinner dinosaur direct dirt disagree discover disease dish dismiss disorder display distance divert divide
divorce dizzy doctor document dog doll dolphin domain donate donkey donor door dose double dove draft dragon
drama drastic draw dream dress drift drill drink drip drive drop drum dry duck dumb dune during dust dutch
duty dwarf dynamic eager eagle early earn earth easily east easy echo ecology economy edge edit educate effort
egg eight either elbow elder electric elegant element elephant elevator elite else embark embody embrace
emerge emotion employ empower empty enable enact end endless endorse enemy energy enforce engage engine
enhance enjoy enlist enough enrich enroll ensure enter entire entry envelope episode equal equip era erase
erode erosion error erupt escape essay essence estate eternal ethics evidence evil evoke evolve exact example
excess exchange excite exclude excuse execute exercise exhaust exhibit exile exist exit exotic expand expect
expire explain expose express extend extra eye eyebrow fabric face faculty fade faint faith fall false fame
family famous fan fancy fantasy farm fashion fat fatal father fatigue fault favorite feature february federal
fee feed feel female fence festival fetch fever few fiber fiction field figure file film filter final find
fine finger finish fire firm first fiscal fish fit fitness fix flag flame flash flat flavor flee flight flip
float flock floor flower fluid flush fly foam focus fog foil fold follow food foot force forest forget fork
fortune forum forward fossil foster found fox fragile frame frequent fresh friend fringe frog front frost
frown frozen fruit fuel fun funny furnace fury future gadget gain galaxy gallery game gap garage garbage
garden garlic garment gas gasp gate gather gauge gaze general genius genre gentle genuine gesture ghost giant
gift giggle ginger giraffe girl give glad glance glare glass glide glimpse globe gloom glory glove glow glue
goat goddess gold good goose gorilla gospel gossip govern gown grab grace grain grant grape grass gravity
great green grid grief grit grocery group grow grunt guard guess guide guilt guitar gun gym habit hair half
hammer hamster hand happy harbor hard harsh harvest hat have hawk hazard head health heart heavy hedgehog
height hello helmet help hen hero hidden high hill hint hip hire history hobby hockey hold hole holiday hollow
home honey hood hope horn horror horse hospital host hotel hour hover hub huge human humble humor hundred
hungry hunt hurdle hurry hurt husband hybrid ice icon idea identify idle ignore ill illegal illness image
imitate immense immune impact impose improve impulse inch include income increase index indicate indoor
industry infant inflict inform inhale inherit initial inject injury inmate inner innocent input inquiry insane
insect inside inspire install intact interest into invest invite involve iron island isolate issue item ivory
jacket jaguar jar jazz jealous jeans jelly jewel job join joke journey joy judge juice jump jungle junior junk
just kangaroo keen keep ketchup key kick kid kidney kind kingdom kiss kit kitchen kite kitten kiwi knee knife
knock know lab label labor ladder lady lake lamp language laptop large later latin laugh laundry lava law lawn
lawsuit layer lazy leader leaf learn leave lecture left leg legal legend leisure lemon lend length lens
leopard lesson letter level liar liberty library license life lift light like limb limit link lion liquid list
little live lizard load loan lobster local lock logic lonely long loop lottery loud lounge love loyal lucky
luggage lumber lunar lunch luxury lyrics machine mad magic magnet maid mail main major make mammal man manage
mandate mango mansion manual maple marble march margin marine market marriage mask mass master match material
math matrix matter maximum maze meadow mean measure meat mechanic medal media melody melt member memory
mention menu mercy merge merit merry mesh message metal method middle midnight milk million mimic mind minimum
minor minute miracle mirror misery miss mistake mix mixed mixture mobile model modify mom moment monitor
monkey monster month moon moral more morning mosquito mother motion motor mountain mouse move movie much
muffin mule multiply muscle museum mushroom music must mutual myself mystery myth naive name napkin narrow
nasty nation nature near neck need negative neglect neither nephew nerve nest net network neutral never news
next nice night noble noise nominee noodle normal north nose notable note nothing notice novel now nuclear
number nurse nut oak obey object oblige obscure observe obtain obvious occur ocean october odor off offer
office often oil okay old olive olympic omit once one onion online only open opera opinion oppose option
orange orbit orchard order ordinary organ orient original orphan ostrich other outdoor outer output outside
oval oven over own owner oxygen oyster ozone pact paddle page pair palace palm panda panel panic panther paper
parade parent park parrot party pass patch path patient patrol pattern pause pave payment peace peanut pear
peasant pelican pen penalty pencil people pepper perfect permit person pet phone photo phrase physical piano
picnic picture piece pig pigeon pill pilot pink pioneer pipe pistol pitch pizza place planet plastic plate
play please pledge pluck plug plunge poem poet point polar pole police pond pony pool popular portion position
possible post potato pottery poverty powder power practice praise predict prefer prepare present pretty
prevent price pride primary print priority prison private prize problem process produce profit program project
promote proof property prosper protect proud provide public pudding pull pulp pulse pumpkin punch pupil puppy
purchase purity purpose purse push put puzzle pyramid quality quantum quarter question quick quit quiz quote
rabbit raccoon race rack radar radio rail rain raise rally ramp ranch random range rapid rare rate rather
raven raw razor ready real reason rebel rebuild recall receive recipe record recycle reduce reflect reform
refuse region regret regular reject relax release relief rely remain remember remind remove render renew rent
reopen repair repeat replace report require rescue resemble resist resource response result retire retreat
return reunion reveal review reward rhythm rib ribbon rice rich ride ridge rifle right rigid ring riot ripple
risk ritual rival river road roast robot robust rocket romance roof rookie room rose rotate rough round route
royal rubber rude rug rule run runway rural sad saddle sadness safe sail salad salmon salon salt salute same
sample sand satisfy satoshi sauce sausage save say scale scan scare scatter scene scheme school science
scissors scorpion scout scrap screen script scrub sea search season seat second secret section security seed
seek segment select sell seminar senior sense sentence series service session settle setup seven shadow shaft
shallow share shed shell sheriff shield shift shine ship shiver shock shoe shoot shop short shoulder shove
shrimp shrug shuffle shy sibling sick side siege sight sign silent silk silly silver similar simple since sing
siren sister situate six size skate sketch ski skill skin skirt skull slab slam sleep slender slice slide
slight slim slogan slot slow slush small smart smile smoke smooth snack snake snap sniff snow soap soccer
social sock soda soft solar soldier solid solution solve someone song soon sorry sort soul sound soup source
south space spare spatial spawn speak special speed spell spend sphere spice spider spike spin spirit split
spoil sponsor spoon sport spot spray spread spring spy square squeeze squirrel stable stadium staff stage
stairs stamp stand start state stay steak steel stem step stereo stick still sting stock stomach stone stool
story stove strategy street strike strong struggle student stuff stumble style subject submit subway success
such sudden suffer sugar suggest suit summer sun sunny sunset super supply supreme sure surface surge surprise
surround survey suspect sustain swallow swamp swap swarm swear sweet swift swim swing switch sword symbol
symptom syrup system table tackle tag tail talent talk tank tape target task taste tattoo taxi teach team tell
ten tenant tennis tent term test text thank that theme then theory there they thing this thought three thrive
throw thumb thunder ticket tide tiger tilt timber time tiny tip tired tissue title toast tobacco today toddler
toe together toilet token tomato tomorrow tone tongue tonight tool tooth top topic topple torch tornado
tortoise toss total tourist toward tower town toy track trade traffic tragic train transfer trap trash travel
tray treat tree trend trial tribe trick trigger trim trip trophy trouble truck true truly trumpet trust truth
try tube tuition tumble tuna tunnel turkey turn turtle twelve twenty twice twin twist two type typical ugly
umbrella unable unaware uncle uncover under undo unfair unfold unhappy uniform unique unit universe unknown
unlock until unusual unveil update upgrade uphold upon upper upset urban urge usage use used useful useless
usual utility vacant vacuum vague valid valley valve van vanish vapor various vast vault vehicle velvet vendor
venture venue verb verify version very vessel veteran viable vibrant vicious victory video view village
vintage violin virtual virus visa visit visual vital vivid vocal voice void volcano volume vote voyage wage
wagon wait walk wall walnut want warfare warm warrior wash wasp waste water wave way wealth weapon wear weasel
weather web wedding weekend weird welcome west wet whale what wheat wheel when where whip whisper wide width
wife wild will win window wine wing wink winner winter wire wisdom wise wish witness wolf woman wonder wood
wool word work world worry worth wrap wreck wrestle wrist write wrong yard year yellow you young youth zebra
zero zone zoo
"""

if __name__ == "__main__":
    sys.exit(main())
