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


def models_xml(models):
    """models: list of (type, extraction id, count). Chat -> 1 chat with count messages."""
    by_type = {}
    for mtype, ext, n in models:
        by_type.setdefault(mtype, []).append((ext, n))
    out = []
    for mtype, entries in by_type.items():
        out.append(f'<modelType type="{mtype}">')
        for ext, n in entries:
            if mtype == "Chat":
                msgs = "".join(
                    f'<model type="InstantMessage" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                    f'<field name="Body" type="String"><value type="String"><![CDATA[message {k}]]></value></field>'
                    f'</model>' for k in range(n))
                out.append(f'<model type="Chat" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                           f'<multiModelField name="Messages" type="InstantMessage">{msgs}</multiModelField></model>')
            else:
                out += [f'<model type="{mtype}" id="{uid()}" deleted_state="Intact" extractionId="{ext}">'
                        f'<field name="Name" type="String"><value type="String"><![CDATA[{mtype} {k}]]></value>'
                        f'</field></model>' for k in range(n)]
        out.append("</modelType>")
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
CONTENT = [("Contact", "0", 40), ("Chat", "0", 25), ("SMS", "0", 10), ("Location", "0", 15), ("Call", "0", 30)]

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
    sys.exit(0 if expected_ok else 1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        check(sys.argv[2])
    elif len(sys.argv) == 2:
        create(sys.argv[1])
    else:
        sys.exit(__doc__)
