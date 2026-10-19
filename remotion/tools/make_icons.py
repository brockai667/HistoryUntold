#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PriceTrap - vygeneruje src/icons.ts a icons.json z vendor/lucide/*.svg (lucide, licencia ISC).

    python -I tools/make_icons.py

Stiahnute SVG su len DATA: skript ich nespusta. Kazdy subor sa nacita ako XML (bez DOCTYPE/ENTITY),
povolia sa len znate kresliace prvky a atributy (path, circle, rect, ...) a z nich sa zlozi vnutorny
obsah <svg viewBox="0 0 24 24">. Subor s neznamym prvkom/atributom alebo podozrivou hodnotou sa
PRESKOCI a vypise sa (nikdy sa ticho nevlozi do videa).

Vystup:
  src/icons.ts   export const ICONS: Record<string, string>   meno -> vnutorny SVG obsah
  icons.json     pole dostupnych mien + "car", "car-red", "car-fly", "none"   (cita ho aj autor/lint)

Chybajuce mena (404 pri stahovani) sa vypisu na konci.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "vendor", "lucide")

# Zoznam z SPEC.md (sekcia Ikony); poradie sa zachova aj v icons.json.
NAMES = """
coffee cup-soda popcorn pizza sandwich cake cake-slice ice-cream-cone candy wine beer apple egg utensils
smartphone laptop tv headphones watch camera gamepad-2 printer plane bike bus train-front fuel house hotel bed
armchair lamp sofa dumbbell pill stethoscope scissors shirt gem crown gift ticket clapperboard music book-open
graduation-cap shopping-cart shopping-bag store package truck tag receipt credit-card banknote coins piggy-bank
wallet key lock percent trophy star newspaper mail droplets zap wifi flame rocket glasses footprints umbrella
phone refrigerator washing-machine microwave bath baby dog cat flower-2 trees tent ship sailboat anchor scale
hammer wrench paintbrush palette briefcase building-2 landmark shield heart
""".split()

SPECIAL = ["car", "car-red", "car-fly", "none"]

ALLOWED_TAGS = {"path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "g"}
ALLOWED_ATTRS = {
    "d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "points",
    "transform", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
    "opacity", "fill-opacity", "stroke-opacity", "fill-rule", "clip-rule",
}
SAFE_VALUE = re.compile(r"^[A-Za-z0-9\s.,\-+#%()]*$")  # ziadne <, >, ", ', &, ;, :, /
BAD_VALUE = re.compile(r"url\s*\(|javascript|data\s*:|expression", re.I)


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def clean_elem(el):
    """Vrati serializovany prvok (atributy v jednoduchych uvodzovkach) alebo vyhodi ValueError."""
    tag = local(el.tag)
    if tag not in ALLOWED_TAGS:
        raise ValueError(f"neznamy prvok <{tag}>")
    attrs = []
    for k, v in el.attrib.items():
        k = local(k)
        if k not in ALLOWED_ATTRS:
            raise ValueError(f"neznamy atribut {k} na <{tag}>")
        v = re.sub(r"\s+", " ", v).strip()
        if not SAFE_VALUE.match(v) or BAD_VALUE.search(v):
            raise ValueError(f"podozriva hodnota atributu {k}")
        attrs.append(f"{k}='{v}'")
    if (el.text or "").strip() or any((c.tail or "").strip() for c in el):
        raise ValueError(f"neocakavany text v <{tag}>")
    kids = "".join(clean_elem(c) for c in el)
    head = tag + ("" if not attrs else " " + " ".join(attrs))
    return f"<{head}>{kids}</{tag}>" if kids else f"<{head}/>"


def inner_svg(path):
    raw = open(path, "rb").read().decode("utf-8")
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", raw, re.I):
        raise ValueError("DOCTYPE/ENTITY nepovolene")
    root = ET.fromstring(raw)
    if local(root.tag) != "svg":
        raise ValueError("koren nie je <svg>")
    if root.attrib.get("viewBox") != "0 0 24 24":
        raise ValueError(f"viewBox {root.attrib.get('viewBox')!r} != '0 0 24 24'")
    if (root.text or "").strip():
        raise ValueError("neocakavany text v <svg>")
    out = "".join(clean_elem(c) for c in root)
    if not out:
        raise ValueError("prazdna ikona")
    return out


def main():
    icons, missing, invalid = {}, [], []
    for n in NAMES:
        p = os.path.join(SRC_DIR, n + ".svg")
        if not os.path.isfile(p):
            missing.append(n)
            continue
        try:
            icons[n] = inner_svg(p)
        except (ValueError, ET.ParseError, UnicodeDecodeError) as e:
            invalid.append(f"{n} ({e})")

    lines = [
        "// GENEROVANE tools/make_icons.py z vendor/lucide/*.svg (lucide, licencia ISC - vendor/lucide/LICENSE). NEEDITUJ.",
        "// meno -> vnutorny obsah <svg viewBox=\"0 0 24 24\"> (len kresliace prvky); vykresluje ich IconArt v Paper.tsx.",
        "export const ICONS: Record<string, string> = {",
    ]
    for n, inner in icons.items():
        lines.append(f"  {json.dumps(n)}: {json.dumps(inner)},")
    lines.append("};")
    with open(os.path.join(ROOT, "src", "icons.ts"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    with open(os.path.join(ROOT, "icons.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(list(icons) + SPECIAL, f, indent=1)
        f.write("\n")

    print(f"icons: {len(icons)} ikon -> src/icons.ts, icons.json (+ {', '.join(SPECIAL)})")
    if missing:
        print("CHYBAJU (nestiahnute / 404): " + ", ".join(missing))
    if invalid:
        print("PRESKOCENE (neplatne): " + "; ".join(invalid))
    return 0 if icons else 1


if __name__ == "__main__":
    sys.exit(main())
