#!/usr/bin/env python3
"""Create synthetic test UFDRs for SAUCE - one per traffic-light rule.

The file name starts with the expected light (green_/yellow_/red_).

  python3 make_test_ufdrs.py OUTDIR            create the test UFDRs
  python3 sauce.py OUTDIR --csv OUTDIR/result.csv -p -a --export-dir OUTDIR/exports   run SAUCE on them
  python3 make_test_ufdrs.py --check OUTDIR/result.csv  compare the lights (figures, apps, exports) with the expectation

The report.xml follows the structure of real Cellebrite reports (namespace, sourceExtractions,
"Extraction Data" metadata, decodedData/modelType/model with extractionId, chats with nested
InstantMessages), but contains no real data.
"""
import csv
import json
import sys
import zipfile
from pathlib import Path

NS = "http://pa.cellebrite.com/report/2.0"
_uid = 0


def uid():
    global _uid
    _uid += 1
    return f"00000000-0000-4000-8000-{_uid:012d}"


def extraction(i, name, etype, device):
    return {"id": str(i), "name": name, "type": etype, "device": device}


def source_xml(app):
    return f'<field name="Source" type="String"><value type="String"><![CDATA[{app}]]></value></field>'


def ts_xml(day):
    """TimeStamp field: 2021-01-01 10:00 +01:00 plus day days; day None: placeholder 0001-01-01 (ignored)."""
    if day is None:
        value = "0001-01-01T00:00:00.000+00:00"
    else:
        value = f"2021-{1 + day // 28:02d}-{1 + day % 28:02d}T10:00:00.000+01:00"
    return (f'<field name="TimeStamp" type="TimeStamp"><value type="TimeStamp" format="TimeStampKnown" '
            f'formattedTimestamp="x">{value}</value></field>')


