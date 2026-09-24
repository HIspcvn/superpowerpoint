#!/usr/bin/env python3
"""Read-only, standard-library checks for an OOXML PowerPoint package.

Exit 0: checks pass (warnings may remain). Exit 1: failed declared checks or
structural errors. Exit 2: argument, I/O, ZIP, or bounded-parsing safety failure.
This is package evidence, not a rendering, visual, accessibility, or factual audit.
"""

from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import sys
import urllib.parse
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET


P_NS = {"http://schemas.openxmlformats.org/presentationml/2006/main",
        "http://purl.oclc.org/ooxml/presentationml/main"}
A_NS = {"http://schemas.openxmlformats.org/drawingml/2006/main",
        "http://purl.oclc.org/ooxml/drawingml/main"}
C_NS = {"http://schemas.openxmlformats.org/drawingml/2006/chart",
        "http://purl.oclc.org/ooxml/drawingml/chart"}
R_NS = {"http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "http://purl.oclc.org/ooxml/officeDocument/relationships"}
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
CHART_CT = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
PRESENTATION_CTS = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    "application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml",
    "application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml",
    "application/vnd.ms-powerpoint.slideshow.macroEnabled.main+xml",
    "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml",
    "application/vnd.ms-powerpoint.template.macroEnabled.main+xml",
}
EMU_PER_INCH = 914400
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_XML_BYTES = 16 * 1024 * 1024
MAX_TOTAL_XML_BYTES = 128 * 1024 * 1024
LIMITATIONS = [
    "Package checks do not render slides or validate visual quality, text overflow, facts, accessibility, or full editability.",
    "Bounds checks cover direct top-level objects with explicit, unrotated geometry; group transforms, rotations, effects, and inherited layout geometry are not resolved.",
    "Font checks cover explicit sizes in slide XML only; inherited theme/master/layout fonts, rendered fitting, and notes fonts are not resolved.",
    "Native chart evidence requires a slide chart element, an internal chart relationship, a chart content type, and a chartSpace root; chart data correctness and embedded workbook editability are not validated.",
    "External relationship targets are listed but never opened; macros and embedded objects are never executed and ZIP entries are never extracted.",
]


class PackageFailure(Exception):
    """Unreadable package or explicit safety bound exceeded."""


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def is_tag(element: ET.Element, names: set[str], local: str) -> bool:
    return element.tag in {"{" + ns + "}" + local for ns in names}


def rel_attr(element: ET.Element, name: str) -> str | None:
    return next((element.get("{" + ns + "}" + name) for ns in R_NS
                 if element.get("{" + ns + "}" + name) is not None), None)


def direct(element: ET.Element, local: str) -> ET.Element | None:
    return next((child for child in element if tag_name(child) == local), None)


def relationship_source(part: str) -> str | None:
    if part == "_rels/.rels":
        return ""
    directory, name = posixpath.split(part)
    if posixpath.basename(directory) != "_rels" or not name.endswith(".rels"):
        return None
    return posixpath.join(posixpath.dirname(directory), name[:-5])


def target_part(source: str, target: str) -> str:
    """Resolve OPC targets without touching the filesystem or network."""
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.query:
        raise ValueError("internal target has a URI scheme, host, or query")
    decoded = urllib.parse.unquote(parsed.path, encoding="utf-8", errors="strict")
    if "\\" in decoded or "\x00" in decoded:
        raise ValueError("internal target contains a backslash or NUL")
    if not decoded:
        if source and parsed.fragment:
            return source
        raise ValueError("internal target has no part path")
    combined = decoded.lstrip("/") if decoded.startswith("/") else posixpath.join(posixpath.dirname(source), decoded)
    normalized = posixpath.normpath(combined)
    if normalized in {".", ".."} or normalized.startswith("../"):
        raise ValueError("internal target escapes the package root")
    return normalized


def slide_text(root: ET.Element) -> str:
    paragraphs = []
    for paragraph in root.iter():
        if is_tag(paragraph, A_NS, "p"):
            text = "".join(node.text or "" for node in paragraph.iter() if is_tag(node, A_NS, "t"))
            if text:
                paragraphs.append(text)
    return "\n".join(paragraphs)


