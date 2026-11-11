#!/usr/bin/env python3
"""SAUCE - SIM And UFDR Content Evaluator.

Traffic light for importing UFDRs into analysis software.

Licenses are counted per extraction, so for every UFDR it checks:
  - is the ZIP intact (with --verify: full ZIP integrity check, every member read and CRC-checked)
  - number of extractions (1 per device is normal)
  - SIM extractions, and whether they contain any data (empty SIMs only cost a license)
  - content per extraction: messages, contacts, locations, calls (+ all item types)
and rates it:
  RED     defective UFDR, empty SIM extraction, >= 3 extractions
  YELLOW  2 extractions, SIM extraction with data, hardly any content, other warnings
  GREEN   everything else

Data sources (--source):
  xml  report.xml               - all UFDR versions
  db   DbData/database.db       - PA 10+ (PostgreSQL custom-format dump)
  auto database.db if present (much faster), otherwise report.xml (default)
If DbData/database.json exists, its SourceExtractionIds are used as a cross-check.

Only the standard library is used (GUI: tkinter, drag & drop: optional tkinterdnd2).

Usage:
  sauce.py                         start the GUI
  sauce.py <ufdr|folder> ... [-r] [-s] [-v] [-q] [-j N] [--source auto|xml|db] [--min-items N]
                                        [--case NO] [--csv FILE] [--html FILE]
"""
import argparse
import csv
import json
import re
import sys
import zipfile
import zlib
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# "SIM" not touching other letters: "SIM Card", "EXTRACTION_SIM", "USIM" - but not "SIMPLE"
SIM_RE = re.compile(r"(?<![a-z])U?SIM(?![a-z])", re.IGNORECASE)
XML_NAME = "report.xml"
DB_NAME = "DbData/database.db"
DB_JSON = "DbData/database.json"

# ---- traffic light rules
GREEN, YELLOW, RED = 0, 1, 2
LIGHT_NAMES = ("GREEN", "YELLOW", "RED")
MIN_ITEMS = 5  # below this in every CONTENT_CATS category: "hardly any content"
# item categories; model types from report.xml (singular) and database.db tables (plural)
CATEGORIES = {
    "Messages": {"InstantMessage", "SMS", "MMS", "Email"},
    "Contacts": {"Contact"},
    "Locations": {"Location", "Journey"},
    "Calls": {"Call"},
}
NESTED_COUNTED = CATEGORIES["Messages"]  # counted also when nested in another model (messages in chats)
CONTENT_CATS = ("Messages", "Contacts", "Locations", "Calls")  # "hardly any content" check
SIM_DATA_CATS = ("Messages", "Contacts", "Calls")     # a SIM extraction with none of these is "empty"


# media files in the UFDR, counted from the ZIP directory: Cellebrite's own categorization
# (files/<category>/) is taken over as is, deliberately without own logic (e.g. no extension filter)
FILE_CATS = {"Audio": "files/Audio/", "Video": "files/Video/"}


def file_counts(names):
    return Counter({c: sum(1 for n in names if n.startswith(prefix) and not n.endswith("/"))
                    for c, prefix in FILE_CATS.items()})


def fmt_files(files):
    return " · ".join(f"{c} {files[c]:,}" for c in FILE_CATS)


def category(model_type):
    for cat, types in CATEGORIES.items():
        if model_type in types or model_type[:-1] in types:  # Contacts -> Contact
            return cat
    return None


# --------------------------------------------------------------------------- report.xml

def tag(elem):
    return elem.tag.rsplit("}", 1)[-1]


CHUNK = 4 << 20
# header (sourceExtractions, metadata) ends where the big sections start
BODY_START = re.compile(rb"<(?:taggedFiles|decodedData)\b")
# body scan: CDATA is matched (and ignored) so chat text like "<model" inside it is not counted
BODY_TAG = re.compile(rb"<!\[CDATA\[.*?\]\]>|<(/?)(modelType|model|extractionInfo)\b([^>]*)>", re.S)
ATTR = re.compile(rb'([\w:.-]+)="([^"]*)"')


def _attrs(raw):
    from html import unescape
    return {k.decode(): unescape(v.decode("utf-8", "replace")) for k, v in ATTR.findall(raw)}


def _parse_header(data, extractions):
    """Parse the report.xml header (everything before taggedFiles/decodedData) with a real XML parser."""
    parser = ET.XMLPullParser(events=("start", "end"))
    parser.feed(data)
    section = None
    for event, elem in parser.read_events():
        name = tag(elem)
        if event == "start":
            if name == "metadata":
                section = elem.get("section")
        elif name == "extractionInfo":
            extractions[elem.get("id")] = dict(elem.attrib)
        elif name == "item" and section == "Extraction Data":
            ex_id = elem.get("sourceExtraction")
            if ex_id is not None:
                extractions.setdefault(ex_id, {"id": ex_id})[elem.get("name")] = (elem.text or "").strip()
        elif name == "metadata":
            section = None