def models_xml(models):
    """models: list of (type, extraction id, count[, app]).

    Chat -> 1 chat with count messages (message k on day k) of app:
      "App"   Source on every message, before the messages ("WhatsApp")
      "App*"  Source only on the chat, after the messages: messages inherit it ("Signal*")
    The first message of each chat is also listed at top level (same id, as in real reports),
    the last one has a placeholder timestamp (0001-01-01, ignored).
    SMS/MMS/Email: TimeStamp on day k, Source only if app is given.
    """
    by_type = {}
    for mtype, ext, n, *app in models:
        by_type.setdefault(mtype, []).append((ext, n, app[0] if app else None))
    out, top_level = [], []
    for mtype, entries in by_type.items():
        out.append(f'<modelType type="{mtype}">')
        for ext, n, app in entries:
            if mtype == "Chat":
                app = app or "WhatsApp"
                inherit = app.endswith("*")
                app = app.rstrip("*")
                msgs = []
                for k in range(n):
                    m = (f'<model type="InstantMessage" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                         + ("" if inherit else source_xml(app))
                         + ts_xml(k if k < n - 1 or n == 1 else None)
                         + f'<field name="Body" type="String"><value type="String"><![CDATA[message {k} '
                           f'<field name="Source">fake</field>]]></value></field>'
                         + '<field name="Status" type="String" />'
                         + f'<modelField name="From" type="Party"><model type="Party" id="{uid()}" '
                           f'deleted_state="Intact">{ts_xml(300)}</model></modelField>'
                         + '</model>')
                    msgs.append(m)
                if msgs:
                    top_level.append(msgs[0])
                out.append(f'<model type="Chat" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                           + ("" if inherit else source_xml(app))
                           + f'<multiModelField name="Messages" type="InstantMessage">{"".join(msgs)}'
                           f'</multiModelField>' + (source_xml(app) if inherit else "") + '</model>')
            elif mtype in ("SMS", "MMS", "Email"):
                out += [f'<model type="{mtype}" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                        + (source_xml(app) if app else "") + ts_xml(k) + '</model>' for k in range(n)]
            else:
                out += [f'<model type="{mtype}" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                        f'<field name="Name" type="String"><value type="String"><![CDATA[{mtype} {k}]]></value>'
                        f'</field></model>' for k in range(n)]
        out.append("</modelType>")
    if top_level:
        out.append('<modelType type="InstantMessage">' + "".join(top_level) + "</modelType>")
    return "".join(out)


def _pw_field(name, value, b64=False):
    import base64
    if b64:
        value = base64.b64encode(value if isinstance(value, bytes) else value.encode()).decode()
    fmt = ' format="Base64String"' if b64 else ""
    return f'<field name="{name}" type="String"><value type="String"{fmt}><![CDATA[{value}]]></value></field>'


# (Type, Data, base64?) - fake values; exported: Default/Secret, printable, <= 64 chars, unique
PASSWORDS = [
    ("Default", "fake-pass-1", True),
    ("Default", "fake pass 2 äöü", False),
    ("Secret", "fake-secret-3", True),
    ("Default", "fake-pass-1", True),          # duplicate: once in the list
    ("Key", "fake-key-not-exported", True),
    ("Token", "fake-token-not-exported", True),
    ("Secret", b"\x00\x01binary", True),       # binary: not exported
    ("Secret", "x" * 65, True),               # too long: not exported
    ("Secret", "0a1b2c3d-0000-4000-8000-00000000abcd", True),   # uuid
    ("Secret", "ab12" * 8, True),                                # hex >= 32: hash / key
    ("Secret", '{"fake": 1}', True),                             # json
    ("Secret", "https://example.org/x", True),                   # url
    ("Secret", "eyJhbGciOiJub25lIn0.eyJmYWtlIjoxfQ.", True),     # jwt
    ("Secret", "1234", True),                                    # digits (PIN): exported
]
WIFI = [("FakeNet", "fake-wifi-4"), ("OpenNet", None), ("HexNet", "cd34" * 16)]  # 64 hex digits: WPA key, exported
EXPECT_PASSWORDS = {"green_phone.ufdr": ["fake-pass-1", "fake pass 2 äöü", "fake-secret-3", "1234", "fake-wifi-4",
                                         "cd34" * 16]}
EXPECT_EXCLUDED = {"green_phone.ufdr": ["longer than 64", "uuid", "hex", "json", "url", "jwt"]}


def passwords_xml(ext="0"):
    pw = "".join(f'<model type="Password" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                 + _pw_field("Source", "Test App") + _pw_field("Account", "fake@example.org")
                 + _pw_field("Data", data, b64) + f'<field name="Type" type="PasswordType"><value type="PasswordType">'
                 f'<![CDATA[{typ}]]></value></field></model>' for typ, data, b64 in PASSWORDS)
    wifi = "".join(f'<model type="WirelessNetwork" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                   + _pw_field("SSId", ssid) + (_pw_field("Password", p) if p else "") + "</model>"
                   for ssid, p in WIFI)
    return f'<modelType type="Password">{pw}</modelType><modelType type="WirelessNetwork">{wifi}</modelType>'


def _entry_xml(mtype, domain, value):
    return (f'<model type="{mtype}" id="{uid()}" deleted_state="Intact" extractionId="0">'
            + _pw_field("Category", "") + _pw_field("Value", value) + _pw_field("Domain", domain) + "</model>")


def accounts_xml():
    """2 accounts, the second with a related account nested in it (RelatedModels): 3 exported, 2 counted."""
    related = ('<multiModelField name="RelatedModels" type="UserAccount">'
               f'<model type="UserAccount" id="{uid()}" deleted_state="Intact" extractionId="0">'
               + _pw_field("Source", "Accounts") + _pw_field("Username", "fake.user")
               + _pw_field("ServiceType", "org.example.chat") + "</model></multiModelField>")
    return ('<modelType type="UserAccount">'
            f'<model type="UserAccount" id="{uid()}" deleted_state="Intact" extractionId="0">'
            + _pw_field("Source", "Test Chat") + _pw_field("Name", "Fake User") + _pw_field("Username", "fake.user")
            + '<multiModelField name="Entries" type="ContactEntry">'
            + _entry_xml("PhoneNumber", "Phone", "+49 000 000")
            + _entry_xml("EmailAddress", "Email", "fake@example.org")
            + _entry_xml("UserID", "User ID", "id-2") + _entry_xml("UserID", "User ID", "id-1")
            + _entry_xml("ProfilePicture", "Profile Picture", "https://example.org/pic.jpg")
            + "</multiModelField>" + ts_xml(0).replace("TimeStamp\"", "TimeCreated\"", 1) + "</model>"
            f'<model type="UserAccount" id="{uid()}" deleted_state="Deleted" extractionId="0">'
            + _pw_field("Source", "Accounts") + _pw_field("Username", "fake@example.org")
            + _pw_field("ServiceType", "com.example") + related + "</model></modelType>")


# expected rows of <ufdr>_accounts.csv (sorted by source, username): source, service, name, username, email,
# phone, user_id, created_utc, deleted
EXPECT_ACCOUNTS = {"green_phone.ufdr": [
    ("Accounts", "org.example.chat", "", "fake.user", "", "", "", "", "Intact"),
    ("Accounts", "com.example", "", "fake@example.org", "", "", "", "", "Deleted"),
    ("Test Chat", "", "Fake User", "fake.user", "fake@example.org", "+49 000 000", "id-1 | id-2",
     "2021-01-01 09:00:00", "Intact"),
]}

# files under files/<category>/ (Cellebrite's categories): name -> size
FILES = {"files/Image/a.jpg": 1000, "files/Image/b.png": 2500, "files/Audio/c.opus": 300, "files/Text/d.txt": 10}
# expected columns of the results CSV (figures and files)
EXPECT_COLUMNS = {"green_phone.ufdr": {"chats": "2", "accounts": "2", "installed_apps": "0", "wifi_networks": "3",
                                       "files_total": "4", "files_bytes_total": "3810", "image_files": "2",
                                       "image_bytes": "3500", "audio_files": "1", "video_files": "0",
                                       "text_files": "1", "accounts_exported": "3"}}
# expected rows of result_apps.csv: (file, app, messages, first, last)
EXPECT_APP_ROWS = {"green_phone.ufdr": [("WhatsApp", "15", "2021-01-01 09:00", "2021-01-14 09:00"),
                                        ("Signal", "10", "2021-01-01 09:00", "2021-01-09 09:00"),
                                        ("SMS", "10", "2021-01-01 09:00", "2021-01-10 09:00")]}


def report_xml(extractions, models, extra=""):
    exs = "".join(
        f'<extractionInfo id="{e["id"]}" name="{e["name"]}" isCustomName="False" type="{e["type"]}" '
        f'deviceName="{e["device"]}" fullName="{e["device"]}" index="{e["id"]}" IsPartialData="False" />'
        for e in extractions)
    meta = "".join(
        f'<item name="ExtractionType" sourceExtraction="{e["id"]}" systemtype="System.String">'
        f'<![CDATA[{e["name"]}]]></item>' for e in extractions)
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<project id="{uid()}" name="Test" reportVersion="8.5" extractionType="{extractions[0]["type"] if extractions else ""}" '
            f'xmlns="{NS}"><sourceExtractions>{exs}</sourceExtractions>'
            f'<metadata section="Extraction Data">{meta}</metadata>'
            f'<decodedData>{models_xml(models)}{extra}</decodedData></project>')


