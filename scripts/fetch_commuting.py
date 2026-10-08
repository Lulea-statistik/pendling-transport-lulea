from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AM/AM0210/AM0210F/ArRegPend2"

NBR = {
    "2505": "Arvidsjaur",
    "2506": "Arjeplog",
    "2510": "Jokkmokk",
    "2513": "Överkalix",
    "2514": "Kalix",
    "2518": "Övertorneå",
    "2521": "Pajala",
    "2523": "Gällivare",
    "2560": "Älvsbyn",
    "2580": "Luleå",
    "2581": "Piteå",
    "2582": "Boden",
    "2583": "Haparanda",
    "2584": "Kiruna",
}
FOCUS = {"2580", "2582", "2581", "2560", "2514"}


def norm(s: str) -> str:
    return (
        s.lower()
        .replace("ä", "a")
        .replace("å", "a")
        .replace("ö", "o")
        .replace("é", "e")
    )


def get_json(url: str):
    req = Request(url, headers={"User-Agent": "pendling-transport-lulea/1.0"})
    with urlopen(req, timeout=60) as r:
        return json.load(r)


def post_json(url: str, payload: dict) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "pendling-transport-lulea/1.0",
        },
    )
    with urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8-sig")


def find_var(metadata: dict, *needles: str) -> dict:
    ns = [norm(x) for x in needles]
    for v in metadata["variables"]:
        hay = norm(str(v.get("text", "")) + " " + str(v.get("code", "")))
        if all(n in hay for n in ns):
            return v
    raise KeyError(f"Kan inte hitta variabel: {needles}")


def code_from_label(value: str) -> str:
    m = re.match(r"\s*(\d{4})\b", str(value))
    return m.group(1) if m else ""


def municipality_values(variable: dict) -> list[str]:
    out = []
    for value, label in zip(variable.get("values", []), variable.get("valueTexts", [])):
        code = str(value)
        label_code = code_from_label(label)
        if code in NBR:
            out.append(code)
        elif label_code in NBR:
            out.append(code)
    return out


def main():
    metadata = get_json(API_URL)
    sex = find_var(metadata, "kon")
    residence = find_var(metadata, "bostad", "kommun")
    workplace = find_var(metadata, "arbets", "kommun")
    year = find_var(metadata, "ar")

    res_values = municipality_values(residence)
    work_values = municipality_values(workplace)
    if len(res_values) != 14 or len(work_values) != 14:
        raise RuntimeError(
            f"Förväntade 14 Norrbottenskommuner men fick bostad={len(res_values)}, arbete={len(work_values)}"
        )

    payload = {
        "query": [
            {"code": sex["code"], "selection": {"filter": "item", "values": sex["values"]}},
            {"code": residence["code"], "selection": {"filter": "item", "values": res_values}},
            {"code": workplace["code"], "selection": {"filter": "item", "values": work_values}},
            {"code": year["code"], "selection": {"filter": "item", "values": year["values"]}},
        ],
        "response": {"format": "csv"},
    }

    text = post_json(API_URL, payload)
    sample = text[:5000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = list(reader)
    if not rows:
        raise RuntimeError("SCB returnerade inga rader")

    headers = reader.fieldnames or []

    def col(*needles: str) -> str:
        ns = [norm(x) for x in needles]
        for h in headers:
            if all(n in norm(h) for n in ns):
                return h
        raise KeyError(f"Kolumn saknas: {needles}. Kolumner: {headers}")

    c_sex = col("kon")
    c_res = col("bostad", "kommun")
    c_work = col("arbets", "kommun")
    c_year = col("ar")
    value_candidates = [
        h for h in headers
        if h not in {c_sex, c_res, c_work, c_year}
    ]
    if len(value_candidates) != 1:
        raise RuntimeError(f"Kan inte entydigt hitta värdekolumn: {value_candidates}")
    c_value = value_candidates[0]

    out = []
    for r in rows:
        rc = code_from_label(r[c_res])
        wc = code_from_label(r[c_work])
        if rc not in NBR or wc not in NBR:
            continue
        raw = str(r[c_value]).strip().replace(" ", "").replace(",", ".")
        try:
            value = int(float(raw)) if raw not in {"", "..", ".", "-"} else None
        except ValueError:
            value = None
        out.append({
            "year": int(r[c_year]),
            "sex": r[c_sex],
            "residence_code": rc,
            "residence": NBR[rc],
            "workplace_code": wc,
            "workplace": NBR[wc],
            "employed": value,
            "residence_focus": "1" if rc in FOCUS else "0",
            "workplace_focus": "1" if wc in FOCUS else "0",
        })

    out.sort(key=lambda x: (x["year"], x["sex"], x["residence_code"], x["workplace_code"]))

    fieldnames = [
        "year", "sex", "residence_code", "residence",
        "workplace_code", "workplace", "employed",
        "residence_focus", "workplace_focus",
    ]
    for path in [Path("data/commuting.csv"), Path("docs/data/commuting.csv")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(out)

    meta = {
        "source": "SCB Statistikdatabasen",
        "table": "ArRegPend2",
        "api": API_URL,
        "years": sorted({r["year"] for r in out}),
        "sex": sorted({r["sex"] for r in out}),
        "municipalities": [{"code": c, "name": NBR[c], "focus": c in FOCUS} for c in sorted(NBR)],
        "rows": len(out),
    }
    for path in [Path("data/meta.json"), Path("docs/data/meta.json")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Skrev {len(out)} rader, år {meta['years']}, kön {meta['sex']}")


if __name__ == "__main__":
    main()