def parse_xml(fh, quick=False):
    """Stream report.xml. Returns (extractions, Counter{(extraction id, model type): n}).

    The header is parsed with ElementTree; the (huge) rest is scanned with a regex for
    <model> tags, which is several times faster. Counts top-level models (direct
    children of <modelType>) plus messages (NESTED_COUNTED) nested in Chats; a message
    listed both in its chat and at top level (same id) is counted once.
    quick: stop after the header (extractions only, no counts).
    """
    extractions = {}  # id -> dict
    counts = Counter()
    ext_stack = []  # (extraction id, model type) of the open <model> elements
    seen = set()  # hashes of counted message ids: report.xml lists chat messages also at top level
    header, rest, tail = b"", b"", b""
    in_body = False

    while True:
        chunk = fh.read(CHUNK)
        if not in_body:
            header += chunk
            m = BODY_START.search(header)
            if m is None and chunk:
                continue
            in_body = True
            if m is None:  # no body at all
                _parse_header(header, extractions)
                tail = header[-64:]
                break
            _parse_header(header[:m.start()], extractions)
            if quick:
                return list(extractions.values()), counts
            chunk, header = header[m.start():], b""
        if not chunk:
            break
        data = rest + chunk
        # cut before an incomplete tag or an unterminated CDATA section at the chunk end
        cut = data.rfind(b"<")
        cdata = data.rfind(b"<![CDATA[")
        if cdata > data.rfind(b"]]>"):
            cut = min(cut, cdata)
        data, rest = data[:cut], data[cut:]
        tail = (tail + data)[-64:]
        for m in BODY_TAG.finditer(data):
            close, name, raw = m.groups()
            if name is None or name == b"modelType":
                continue
            if name == b"extractionInfo":  # normally in the header; just in case
                if not close:
                    a = _attrs(raw)
                    extractions.setdefault(a.get("id"), {}).update(a)
                continue
            if close:
                if not ext_stack:
                    raise ValueError("report.xml not well-formed (unbalanced </model>)")
                ext_stack.pop()
                continue
            a = _attrs(raw)
            ext = a.get("extractionId") or (ext_stack[-1][0] if ext_stack else None)
            mtype = a.get("type", "?")
            if not ext_stack or mtype in NESTED_COUNTED:
                if ext_stack and ext_stack[-1][1] in NESTED_COUNTED:
                    mtype = "Embedded" + mtype  # message inside a message (database.db: own table)
                mid = a.get("id")
                if mid is None or hash(mid) not in seen:  # 64-bit hash: less memory than the ids
                    counts[(ext, mtype)] += 1
                    if mid is not None:
                        seen.add(hash(mid))
            if not raw.rstrip().endswith(b"/"):
                ext_stack.append((ext, mtype))

    tail = (tail + rest).rstrip()
    if ext_stack or not tail.endswith(b">") or not re.search(rb"</(?:\w+:)?project>$", tail):
        raise ValueError("report.xml truncated or not well-formed")
    return list(extractions.values()), counts


# --------------------------------------------------------------------------- database.db (pg_dump -Fc)

class PgDump:
    """Minimal reader for PostgreSQL custom-format dumps (archive version 1.12 - 1.16)."""

    def __init__(self, fh):
        self.fh = fh
        if fh.read(5) != b"PGDMP":
            raise ValueError("database.db is not a pg_dump custom-format archive")
        vmaj, vmin, vrev, self.intsize, self.offsize, fmt = fh.read(6)
        self.version = (vmaj, vmin, vrev)
        if fmt != 1:
            raise ValueError(f"unsupported pg_dump format {fmt}")
        if self.version >= (1, 15, 0):
            algorithm = fh.read(1)[0]  # 0 none, 1 gzip, 2 lz4, 3 zstd
            if algorithm not in (0, 1):
                raise ValueError("only uncompressed or gzip-compressed dumps are supported")
            self.compressed = algorithm == 1
        else:
            self.compressed = self.int() != 0
        for _ in range(7):  # creation timestamp
            self.int()
        for _ in range(3):  # db name, server version, pg_dump version
            self.bytes()
        self.entries = [self._entry() for _ in range(self.int())]

    def int(self):
        sign = self.fh.read(1)[0]
        value = int.from_bytes(self.fh.read(self.intsize), "little")
        return -value if sign else value

    def bytes(self):
        n = self.int()
        return self.fh.read(n) if n > 0 else b""

    def str(self):
        return self.bytes().decode("utf-8", "replace")

    def _entry(self):
        e = {"dump_id": self.int(), "had_dumper": self.int()}
        self.bytes(), self.bytes()  # table oid, oid
        e["tag"], e["desc"] = self.str(), self.str()
        self.int()  # section
        e["defn"] = self.str()
        self.bytes(), self.bytes()  # drop stmt, copy stmt
        e["namespace"] = self.str()
        self.bytes()  # tablespace
        if self.version >= (1, 14, 0):
            self.bytes()  # table access method
        if self.version >= (1, 16, 0):
            self.int()  # relkind
        self.bytes(), self.bytes()  # owner, with oids
        while self.bytes():  # dependencies, terminated by empty string
            pass
        state = self.fh.read(1)[0]
        offset = int.from_bytes(self.fh.read(self.offsize), "little")
        e["offset"] = offset if state == 2 else None  # 2 = K_OFFSET_POS_SET
        return e

    def tables(self):
        """TABLE entries that have data, sorted by file offset (forward seeks only)."""
        data = {e["tag"]: e for e in self.entries if e["desc"] == "TABLE DATA" and e["offset"]}
        out = []
        for e in self.entries:
            if e["desc"] == "TABLE" and e["tag"] in data:
                cols = [line.strip().split('"')[1] for line in e["defn"].splitlines() if line.strip().startswith('"')]
                out.append({"name": e["tag"], "columns": cols, **{k: data[e["tag"]][k] for k in ("dump_id", "offset")}})
        return sorted(out, key=lambda t: t["offset"])

    def chunks(self, table):
        """Raw (decompressed) COPY data of a table, chunk by chunk."""
        self.fh.seek(table["offset"])
        self.fh.read(1)  # block type
        if self.int() != table["dump_id"]:
            raise ValueError(f"data block mismatch for table {table['name']}")
        dec = zlib.decompressobj() if self.compressed else None
        while (n := self.int()) > 0:
            chunk = self.fh.read(n)
            yield dec.decompress(chunk) if dec else chunk
        if dec:
            yield dec.flush()

    def lines(self, table):
        """COPY text lines (one row each) up to the end marker '\\.'."""
        rest = b""
        for c in self.chunks(table):
            *lines, rest = (rest + c).split(b"\n")
            for line in lines:
                if line == b"\\.":
                    return
                if line:
                    yield line
        if rest and rest != b"\\.":
            yield rest

    def count_rows(self, table):
        """Number of rows without splitting lines (newlines inside values are escaped in COPY data)."""
        n, tail = 0, b""
        for c in self.chunks(table):
            n += c.count(b"\n")
            tail = (tail + c)[-64:]
        body = tail.rstrip(b"\n")
        if not body:
            return 0
        lines = n - (len(tail) - len(body)) + 1  # lines up to the last non-empty one
        return lines - (body == b"\\." or body.endswith(b"\n\\."))  # end marker line

    def rows(self, table):
        for line in self.lines(table):
            vals = line.decode("utf-8", "replace").split("\t")
            vals = [None if v == "\\N" else v.replace("\\\\", "\\") for v in vals]
            yield dict(zip(table["columns"], vals))