PHONE = extraction(0, "File System", "FileSystem", "Test Phone")
CONTENT = [("Contact", "0", 40), ("Chat", "0", 15, "WhatsApp"), ("Chat", "0", 10, "Signal*"), ("SMS", "0", 10),
           ("Location", "0", 15), ("Call", "0", 30)]

# expected app overview (CSV columns apps / first_message_utc / last_message_utc), times in UTC:
# WhatsApp days 0-13 (last message: placeholder), Signal days 0-8, SMS days 0-9
EXPECT_APPS = {
    "green_phone.ufdr": ("WhatsApp 15 (2021-01-01 09:00 – 2021-01-14 09:00) | "
                         "Signal 10 (2021-01-01 09:00 – 2021-01-09 09:00) | "
                         "SMS 10 (2021-01-01 09:00 – 2021-01-10 09:00)",
                         "2021-01-01 09:00", "2021-01-14 09:00"),
    "yellow_empty_device.ufdr": ("", "", ""),
}

CASES = {
    # --- green
    "green_phone": ([PHONE], CONTENT),
    "green_calls_only": ([extraction(0, "Logical", "Logical", "Feature Phone")],
                         [("Contact", "0", 2), ("Call", "0", 30)]),
    # --- yellow
    "yellow_memory_card": ([PHONE, extraction(1, "Memory Card", "FileSystem", "SD Card")], CONTENT),
    "yellow_sim_with_data": ([PHONE, extraction(1, "SIM Card", "Logical", "SIM")],
                             CONTENT + [("SMS", "1", 4), ("Contact", "1", 12)]),
    "yellow_hardly_any_content": ([PHONE], [("Contact", "0", 1), ("Call", "0", 2), ("InstalledApplication", "0", 50)]),
    "yellow_empty_device": ([PHONE], []),
    # --- red
    "red_empty_sim": ([PHONE, extraction(1, "SIM Card", "Logical", "SIM")],
                      CONTENT + [("SIMData", "1", 3), ("DeviceInfoEntry", "1", 2)]),
    "red_only_empty_sim": ([extraction(0, "SIM Card", "Logical", "SIM")], [("SIMData", "0", 3)]),
    "red_three_extractions": ([PHONE, extraction(1, "Memory Card", "FileSystem", "SD Card"),
                               extraction(2, "SIM Card", "Logical", "SIM")],
                              CONTENT + [("SMS", "2", 5)]),
}


