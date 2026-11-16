#!/usr/bin/env python3
"""Create synthetic test UFDRs for SAUCE - one per traffic-light rule.

The file name starts with the expected light (green_/yellow_/red_).

  python3 make_test_ufdrs.py OUTDIR            create the test UFDRs
  python3 sauce.py OUTDIR --csv result.csv     run SAUCE on them
  python3 make_test_ufdrs.py --check result.csv  compare the lights with the expectation

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


def report_xml(extractions, models):
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
            f'<decodedData>{models_xml(models)}</decodedData></project>')


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
            z.writestr("report.xml", report_xml(exs, models))
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


def check(csv_path):
    expected_ok = True
    with open(csv_path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    if not rows:
        sys.exit("no rows in CSV")
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
    sys.exit(0 if expected_ok else 1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        check(sys.argv[2])
    elif len(sys.argv) == 2:
        create(sys.argv[1])
    else:
        sys.exit(__doc__)