def count_models(dump, t, counts):
    """Count top-level decoded models of a table per extraction into counts.

    Model tables carry DecodingConfidence/ModelLabels/SourceExtraction; junction
    tables have a '_' in their name. Rows that point to a parent model via a
    '...DtoId' column are sub-models (e.g. Locations of a Journey) and are skipped -
    except messages, which always belong to a chat.
    """
    cols = t["columns"]
    if not {"DecodingConfidence", "ModelLabels", "SourceExtraction"} <= set(cols) or "_" in t["name"]:
        return
    name = t["name"]
    # messages belong to a chat (parent column) but are counted anyway
    parent_i = [] if category(name) == "Messages" else [i for i, c in enumerate(cols) if c.endswith("DtoId")]
    if category(name) is None and not parent_i:
        # not needed per extraction (only in "All item types"): just count the rows
        counts[(None, name)] += dump.count_rows(t)
        return
    ext_i = cols.index("SourceExtraction")
    rows = Counter()
    for line in dump.lines(t):
        vals = line.split(b"\t")
        if all(vals[i] == b"\\N" for i in parent_i):
            rows[vals[ext_i]] += 1
    for ext, n in rows.items():
        counts[(ext.decode("ascii", "replace"), name)] += n


def parse_db(fh, quick=False):
    """Read database.db. Returns (extractions, Counter{(extraction id, table): n}).

    quick: read only the ExtractionInfos table (no counts).
    """
    dump = PgDump(fh)
    extractions, counts = [], Counter()
    for t in dump.tables():
        if t["name"] == "ExtractionInfos":
            for r in dump.rows(t):
                extractions.append({
                    "id": r.get("Id"), "name": r.get("Name"), "type": r.get("Type"),
                    "deviceName": r.get("DeviceName"), "fullName": r.get("FullDeviceName"),
                })
            if quick:
                break
        elif not quick:
            count_models(dump, t, counts)
    return extractions, counts


# --------------------------------------------------------------------------- check + rating

def describe(ex):
    parts = [ex.get("name") or ex.get("type") or "?"]
    etype = ex.get("ExtractionType")
    if etype and etype != parts[0]:
        parts.append(f"[{etype}]")
    device = " ".join(filter(None, (ex.get("DeviceInfoSelectedManufacturer"), ex.get("DeviceInfoSelectedDeviceName"))))
    device = device or ex.get("fullName")
    if device:
        parts.append(f"- {device}")
    return " ".join(parts)


def is_sim(ex):
    fields = (ex.get("type"), ex.get("name"), ex.get("fullName"), ex.get("deviceName"), ex.get("ExtractionType"))
    return any(f and SIM_RE.search(str(f)) for f in fields)


def cat_counts(model_counts):
    cats = Counter({c: 0 for c in CATEGORIES})
    for mtype, n in model_counts.items():
        c = category(mtype)
        if c:
            cats[c] += n
    return cats


def fmt_cats(cats):
    return " · ".join(f"{c} {cats[c]:,}" for c in CATEGORIES)


def evaluate(r, min_items=MIN_ITEMS):
    """Set r['light'] and r['reasons'] = [(level, text), ...]."""
    reasons = []
    if r["errors"]:
        reasons += [(RED, f"defective: {e}") for e in r["errors"]]
    else:
        exs = r["extractions"]
        n = len(exs)
        if n == 0:
            reasons.append((RED, "no extraction found"))
        elif n >= 3:
            reasons.append((RED, f"{n} extractions (license per extraction)"))
        elif n == 2:
            reasons.append((YELLOW, "2 extractions - separate memory card / SIM?"))
        for e in exs:
            if e["sim"] and r.get("quick"):
                reasons.append((YELLOW, f"SIM extraction (content not checked, quick mode): {e['label']}"))
            elif e["sim"]:
                if sum(e["cats"][c] for c in SIM_DATA_CATS) == 0:
                    reasons.append((RED, f"empty SIM extraction: {e['label']} - do not import"))
                else:
                    reasons.append((YELLOW, f"SIM extraction with data: {e['label']}"))
        if n and not r.get("quick") and all(r["cats"][c] < min_items for c in CONTENT_CATS):
            reasons.append((YELLOW, "hardly any content: " + ", ".join(f"{c} {r['cats'][c]}" for c in CONTENT_CATS)))
        reasons += [(YELLOW, w) for w in r["warnings"]]
    r["reasons"] = reasons
    r["light"] = max((lvl for lvl, _ in reasons), default=GREEN)
    return r