class Inspector:
    def __init__(self, path: Path, min_font_pt: float | None = None):
        self.path = path
        self.min_font_pt = min_font_pt
        self.report = {
            "schema_version": 1,
            "package": {"path": str(path), "slide_count": 0, "slide_size_emu": None, "slide_size_inches": None},
            "slides": [], "external_links": [], "checks": [],
            "errors": [], "warnings": [], "limitations": LIMITATIONS[:], "ok": False,
        }
        self.zip: zipfile.ZipFile
        self.names: set[str] = set()
        self.xml_cache: dict[str, ET.Element | None] = {}
        self.xml_bytes = 0
        self.rels: dict[str, dict[str, dict]] = {}
        self.defaults: dict[str, str] = {}
        self.overrides: dict[str, str] = {}

    def issue(self, severity: str, code: str, message: str, **context) -> None:
        self.report[severity].append({"code": code, "message": message, **context})

    def read_xml(self, part: str) -> ET.Element | None:
        if part in self.xml_cache:
            return self.xml_cache[part]
        self.xml_cache[part] = None
        if part not in self.names:
            self.issue("errors", "missing_part", "Required XML part is missing.", part=part)
            return None
        info = self.zip.getinfo(part)
        if info.file_size > MAX_XML_BYTES:
            raise PackageFailure(f"XML part exceeds {MAX_XML_BYTES} bytes: {part}")
        self.xml_bytes += info.file_size
        if self.xml_bytes > MAX_TOTAL_XML_BYTES:
            raise PackageFailure("Total XML parsing byte limit exceeded.")
        try:
            data = self.zip.read(part)
        except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error) as exc:
            raise PackageFailure(f"Cannot read ZIP part {part}: {exc}") from exc
        # Removing NUL bytes also detects these tokens in UTF-16/UTF-32 XML.
        if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.I):
            raise PackageFailure(f"DTD/entity declarations are not allowed: {part}")
        try:
            root = ET.fromstring(data)
        except (ET.ParseError, ValueError, LookupError) as exc:
            self.issue("errors", "malformed_xml", str(exc), part=part)
            return None
        self.xml_cache[part] = root
        return root

    def content_type(self, part: str) -> str | None:
        return self.overrides.get(part, self.defaults.get(posixpath.splitext(part)[1][1:].lower()))

    def read_content_types(self) -> None:
        root = self.read_xml("[Content_Types].xml")
        if root is None:
            return
        if root.tag != "{" + CT_NS + "}Types":
            self.issue("errors", "invalid_content_types", "Content types root has an unexpected name or namespace.")
            return
        for entry in root:
            content_type = entry.get("ContentType", "")
            if entry.tag == "{" + CT_NS + "}Default":
                self.defaults[entry.get("Extension", "").lower()] = content_type
            elif entry.tag == "{" + CT_NS + "}Override":
                try:
                    part = target_part("", entry.get("PartName", ""))
                except (ValueError, UnicodeError) as exc:
                    self.issue("errors", "invalid_content_type_part", str(exc))
                    continue
                self.overrides[part] = content_type

    def read_relationships(self) -> None:
        for part in sorted(name for name in self.names if name.endswith(".rels")):
            source = relationship_source(part)
            if source is None:
                self.issue("errors", "invalid_relationship_part", "Relationship part is outside an OPC _rels directory.", part=part)
                continue
            if source and source not in self.names:
                self.issue("errors", "missing_relationship_source", "Relationship source part is missing.", part=part, source_part=source)
            root = self.read_xml(part)
            if root is None:
                continue
            if root.tag != "{" + RELS_NS + "}Relationships":
                self.issue("errors", "invalid_relationship_xml", "Relationship root has an unexpected name or namespace.", part=part)
                continue
            links = self.rels.setdefault(source, {})
            for node in root:
                if node.tag != "{" + RELS_NS + "}Relationship":
                    continue
                rid, target, kind = node.get("Id", ""), node.get("Target", ""), node.get("Type", "")
                if not rid or not target or not kind or rid in links:
                    self.issue("errors", "invalid_relationship", "Relationship requires unique Id, nonempty Target and Type.", part=part, relationship_id=rid)
                    continue
                mode = node.get("TargetMode", "Internal")
                link = {"id": rid, "target": target, "relationship_type": kind, "external": mode == "External", "part": None}
                links[rid] = link
                if mode not in {"Internal", "External"}:
                    self.issue("errors", "invalid_target_mode", "TargetMode must be Internal or External.", part=part, relationship_id=rid)
                    continue
                if link["external"]:
                    self.report["external_links"].append({"source_part": source or "/", "id": rid, "relationship_type": kind, "target": target})
                    continue
                try:
                    resolved = target_part(source, target)
                except (ValueError, UnicodeError) as exc:
                    self.issue("errors", "invalid_relationship_target", str(exc), part=part, relationship_id=rid)
                    continue
                link["part"] = resolved
                if resolved not in self.names:
                    self.issue("errors", "broken_relationship", "Internal relationship target is missing.", part=part, relationship_id=rid, target_part=resolved)

    def bound_objects(self, root: ET.Element, number: int, size: tuple[int, int] | None) -> list[dict]:
        tree = next((node for node in root.iter() if is_tag(node, P_NS, "spTree")), None)
        if tree is None:
            return []
        result = []
        for node in tree:
            kind = tag_name(node)
            if kind not in {"sp", "pic", "graphicFrame", "cxnSp", "grpSp"}:
                continue
            properties = next((item for item in node.iter() if tag_name(item) == "cNvPr"), None)
            name = properties.get("name", "") if properties is not None else ""
            obj = {"name": name, "kind": kind, "bounds_check": "unavailable", "bounds_emu": None}
            result.append(obj)
            if kind == "grpSp":
                obj["bounds_check"] = "skipped_group"
                self.issue("warnings", "group_bounds_not_checked", "Grouped object geometry is not resolved.", slide=number, object_name=name)
                continue
            holder = node if kind == "graphicFrame" else direct(node, "spPr")
            transform = direct(holder, "xfrm") if holder is not None else None
            if transform is None:
                continue
            try:
                if int(transform.get("rot", "0")) % 21600000:
                    obj["bounds_check"] = "skipped_rotated"
                    self.issue("warnings", "rotated_bounds_not_checked", "Rotated object geometry is not resolved.", slide=number, object_name=name)
                    continue
                off, ext = direct(transform, "off"), direct(transform, "ext")
                if off is None or ext is None:
                    continue
                x, y, width, height = int(off.attrib["x"]), int(off.attrib["y"]), int(ext.attrib["cx"]), int(ext.attrib["cy"])
            except (ValueError, KeyError):
                self.issue("warnings", "invalid_object_geometry", "Explicit object geometry is incomplete or nonnumeric.", slide=number, object_name=name)
                continue
            obj["bounds_emu"] = {"x": x, "y": y, "cx": width, "cy": height}
            if width < 0 or height < 0:
                self.issue("warnings", "invalid_object_geometry", "Object has a negative extent.", slide=number, object_name=name)
            elif size is not None:
                outside = x < 0 or y < 0 or x + width > size[0] or y + height > size[1]
                obj["bounds_check"] = "outside_slide" if outside else "within_slide"
                if outside:
                    self.issue("warnings", "object_outside_slide", "Explicit top-level unrotated bounds extend outside the slide; intentional bleed is possible.", slide=number, object_name=name)
        return result

    def notes_text(self, slide_part: str) -> str:
        pieces = []
        for link in self.rels.get(slide_part, {}).values():
            if link["relationship_type"].endswith("/notesSlide") and not link["external"] and link["part"] in self.names:
                root = self.read_xml(link["part"])
                if root is None:
                    continue
                if not is_tag(root, P_NS, "notes"):
                    self.issue("errors", "invalid_notes_root", "Notes relationship target is not a notes part.", part=link["part"])
                    continue
                for shape in root.iter():
                    if not is_tag(shape, P_NS, "sp"):
                        continue
                    placeholder = next((node for node in shape.iter() if is_tag(node, P_NS, "ph")), None)
                    if placeholder is not None and placeholder.get("type") in {"sldImg", "sldNum", "hdr", "ftr", "dt"}:
                        continue
                    text = slide_text(shape)
                    if text:
                        pieces.append(text)
        return "\n".join(pieces)

    def inspect_slide(self, number: int, part: str | None, size: tuple[int, int] | None) -> dict:
        slide = {"number": number, "part": part, "hidden": False, "text": "", "notes": "",
                 "counts": {"native_charts": 0, "tables": 0, "images": 0},
                 "native_chart_parts": [], "explicit_font_sizes_pt": [], "objects": []}
        if part is None or part not in self.names:
            return slide
        root = self.read_xml(part)
        if root is None:
            return slide
        if not is_tag(root, P_NS, "sld"):
            self.issue("errors", "invalid_slide_root", "Slide relationship target is not a slide part.", slide=number, part=part)
            return slide
        slide["hidden"] = root.get("show", "1") in {"0", "false"}
        slide["text"] = slide_text(root)
        slide["notes"] = self.notes_text(part)
        links = self.rels.get(part, {})
        fonts = set()
        for node in root.iter():
            if is_tag(node, A_NS, "tbl"):
                slide["counts"]["tables"] += 1
            if is_tag(node, A_NS, "blip"):
                rid = rel_attr(node, "embed")
                link = links.get(rid)
                if rid is not None and link is None:
                    self.issue("errors", "missing_image_relationship", "Embedded image refers to an unknown relationship.", slide=number, relationship_id=rid)
                elif link and not link["external"] and link["part"] in self.names and link["relationship_type"] in {namespace + "/image" for namespace in R_NS} and (self.content_type(link["part"]) or "").startswith("image/"):
                    slide["counts"]["images"] += 1
                elif rid is not None:
                    self.issue("errors", "invalid_image_relationship", "Embedded image requires an internal image relationship to an existing part with an image content type.", slide=number, relationship_id=rid)
            if is_tag(node, C_NS, "chart"):
                rid = rel_attr(node, "id")
                link = links.get(rid)
                chart_part = link["part"] if link else None
                chart_root = None
                if link and not link["external"] and link["relationship_type"].endswith("/chart") and chart_part in self.names and self.content_type(chart_part) == CHART_CT:
                    chart_root = self.read_xml(chart_part)
                if chart_root is not None and is_tag(chart_root, C_NS, "chartSpace"):
                    slide["counts"]["native_charts"] += 1
                    slide["native_chart_parts"].append(chart_part)
                else:
                    self.issue("errors", "invalid_native_chart", "Chart element lacks a valid internal native chart target and content type.", slide=number, relationship_id=rid)
            if any(is_tag(node, A_NS, name) for name in {"rPr", "defRPr", "endParaRPr"}) and "sz" in node.attrib:
                try:
                    font = int(node.attrib["sz"]) / 100
                    if font <= 0:
                        raise ValueError()
                    fonts.add(font)
                except ValueError:
                    self.issue("warnings", "invalid_font_size", "Explicit font size is not a positive integer in hundredths of a point.", slide=number)
        slide["explicit_font_sizes_pt"] = sorted(fonts)
        if self.min_font_pt is not None:
            small = sorted(font for font in fonts if font < self.min_font_pt)
            if small:
                self.issue("warnings", "small_explicit_font", "Explicit slide font sizes fall below the requested minimum.", slide=number, sizes_pt=small, minimum_pt=self.min_font_pt)
        slide["objects"] = self.bound_objects(root, number, size)
        return slide

    def inspect(self) -> None:
        if self.path.stat().st_size > MAX_FILE_BYTES:
            raise PackageFailure(f"Input exceeds {MAX_FILE_BYTES} bytes.")
        with zipfile.ZipFile(self.path) as archive:
            self.zip = archive
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES or sum(info.file_size for info in entries) > MAX_EXPANDED_BYTES:
                raise PackageFailure("ZIP entry count or expanded size exceeds safety limits.")
            seen = set()
            for info in entries:
                name = info.filename
                normalized = name[:-1] if info.is_dir() else name
                if not normalized or normalized.startswith("/") or "\\" in normalized or posixpath.normpath(normalized) != normalized or normalized.startswith("../") or normalized == ".." or "\x00" in normalized:
                    raise PackageFailure(f"Unsafe or noncanonical ZIP entry name: {name!r}")
                if name in seen or info.flag_bits & 1:
                    raise PackageFailure(f"Duplicate or encrypted ZIP entry: {name!r}")
                seen.add(name)
                if not info.is_dir():
                    self.names.add(name)
            self.read_content_types()
            self.read_relationships()
            office_types = {namespace + "/officeDocument" for namespace in R_NS}
            office_links = [link for link in self.rels.get("", {}).values()
                            if link["relationship_type"] in office_types]
            if len(office_links) != 1 or office_links[0]["external"] or office_links[0]["part"] not in self.names:
                self.issue("errors", "invalid_office_document_relationship", "Package root requires exactly one valid internal officeDocument relationship.", part="_rels/.rels")
                return
            presentation_part = office_links[0]["part"]
            # The declared main part may be a presentation, slideshow, or template,
            # including macro-enabled variants; macros are never executed.
            if self.content_type(presentation_part) not in PRESENTATION_CTS:
                self.issue("errors", "invalid_presentation_content_type", "The officeDocument target lacks a supported presentation content type.", part=presentation_part)
                return
            root = self.read_xml(presentation_part)
            if root is None:
                return
            if not is_tag(root, P_NS, "presentation"):
                self.issue("errors", "invalid_presentation_root", "Presentation root has an unexpected name or namespace.")
                return
            size = None
            size_node = direct(root, "sldSz")
            try:
                if size_node is None:
                    raise ValueError()
                size = int(size_node.attrib["cx"]), int(size_node.attrib["cy"])
                if min(size) <= 0:
                    raise ValueError()
                self.report["package"]["slide_size_emu"] = {"cx": size[0], "cy": size[1]}
                self.report["package"]["slide_size_inches"] = {"width": round(size[0] / EMU_PER_INCH, 6), "height": round(size[1] / EMU_PER_INCH, 6)}
            except (ValueError, KeyError):
                size = None
                self.issue("errors", "invalid_slide_size", "Presentation requires a positive integer slide width and height.")
            slide_list = direct(root, "sldIdLst")
            if slide_list is None:
                return
            ids = [node for node in slide_list if is_tag(node, P_NS, "sldId")]
            self.report["package"]["slide_count"] = len(ids)
            for number, node in enumerate(ids, 1):
                rid = rel_attr(node, "id")
                link = self.rels.get(presentation_part, {}).get(rid)
                part = None
                if link and not link["external"] and link["relationship_type"].endswith("/slide"):
                    part = link["part"]
                else:
                    self.issue("errors", "invalid_slide_relationship", "Presentation slide reference lacks an internal slide relationship.", slide=number, relationship_id=rid)
                self.report["slides"].append(self.inspect_slide(number, part, size))

    def declared_checks(self, expect_slides: int | None, require_chart: list[int], require_table: list[int]) -> None:
        if expect_slides is not None:
            actual = self.report["package"]["slide_count"]
            self.report["checks"].append({"kind": "slide_count", "expected": expect_slides, "actual": actual, "passed": actual == expect_slides})
        for kind, indices, count_key in [("native_chart", require_chart, "native_charts"), ("native_table", require_table, "tables")]:
            for number in indices:
                slide = next((slide for slide in self.report["slides"] if slide["number"] == number), None)
                actual = slide["counts"][count_key] if slide else 0
                self.report["checks"].append({"kind": kind, "slide": number, "expected_minimum": 1, "actual": actual, "passed": actual >= 1})
        for check in self.report["checks"]:
            if not check["passed"]:
                self.issue("errors", "declared_check_failed", f"Declared {check['kind']} check failed.", **({"slide": check["slide"]} if "slide" in check else {}))


def positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def nonnegative_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return result


def positive_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return result


def text_report(report: dict) -> str:
    lines = [f"{'PASS' if report['ok'] else 'FAIL'}: {report['package']['path']}",
             f"Slides: {report['package']['slide_count']}"]
    for slide in report["slides"]:
        counts = slide["counts"]
        lines.append(f"  Slide {slide['number']}: native charts={counts['native_charts']}, tables={counts['tables']}, images={counts['images']}, hidden={slide['hidden']}, notes={'yes' if slide['notes'] else 'no'} ({slide['part']})")
    for level in ("errors", "warnings"):
        for issue in report[level]:
            location = f" [slide {issue['slide']}]" if "slide" in issue else ""
            lines.append(f"{level[:-1].upper()} {issue['code']}{location}: {issue['message']}")
    for link in report["external_links"]:
        lines.append(f"EXTERNAL [{link['source_part']} / {link['id']}]: {link['target']}")
    lines.append(f"Result: {len(report['errors'])} error(s), {len(report['warnings'])} warning(s).")
    lines.extend("LIMITATION: " + limitation for limitation in report["limitations"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", type=Path, help="local PPTX/OOXML presentation to inspect without modification")
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    parser.add_argument("--expect-slides", type=nonnegative_int)
    parser.add_argument("--require-chart", type=positive_int, action="append", default=[], metavar="SLIDE", help="require native chart evidence on this 1-based slide (repeatable)")
    parser.add_argument("--require-table", type=positive_int, action="append", default=[], metavar="SLIDE", help="require native table XML on this 1-based slide (repeatable)")
    parser.add_argument("--min-font-pt", type=positive_float, help="warn about explicit slide font sizes below this threshold")
    args = parser.parse_args(argv)
    inspector = Inspector(args.deck, args.min_font_pt)
    exit_code = 0
    try:
        inspector.inspect()
        inspector.declared_checks(args.expect_slides, args.require_chart, args.require_table)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, PackageFailure) as exc:
        inspector.issue("errors", "unreadable_package", str(exc))
        exit_code = 2
    report = inspector.report
    report["ok"] = not report["errors"]
    if report["errors"] and exit_code == 0:
        exit_code = 1
    report["exit_code"] = exit_code
    print(json.dumps(report, ensure_ascii=True, indent=2) if args.json else text_report(report))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