def create(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, (exs, models) in CASES.items():
        with zipfile.ZipFile(out / f"{name}.ufdr", "w", zipfile.ZIP_DEFLATED) as z:
            phone = name == "green_phone"
            z.writestr("report.xml", report_xml(exs, models, passwords_xml() + accounts_xml() if phone else ""))
            if phone:
                z.writestr("files/Image/", "")  # directory entry: not counted
                for fname, size in FILES.items():
                    z.writestr(fname, b"x" * size)
    # warning: database.json lists more extractions than report.xml
    with zipfile.ZipFile(out / "yellow_database_json_mismatch.ufdr", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.xml", report_xml([PHONE], CONTENT))
        z.writestr("DbData/database.json", json.dumps({"SourceExtractionIds": [uid(), uid()]}))
    # defects
    good = (out / "green_phone.ufdr").read_bytes()
    (out / "red_defect_truncated.ufdr").write_bytes(good[: len(good) // 2])
    (out / "red_defect_not_a_zip.ufdr").write_bytes(b"this is not a zip file\n")
    with zipfile.ZipFile(out / "red_defect_no_report.ufdr", "w") as z:
        z.writestr("files/readme.txt", "no report.xml and no database.db in here")
    with zipfile.ZipFile(out / "red_defect_broken_xml.ufdr", "w") as z:
        z.writestr("report.xml", report_xml([PHONE], CONTENT)[:-200])
    names = sorted(p.name for p in out.glob("*.ufdr"))
    print(f"{len(names)} test UFDRs written to {out}:")
    for n in names:
        print("  " + n)


def _rows(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def _report(ok, name, what, want, got):
    print(f"{'OK  ' if ok else 'FAIL'} {name:<40} {what}" + ("" if ok else f"\n       expected {want}"
                                                                       f"\n       got      {got}"))
    return ok


def check(csv_path):
    expected_ok = True
    rows = _rows(csv_path)
    if not rows:
        sys.exit("no rows in CSV")
    apps_csv = Path(csv_path).with_name(Path(csv_path).stem + "_apps.csv")
    app_rows = _rows(apps_csv) if apps_csv.exists() else []
    exports = Path(csv_path).parent / "exports"
    for row in rows:
        name = Path(row["file"]).name
        want = name.split("_", 1)[0].upper()
        got = row["light"]
        ok = got == want
        expected_ok &= ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:<40} expected {want:<6} got {got}")
        if name in EXPECT_APPS:
            want_apps = EXPECT_APPS[name]
            got_apps = (row["apps"], row["first_message_utc"], row["last_message_utc"])
            ok = got_apps == want_apps
            expected_ok &= ok
            print(f"{'OK  ' if ok else 'FAIL'} {name:<40} apps" + ("" if ok else f"\n       expected {want_apps}"
                                                                         f"\n       got      {got_apps}"))
        if name in EXPECT_COLUMNS:
            want = EXPECT_COLUMNS[name]
            got = {k: row.get(k) for k in want}
            expected_ok &= _report(got == want, name, "figures and files", want, got)
        if name in EXPECT_APP_ROWS:
            want = EXPECT_APP_ROWS[name]
            got = [(r["app"], r["messages"], r["first_message_utc"], r["last_message_utc"])
                   for r in app_rows if Path(r["file"]).name == name]
            expected_ok &= _report(got == want, name, "apps CSV", want, got)
        acc_file = exports / (Path(name).stem + "_accounts.csv")
        if name in EXPECT_ACCOUNTS and acc_file.exists():  # only if run with -a --export-dir <csv dir>/exports
            want = EXPECT_ACCOUNTS[name]
            got = [tuple(r[c] for c in ("source", "service", "name", "username", "email", "phone", "user_id",
                                        "created_utc", "deleted")) for r in _rows(acc_file)]
            expected_ok &= _report(got == want, name, "accounts", want, got)
        pw_file = exports / (Path(name).stem + "_passwords.txt")
        if name in EXPECT_PASSWORDS and pw_file.exists():  # only if run with -p --export-dir <csv dir>/exports
            got_pw = pw_file.read_text(encoding="utf-8").splitlines()
            ctx = pw_file.with_name(pw_file.stem + "_context.csv")
            with open(ctx, encoding="utf-8-sig") as fh:
                excluded = [r["excluded"] for r in csv.DictReader(fh, delimiter=";") if r["excluded"]]
            ok = (got_pw == EXPECT_PASSWORDS[name] and row["passwords_exported"] == str(len(got_pw))
                  and excluded == EXPECT_EXCLUDED[name])
            expected_ok &= ok
            print(f"{'OK  ' if ok else 'FAIL'} {name:<40} passwords" + (
                "" if ok else f"\n       expected {EXPECT_PASSWORDS[name]} excluded {EXPECT_EXCLUDED[name]}"
                              f"\n       got      {got_pw} excluded {excluded}"))
    sys.exit(0 if expected_ok else 1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        check(sys.argv[2])
    elif len(sys.argv) == 2:
        create(sys.argv[1])
    else:
        sys.exit(__doc__)