def check(path, verify=False, source="auto", min_items=MIN_ITEMS, quick=False):
    """Check one UFDR. quick: extractions only (no content counts, much faster)."""
    res = {"file": str(path), "source": "", "quick": quick, "errors": [], "warnings": [],
           "extractions": [], "models": Counter(), "cats": cat_counts({}), "files": Counter()}
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            res["files"] = file_counts(names)
            if verify:
                bad = zf.testzip()
                if bad:
                    res["errors"].append(f"CRC error in member: {bad}")
            auto = source == "auto"
            if auto:
                source = "db" if DB_NAME in names else "xml"
            member = XML_NAME if source == "xml" else DB_NAME
            res["source"] = source
            if member not in names:
                res["errors"].append(f"{member} missing")
            else:
                try:
                    with zf.open(member) as fh:
                        exs, counts = (parse_xml if source == "xml" else parse_db)(fh, quick)
                except (ValueError, IndexError, zlib.error) as e:
                    if not (auto and source == "db" and XML_NAME in names):
                        raise
                    # e.g. zstd/lz4-compressed dump: fall back to report.xml
                    res["warnings"].append(f"database.db not readable ({e}) - report.xml used")
                    source = res["source"] = "xml"
                    member = XML_NAME
                    with zf.open(member) as fh:
                        exs, counts = parse_xml(fh, quick)
                for e in exs:
                    models = Counter({m: n for (x, m), n in counts.items() if x == e.get("id")})
                    res["extractions"].append({"id": e.get("id"), "label": describe(e), "sim": is_sim(e),
                                               "models": models, "cats": cat_counts(models)})
                for (_, m), n in counts.items():
                    res["models"][m] += n
                res["cats"] = cat_counts(res["models"])
                if DB_JSON in names:
                    ids = json.loads(zf.read(DB_JSON)).get("SourceExtractionIds") or []
                    if ids and len(ids) != len(exs):
                        res["warnings"].append(
                            f"database.json lists {len(ids)} extraction(s), {member} {len(exs)}")
    except zipfile.BadZipFile as e:
        res["errors"].append(f"not a valid ZIP: {e}")
    except ET.ParseError as e:
        res["errors"].append(f"report.xml not parseable: {e}")
    except (OSError, ValueError, IndexError, zlib.error, RuntimeError, NotImplementedError) as e:
        res["errors"].append(f"{type(e).__name__}: {e}")
    res["ok"] = not res["errors"]
    return evaluate(res, min_items)


def default_jobs():
    import os
    return max(1, min(4, os.cpu_count() or 1))


def check_all(files, jobs=1, running=None, **kw):
    """Check UFDRs, yielding (index, result) as they finish; jobs > 1: in parallel processes.

    running: optional callback, called with the list of files currently being checked.
    """
    for i, r in _check_all(files, jobs, running or (lambda _: None), **kw):
        r["idx"] = i
        yield i, r


def _check_all(files, jobs, running, **kw):
    if jobs <= 1 or len(files) <= 1:
        for i, f in enumerate(files):
            running([f])
            yield i, check(f, **kw)
        return
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor, as_completed
    # spawn: safe with the GUI thread and in the PyInstaller executables (see freeze_support in main)
    with ProcessPoolExecutor(min(jobs, len(files)), mp_context=multiprocessing.get_context("spawn")) as ex:
        futures = {ex.submit(check, f, **kw): i for i, f in enumerate(files)}
        pending = dict(futures)

        def report():
            # futures are handed to the workers in order; the pool may pre-queue one extra
            running([files[i] for i in sorted(pending.values())[:jobs]])

        report()
        for fut in as_completed(futures):
            del pending[fut]
            report()
            yield futures[fut], fut.result()


def format_result(r, full=True):
    src = r["source"] + (", quick" if r.get("quick") else "")
    out = [f"[{LIGHT_NAMES[r['light']]}] {r['file']}" + (f"  (source: {src})" if r["source"] else "")]
    out += [f"    {'!' if lvl == RED else '?'} {text}" for lvl, text in r["reasons"]]
    if r["ok"]:
        out.append(f"    Extractions: {len(r['extractions'])}")
        labels = [e["label"] + ("  [SIM]" if e["sim"] else "") for e in r["extractions"]]
        width = max(map(len, labels), default=0)
        for label, e in zip(labels, r["extractions"]):
            out.append(f"      - {label:<{width}}    {'' if r.get('quick') else fmt_cats(e['cats'])}".rstrip())
        if not r.get("quick"):
            out.append(f"    Content: {fmt_cats(r['cats'])}")
        out.append(f"    Files:   {fmt_files(r['files'])}")
        if full and r["models"]:
            out.append("    All item types:")
            for k, v in sorted(r["models"].items(), key=lambda kv: (-kv[1], kv[0])):
                out.append(f"      {k:<30} {v:>10,}")
    return "\n".join(out)


def collect_files(paths, recursive=False):
    """Expand files/folders into a list of UFDRs. Returns (files, not_found)."""
    pattern = "**/*" if recursive else "*"
    files, missing = [], []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.glob(pattern) if f.is_file() and f.suffix.lower() == ".ufdr")
        elif p.is_file():
            files.append(p)  # given explicitly: checked regardless of extension
        else:
            missing.append(p)
    return list(dict.fromkeys(files)), missing  # drop duplicates, keep order


def write_csv(results, path, case=""):
    model_keys = sorted({k for r in results for k in r["models"]})
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:  # BOM: Excel opens UTF-8 correctly
        w = csv.writer(fh, delimiter=";")
        w.writerow(["case", "file", "light", "reasons", "source", "extraction_count", "extractions",
                    "sim_count", *CATEGORIES, *(f"{c.lower()}_files" for c in FILE_CATS), *model_keys])
        for r in results:
            q = r.get("quick")
            exs = [e["label"] + (" [SIM]" if e["sim"] else "") + ("" if q else f" ({fmt_cats(e['cats'])})")
                   for e in r["extractions"]]
            w.writerow([
                case, r["file"], LIGHT_NAMES[r["light"]], " | ".join(t for _, t in r["reasons"]), r["source"],
                len(r["extractions"]), " | ".join(exs), sum(e["sim"] for e in r["extractions"]),
                *(("" if q else r["cats"][c]) for c in CATEGORIES),
                *((r["files"][c] if r["ok"] else "") for c in FILE_CATS),
                *(("" if q else r["models"].get(k, 0)) for k in model_keys),
            ])


HTML_CSS = """
:root{--bg:#f3f5f8;--card:#fff;--text:#1e293b;--muted:#64748b;--border:#d8dee6;--head:#1e293b;
--g:#15803d;--gbg:#eaf6ee;--y:#a16207;--ybg:#fff6dd;--r:#b91c1c;--rbg:#fdeceb}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",system-ui,-apple-system,sans-serif}
header{background:var(--head);color:#fff;padding:18px 28px}
header h1{margin:0;font-size:22px}
header p{margin:2px 0 0;color:#94a3b8}
main{max-width:1200px;margin:0 auto;padding:20px 28px}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px 18px;margin-bottom:16px}
h2{font-size:16px;margin:0 0 12px}
dl.meta{display:grid;grid-template-columns:max-content 1fr;gap:4px 18px;margin:0}
dl.meta dt{color:var(--muted)}dl.meta dd{margin:0}
.case{font-size:18px;font-weight:600}
.chips{display:flex;gap:10px;flex-wrap:wrap}
.chip{border-radius:999px;padding:6px 14px;font-weight:600}
.chip.g{background:var(--gbg);color:var(--g)}.chip.y{background:var(--ybg);color:var(--y)}.chip.r{background:var(--rbg);color:var(--r)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
th{background:#e9edf2;font-weight:600;white-space:nowrap}
th.n{text-align:right}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.g td{background:var(--gbg)}tr.y td{background:var(--ybg)}tr.r td{background:var(--rbg)}
.light{font-weight:700;white-space:nowrap}
tr.g .light{color:var(--g)}tr.y .light{color:var(--y)}tr.r .light{color:var(--r)}
.path{color:var(--muted);font-size:12px;word-break:break-all}
ul.reasons{margin:0;padding-left:18px}
details{border:1px solid var(--border);border-radius:8px;margin-bottom:10px;background:var(--card)}
details>summary{cursor:pointer;padding:10px 14px;font-weight:600}
details>div{padding:0 14px 14px}
details.g>summary{border-left:6px solid var(--g)}details.y>summary{border-left:6px solid var(--y)}details.r>summary{border-left:6px solid var(--r)}
.sim{background:#e0e7ff;color:#3730a3;border-radius:4px;padding:0 6px;font-size:12px;font-weight:600}
.types{columns:3 220px;font-size:13px}
.types div{display:flex;justify-content:space-between;gap:10px;break-inside:avoid;border-bottom:1px dotted var(--border)}
footer{color:var(--muted);font-size:12px;text-align:center;padding:10px}
@media print{body{background:#fff}header{-webkit-print-color-adjust:exact;print-color-adjust:exact}
tr td,.chip{-webkit-print-color-adjust:exact;print-color-adjust:exact}details{break-inside:avoid}}
"""


def write_html(results, path, case="", settings=None):
    """Self-contained HTML report (no external resources, printable)."""
    import datetime
    from html import escape as e

    cls = "gyr"
    words = ("GO", "CHECK", "STOP")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    n = Counter(r["light"] for r in results)
    settings = settings or {}

    def reasons_html(r):
        if not r["reasons"]:
            return "-"
        items = sorted(r["reasons"], key=lambda x: -x[0])
        return "<ul class='reasons'>" + "".join(f"<li>{e(t)}</li>" for _, t in items) + "</ul>"

    rows = []
    for r in results:
        ok, c = r["ok"], r["cats"]
        num = (lambda v: f"{v:,}") if ok else (lambda v: "")
        cnum = num if not r.get("quick") else (lambda v: "–")
        rows.append(
            f"<tr class='{cls[r['light']]}'><td class='light'>● {words[r['light']]}</td>"
            f"<td><b>{e(Path(r['file']).name)}</b><div class='path'>{e(r['file'])}</div></td>"
            f"<td class='n'>{num(len(r['extractions']))}</td>"
            f"<td class='n'>{num(sum(x['sim'] for x in r['extractions']))}</td>"
            + "".join(f"<td class='n'>{cnum(c[k])}</td>" for k in CONTENT_CATS)
            + "".join(f"<td class='n'>{num(r['files'][k])}</td>" for k in FILE_CATS)
            + f"<td>{reasons_html(r)}</td></tr>")

    details = []
    for r in results:
        body = [f"<p class='path'>{e(r['file'])} · source: {e(r['source'] or '-')}</p>", reasons_html(r)]
        if r["ok"]:
            body.append(f"<p>Files in UFDR: {e(fmt_files(r['files']))}</p>")
        if r["ok"] and r.get("quick"):
            body.append("<h3>Extractions</h3><ul>" + "".join(
                f"<li>{e(x['label'])}{' <span class=sim>SIM</span>' if x['sim'] else ''}</li>"
                for x in r["extractions"]) + "</ul><p class='path'>quick mode: content not counted</p>")
        elif r["ok"]:
            body.append("<h3>Extractions</h3><div class='scroll'><table><tr><th>Extraction</th>"
                        + "".join(f"<th class='n'>{k}</th>" for k in CATEGORIES) + "</tr>")
            for x in r["extractions"]:
                sim = " <span class='sim'>SIM</span>" if x["sim"] else ""
                body.append(f"<tr><td>{e(x['label'])}{sim}</td>"
                            + "".join(f"<td class='n'>{x['cats'][k]:,}</td>" for k in CATEGORIES) + "</tr>")
            body.append("</table></div>")
            if r["models"]:
                body.append("<h3>All item types</h3><div class='types'>" + "".join(
                    f"<div><span>{e(k)}</span><span>{v:,}</span></div>"
                    for k, v in sorted(r["models"].items(), key=lambda kv: (-kv[1], kv[0]))) + "</div>")
        open_attr = " open" if r["light"] else ""
        details.append(f"<details class='{cls[r['light']]}'{open_attr}><summary>● {words[r['light']]} — "
                       f"{e(Path(r['file']).name)}</summary><div>{''.join(body)}</div></details>")

    meta = []
    if case:
        meta.append(f"<dt>Case number</dt><dd class='case'>{e(case)}</dd>")
    meta.append(f"<dt>Created</dt><dd>{now}</dd>")
    meta.append(f"<dt>UFDRs</dt><dd>{len(results)}</dd>")
    for k, v in settings.items():
        meta.append(f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>")

    title = "SAUCE" + (f" – {case}" if case else "")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><style>{HTML_CSS}</style></head><body>
<header><h1>{e(title)}</h1><p>SIM And UFDR Content Evaluator · traffic light for import</p></header>
<main>
<section class="card"><dl class="meta">{''.join(meta)}</dl></section>
<section class="card"><h2>Overview</h2><div class="chips">
<span class="chip g">● GO: {n[GREEN]}</span><span class="chip y">● CHECK: {n[YELLOW]}</span>
<span class="chip r">● STOP: {n[RED]}</span></div></section>
<section class="card"><h2>Results</h2><div class="scroll"><table>
<tr><th>Light</th><th>File</th><th class="n">Extr.</th><th class="n">SIM</th>{''.join(f"<th class='n'>{k}</th>" for k in CONTENT_CATS)}{''.join(f"<th class='n'>{k}</th>" for k in FILE_CATS)}<th>Reasons</th></tr>
{''.join(rows)}
</table></div></section>
<section><h2>Details</h2>{''.join(details)}</section>
<section class="card"><h2>Rules</h2><ul>
<li><b>STOP</b>: UFDR defective · empty SIM extraction (no messages, contacts or calls) · 3 or more extractions</li>
<li><b>CHECK</b>: 2 extractions · SIM extraction with data · hardly any content
(messages, contacts, locations and calls each below {e(str(settings.get('Min. items', MIN_ITEMS)))}) · warnings</li>
<li><b>GO</b>: everything else</li></ul></section>
</main><footer>sauce · {now}</footer></body></html>
"""
    Path(path).write_text(doc, encoding="utf-8")


def footer(results):
    n = Counter(r["light"] for r in results)
    return (f"{len(results)} UFDR(s) checked:  {n[GREEN]} green,  {n[YELLOW]} yellow,  {n[RED]} red")



# --------------------------------------------------------------------------- GUI

def run_gui():
    import queue
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter import font as tkfont

    try:  # optional: drag & drop (pip install tkinterdnd2, bundled in the executables)
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        dnd = True
    except Exception:
        root = tk.Tk()
        dnd = False

    C = {
        "bg": "#f3f5f8", "card": "#ffffff", "head": "#1e293b", "head_sub": "#94a3b8",
        "text": "#1e293b", "muted": "#64748b", "border": "#d8dee6",
        "accent": "#2563eb", "accent_hover": "#1d4ed8", "accent_off": "#9db7f2",
        "drop": "#f5f8ff", "drop_active": "#dbe7ff",
        "ok": "#15803d", "ok_bg": "#eaf6ee", "bad": "#b91c1c", "bad_bg": "#fdeceb",
        "warn": "#a16207", "warn_bg": "#fff6dd",
    }
    root.title("SAUCE")
    root.configure(bg=C["bg"])

    base = tkfont.nametofont("TkDefaultFont")
    base.configure(size=10, family="Segoe UI" if sys.platform == "win32" else base.actual("family"))
    # pixel sizes follow the real font size (HiDPI, e.g. Xft.dpi=192 on Linux)
    scale = max(1.0, base.metrics("linespace") / 17)

    def px(n):
        return int(round(n * scale))

    w, h = min(px(1040), int(root.winfo_screenwidth() * 0.9)), min(px(780), int(root.winfo_screenheight() * 0.9))
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
    st.configure("TCombobox", arrowsize=px(13), padding=px(3))
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
    # no selection colors: a selected row keeps its traffic-light color (stronger tag, see on_select)
    st.map("Treeview", background=[], foreground=[])
    st.configure("Horizontal.TProgressbar", troughcolor="#e2e7ee", background=C["accent"],
                 lightcolor=C["accent"], darkcolor=C["accent"], bordercolor="#e2e7ee", thickness=px(6))

    inputs, results, events = [], [], queue.Queue()
    opt = {k: tk.BooleanVar(value=False) for k in ("recursive", "verify", "quick")}
    jobs = tk.IntVar(value=default_jobs())
    min_items = tk.IntVar(value=MIN_ITEMS)
    case_no = tk.StringVar()
    run_settings = {}
    source = tk.StringVar(value="auto")
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
    tk.Label(head, text="SAUCE", bg=C["head"], fg="white",
             font=(base.actual("family"), 17, "bold")).pack(side="left", padx=(px(18), px(12)), pady=px(12))
    tk.Label(head, text="SIM And UFDR Content Evaluator  ·  traffic light for import", bg=C["head"],
             fg=C["head_sub"]).pack(side="left", pady=(px(6), 0))

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
    drop_hint = ("Drop UFDR files or folders here" if dnd else "Drag & drop needs: pip install tkinterdnd2")

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
        status.set(f"{len(inputs)} input(s) selected.")

    def add_files(_=None):
        add(filedialog.askopenfilenames(title="Select UFDR files",
                                        filetypes=[("UFDR", "*.ufdr *.UFDR"), ("All files", "*")]))

    def add_folder():
        add([filedialog.askdirectory(title="Select folder with UFDRs")])

    def remove():
        for i in reversed(lst.curselection()):
            lst.delete(i)
            del inputs[i]

    def clear():
        lst.delete(0, "end")
        inputs.clear()

    drop.bind("<Button-1>", add_files)
    for text, cmd in (("Add files…", add_files), ("Add folder…", add_folder)):
        ttk.Button(btns, text=text, command=cmd).pack(side="left", padx=(0, px(6)))
    for text, cmd in (("Clear", clear), ("Remove selected", remove)):
        ttk.Button(btns, text=text, command=cmd).pack(side="right", padx=(px(6), 0))

    if dnd:
        def on_drop(event):
            add(root.tk.splitlist(event.data))
            draw_drop()
            return event.action

        for w in (drop, lst):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", on_drop)
            w.dnd_bind("<<DropEnter>>", lambda e: (draw_drop(True), e.action)[1])
            w.dnd_bind("<<DropLeave>>", lambda e: (draw_drop(), e.action)[1])

    # ---- options card
    copt = card(body, fill="x", pady=(px(10), 0))
    r1 = ttk.Frame(copt, style="Card.TFrame")
    r1.pack(fill="x", pady=(0, px(10)))
    ttk.Label(r1, text="Case number (optional)", style="Muted.TLabel").pack(side="left", padx=(0, px(8)))
    ttk.Entry(r1, textvariable=case_no, width=28).pack(side="left")
    btn_csv = ttk.Button(r1, text="Save CSV…", state="disabled")
    btn_csv.pack(side="right")
    btn_html = ttk.Button(r1, text="Save HTML report…", state="disabled")
    btn_html.pack(side="right", padx=px(8))
    r2 = ttk.Frame(copt, style="Card.TFrame")
    r2.pack(fill="x")
    ttk.Checkbutton(r2, text="Include subfolders", variable=opt["recursive"]).pack(side="left")
    ttk.Checkbutton(r2, text="Verify ZIP integrity (slow)", variable=opt["verify"]).pack(side="left", padx=px(14))
    ttk.Checkbutton(r2, text="Quick (extractions only)", variable=opt["quick"]).pack(side="left")
    ttk.Label(r2, text="Parallel", style="Muted.TLabel").pack(side="left", padx=(px(20), px(6)))
    ttk.Spinbox(r2, from_=1, to=32, textvariable=jobs, width=3).pack(side="left")
    ttk.Label(r2, text="Min. items", style="Muted.TLabel").pack(side="left", padx=(px(20), px(6)))
    ttk.Spinbox(r2, from_=0, to=100000, textvariable=min_items, width=5).pack(side="left")
    ttk.Label(r2, text="Source", style="Muted.TLabel").pack(side="left", padx=(px(20), px(6)))
    ttk.Combobox(r2, textvariable=source, values=("auto", "xml", "db"), width=6,
                 state="readonly").pack(side="left")
    btn_run = ttk.Button(r2, text="▶  Run", style="Accent.TButton")
    btn_run.pack(side="right")

    # ---- progress + status
    prog = ttk.Progressbar(body, mode="determinate")
    prog.pack(fill="x", pady=(px(12), px(2)))
    ttk.Label(body, textvariable=status, style="Status.TLabel").pack(anchor="w")

    # ---- results card: table + details
    cres = card(body, "Results", fill="both", expand=True, pady=(px(8), 0))
    pane = ttk.PanedWindow(cres, orient="vertical")
    pane.pack(fill="both", expand=True)

    tframe = ttk.Frame(pane, style="Card.TFrame")
    cols = (("light", "Light", 95, "w"), ("file", "File", 240, "w"), ("ext", "Extr.", 55, "center"),
            ("sim", "SIM", 45, "center"), ("msg", "Messages", 85, "center"), ("con", "Contacts", 80, "center"),
            ("loc", "Locations", 85, "center"), ("call", "Calls", 70, "center"),
            ("aud", "Audio", 65, "center"), ("vid", "Video", 65, "center"), ("note", "Reasons", 300, "w"))
    tree = ttk.Treeview(tframe, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=7)
    for cid, title, width, anchor in cols:
        tree.heading(cid, text=title, anchor=anchor)
        tree.column(cid, width=px(width), anchor=anchor, stretch=cid in ("file", "note"))
    for lvl, bg, fg, sel_bg, sel_fg in ((GREEN, C["ok_bg"], C["ok"], "#bfe6cb", "#0f5f2a"),
                                         (YELLOW, C["warn_bg"], C["warn"], "#fde58a", "#7a4a00"),
                                         (RED, C["bad_bg"], C["bad"], "#f8c4c0", "#991b1b")):
        tree.tag_configure(f"L{lvl}", background=bg, foreground=fg)
        tree.tag_configure(f"L{lvl}s", background=sel_bg, foreground=sel_fg, font=bold)
    tsb = ttk.Scrollbar(tframe, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=tsb.set)
    tree.pack(side="left", fill="both", expand=True)
    tsb.pack(side="right", fill="y")
    pane.add(tframe, weight=3)

    dframe = ttk.Frame(pane, style="Card.TFrame")
    detail = tk.Text(dframe, font=mono, relief="flat", wrap="none", height=8, bg="#fafbfc",
                     fg=C["text"], padx=px(10), pady=px(8), highlightthickness=0, state="disabled")
    dsb = ttk.Scrollbar(dframe, orient="vertical", command=detail.yview)
    detail.configure(yscrollcommand=dsb.set)
    for lvl, color in ((GREEN, C["ok"]), (YELLOW, C["warn"]), (RED, C["bad"])):
        detail.tag_configure(lvl, foreground=color, font=(mono.actual("family"), 10, "bold"))
    detail.pack(side="left", fill="both", expand=True, pady=(px(8), 0))
    dsb.pack(side="right", fill="y", pady=(px(8), 0))
    pane.add(dframe, weight=2)

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
            lvl = results[int(iid)]["light"]
            tree.item(iid, tags=(f"L{lvl}s" if iid in sel else f"L{lvl}",))
        if sel:
            r = results[int(sel[0])]
            show_detail(format_result(r), r["light"])

    tree.bind("<<TreeviewSelect>>", on_select)
    show_detail("Select a row to see details.")

    def add_row(i, r, pos="end"):
        light = ("●  GO", "●  CHECK", "●  STOP")[r["light"]]
        note = " | ".join(t for _, t in sorted(r["reasons"], key=lambda x: -x[0]))
        ok, cats = r["ok"], r["cats"]
        tree.insert("", pos, iid=str(i), tags=(f"L{r['light']}",), values=(
            light, Path(r["file"]).name,
            len(r["extractions"]) if ok else "", sum(e["sim"] for e in r["extractions"]) if ok else "",
            *((("–" if r.get("quick") else f"{cats[c]:,}") if ok else "") for c in CONTENT_CATS),
            *((f"{r['files'][c]:,}" if ok else "") for c in FILE_CATS), note))

    # ---- run
    def worker(files, n_jobs, **kw):
        done = 0

        def running(fs):
            if fs:
                events.put(("progress", (done + 1, f"{done}/{len(files)} done  ·  checking:  "
                                         + ",  ".join(Path(f).name for f in fs))))

        try:
            for _, r in check_all(files, n_jobs, running=running, **kw):
                done += 1
                events.put(("result", r))
        finally:
            events.put(("done", None))

    def poll():
        try:
            while True:
                kind, data = events.get_nowait()
                if kind == "progress":
                    prog["value"] = data[0] - 1
                    status.set(data[1])
                elif kind == "result":
                    results.append(data)
                    add_row(len(results) - 1, data, sum(r["idx"] < data["idx"] for r in results))
                    prog["value"] = len(results)
                elif kind == "done":
                    status.set(footer(results))
                    btn_run.configure(state="normal")
                    for b in (btn_csv, btn_html):
                        b.configure(state="normal" if results else "disabled")
                    worst = max(range(len(results)), key=lambda i: (results[i]["light"], -results[i]["idx"]),
                                default=0)
                    first_bad = str(worst)
                    if results:
                        tree.selection_set(first_bad)
                        tree.see(first_bad)
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    def run():
        files, missing = collect_files(inputs, opt["recursive"].get())
        tree.delete(*tree.get_children())
        results.clear()
        show_detail("\n".join(f"Not found: {m}" for m in missing) or "Select a row to see details.")
        if not files:
            status.set("No UFDR files found. Add files or folders first.")
            return
        try:
            min_n = max(0, int(min_items.get()))
        except (tk.TclError, ValueError):
            min_n = MIN_ITEMS
            min_items.set(MIN_ITEMS)
        prog.configure(maximum=len(files), value=0)
        btn_run.configure(state="disabled")
        btn_csv.configure(state="disabled")
        btn_html.configure(state="disabled")
        run_settings.clear()
        run_settings.update({"Source": source.get(), "Min. items": min_n,
                             "ZIP integrity verified": "yes" if opt["verify"].get() else "no",
                             "Mode": "quick (extractions only)" if opt["quick"].get() else "full"})
        try:
            n_jobs = max(1, int(jobs.get()))
        except (tk.TclError, ValueError):
            n_jobs = default_jobs()
            jobs.set(n_jobs)
        threading.Thread(target=worker, daemon=True, args=(files, n_jobs), kwargs=dict(
            verify=opt["verify"].get(), source=source.get(), min_items=min_n, quick=opt["quick"].get())).start()
        poll()

    def export(kind):
        case = case_no.get().strip()
        stem = "sauce" + (f"_{re.sub(r'[^A-Za-z0-9._-]+', '_', case)}" if case else "")
        ext = ".html" if kind == "html" else ".csv"
        path = filedialog.asksaveasfilename(title=f"Save {kind.upper()}", defaultextension=ext,
                                            filetypes=[(kind.upper(), "*" + ext)], initialfile=stem + ext)
        if not path:
            return
        ordered = sorted(results, key=lambda r: r["idx"])  # input order
        try:
            if kind == "html":
                write_html(ordered, path, case, run_settings)
            else:
                write_csv(ordered, path, case)
            status.set(f"{kind.upper()} written: {path}")
        except OSError as e:
            messagebox.showerror("SAUCE", f"Could not write {kind.upper()}:\n{e}")

    btn_run.configure(command=run)
    btn_csv.configure(command=lambda: export("csv"))
    btn_html.configure(command=lambda: export("html"))
    root.mainloop()


# --------------------------------------------------------------------------- CLI

def main():
    import multiprocessing
    multiprocessing.freeze_support()  # parallel checks in the PyInstaller executables
    if len(sys.argv) == 1 or sys.argv[1:] == ["--gui"]:
        run_gui()
        return

    ap = argparse.ArgumentParser(description="SAUCE - SIM And UFDR Content Evaluator. Traffic light for UFDR import (integrity, extractions, SIM, content). "
                                             "Start without arguments (or with --gui) for the GUI.")
    ap.add_argument("paths", nargs="+", help="UFDR file(s) and/or folder(s) containing UFDRs")
    ap.add_argument("-r", "--recursive", action="store_true", help="search subfolders too")
    ap.add_argument("-s", "--summary", action="store_true", help="also list all item types with counts")
    ap.add_argument("--min-items", type=int, default=MIN_ITEMS,
                    help=f"'hardly any content' if messages, contacts, locations and calls are each below N (default {MIN_ITEMS})")
    ap.add_argument("-v", "--verify", action="store_true", help="verify ZIP integrity: read every member and check its CRC (slow on big UFDRs)")
    ap.add_argument("--source", choices=("auto", "xml", "db"), default="auto",
                    help="data source: report.xml, DbData/database.db, or auto (db if present - much faster)")
    ap.add_argument("-q", "--quick", action="store_true",
                    help="quick: only count extractions and detect SIMs, no content counts "
                         "(much faster; an empty SIM cannot be told from one with data)")
    ap.add_argument("-j", "--jobs", type=int, default=default_jobs(),
                    help=f"check N UFDRs in parallel (default {default_jobs()}; use 1 for a single slow disk)")
    ap.add_argument("--csv", type=Path, help="also write results to this CSV file")
    ap.add_argument("--html", type=Path, help="also write an HTML report to this file")
    ap.add_argument("--case", default="", help="optional case number (shown in CSV/HTML)")
    args = ap.parse_args()

    files, missing = collect_files(args.paths, args.recursive)
    for m in missing:
        print(f"Not found: {m}", file=sys.stderr)
    if not files:
        sys.exit("No .ufdr files found.")

    results = []
    for _, r in check_all(files, args.jobs, verify=args.verify, source=args.source,
                          min_items=args.min_items, quick=args.quick):
        print("\n" + format_result(r, full=args.summary), flush=True)
        results.append(r)
    results.sort(key=lambda r: r["idx"])  # exports in input order

    if args.csv:
        write_csv(results, args.csv, args.case)
        print(f"\nCSV written: {args.csv}")
    if args.html:
        write_html(results, args.html, args.case, {"Source": args.source, "Min. items": args.min_items,
                                                   "ZIP integrity verified": "yes" if args.verify else "no",
                                                   "Mode": "quick (extractions only)" if args.quick else "full"})
        print(f"HTML written: {args.html}")

    print("\n" + footer(results))
    sys.exit(max(r["light"] for r in results))  # 0 green, 1 yellow, 2 red


if __name__ == "__main__":
    main()
