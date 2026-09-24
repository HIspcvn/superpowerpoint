"""Synthetic OOXML fixtures; no PowerPoint, third-party libraries, or network."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "reviewing-powerpoint" / "scripts" / "inspect_pptx.py"
SPEC = importlib.util.spec_from_file_location("inspect_pptx", SCRIPT)
inspector_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector_module)
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = f'xmlns:p="{P}" xmlns:a="{A}" xmlns:c="{C}" xmlns:r="{R}"'
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"


def relationships(*entries):
    return f'<Relationships xmlns="{RELS}">' + "".join(
        f'<Relationship Id={quoteattr(rid)} Type={quoteattr(R + "/" + kind)} Target={quoteattr(target)}'
        + (' TargetMode="External"' if external else "") + '/>'
        for rid, kind, target, external in entries
    ) + '</Relationships>'


def shape(text="Hello", x=10, y=10, cx=500, cy=300, font=2400, name="Text", rotation=0):
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="1" name={quoteattr(name)}/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm rot="{rotation}"><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm></p:spPr>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>'
        + (f'<a:rPr sz="{font}"/>' if font is not None else '<a:rPr/>')
        + f'<a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp>'
    )


def slide(body, hidden=False):
    return f'<p:sld {NS} show="{0 if hidden else 1}"><p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>'


def base_parts():
    presentation = (
        f'<p:presentation {NS}><p:sldIdLst>'
        '<p:sldId id="256" r:id="rSecond"/><p:sldId id="257" r:id="rFirst"/>'
        '</p:sldIdLst><p:sldSz cx="9144000" cy="5143500"/></p:presentation>'
    )
    content_types = (
        f'<Types xmlns="{CT}">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slides/z-final.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        '<Override PartName="/ppt/slides/a%20first.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        '<Override PartName="/ppt/charts/chart-one.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
        '</Types>'
    )
    return {
        '[Content_Types].xml': content_types,
        '_rels/.rels': relationships(('office', 'officeDocument', 'ppt/presentation.xml', False)),
        'ppt/presentation.xml': presentation,
        'ppt/_rels/presentation.xml.rels': relationships(
            ('rFirst', 'slide', 'slides/a%20first.xml', False),
            ('rSecond', 'slide', './slides/z-final.xml', False)),
        'ppt/slides/z-final.xml': slide(shape('First in presentation order'), hidden=True),
        'ppt/slides/a first.xml': slide(shape('Second in presentation order')),
    }


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.pptx'

    def write(self, parts=None):
        with zipfile.ZipFile(self.path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, payload in (base_parts() if parts is None else parts).items():
                archive.writestr(name, payload)
        return self.path

    def cli(self, *arguments, json_output=True, path=None):
        command = [sys.executable, str(SCRIPT), str(self.path if path is None else path)]
        if json_output:
            command.append('--json')
        result = subprocess.run(command + list(arguments), capture_output=True, text=True, encoding='utf-8')
        if json_output and result.stdout:
            return result.returncode, json.loads(result.stdout), result.stderr
        return result.returncode, result.stdout, result.stderr

    def test_order_size_hidden_text_and_source_unchanged(self):
        self.write()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        status, report, _ = self.cli('--expect-slides', '2')
        self.assertEqual(status, 0, report)
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual([item['part'] for item in report['slides']], ['ppt/slides/z-final.xml', 'ppt/slides/a first.xml'])
        self.assertEqual(report['slides'][0]['text'], 'First in presentation order')
        self.assertTrue(report['slides'][0]['hidden'])
        self.assertFalse(report['slides'][1]['hidden'])
        self.assertEqual(report['package']['slide_size_inches'], {'width': 10.0, 'height': 5.625})
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)
        self.assertTrue(report['checks'][0]['passed'])

    def test_requires_one_internal_root_office_document_relationship(self):
        root_variants = {
            'missing': None,
            'wrong_type': relationships(('office', 'slide', 'ppt/presentation.xml', False)),
            'external': relationships(('office', 'officeDocument', 'https://example.invalid/deck.xml', True)),
            'multiple': relationships(
                ('office', 'officeDocument', 'ppt/presentation.xml', False),
                ('second', 'officeDocument', 'ppt/presentation.xml', False)),
        }
        for label, value in root_variants.items():
            with self.subTest(label=label):
                parts = base_parts()
                if value is None:
                    del parts['_rels/.rels']
                else:
                    parts['_rels/.rels'] = value
                self.write(parts)
                status, report, _ = self.cli()
                self.assertEqual(status, 1, report)
                self.assertFalse(report['ok'])
                self.assertIn('invalid_office_document_relationship', [issue['code'] for issue in report['errors']])

    def test_follows_relocated_root_and_its_slide_relationships(self):
        parts = base_parts()
        parts['decks/custom.xml'] = parts.pop('ppt/presentation.xml')
        parts['decks/_rels/custom.xml.rels'] = parts.pop('ppt/_rels/presentation.xml.rels').replace('slides/', '../ppt/slides/')
        parts['_rels/.rels'] = relationships(('office', 'officeDocument', 'decks/custom.xml', False))
        parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace('/ppt/presentation.xml', '/decks/custom.xml')
        self.write(parts)
        status, report, _ = self.cli('--expect-slides', '2')
        self.assertEqual(status, 0, report)
        self.assertEqual([item['part'] for item in report['slides']], ['ppt/slides/z-final.xml', 'ppt/slides/a first.xml'])
        self.assertEqual(report['slides'][0]['text'], 'First in presentation order')

    def test_root_requires_presentation_content_type_and_xml_root(self):
        for alteration in ('content_type', 'xml_root'):
            with self.subTest(alteration=alteration):
                parts = base_parts()
                if alteration == 'content_type':
                    parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace(
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml', 'application/xml')
                    expected_code = 'invalid_presentation_content_type'
                else:
                    parts['ppt/presentation.xml'] = slide(shape())
                    expected_code = 'invalid_presentation_root'
                self.write(parts)
                status, report, _ = self.cli()
                self.assertEqual(status, 1, report)
                self.assertIn(expected_code, [issue['code'] for issue in report['errors']])

    def test_template_and_macro_presentation_content_types_supported(self):
        for content_type in (
            'application/vnd.openxmlformats-officedocument.presentationml.template.main+xml',
            'application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml',
        ):
            with self.subTest(content_type=content_type):
                parts = base_parts()
                parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace(
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml', content_type)
                self.write(parts)
                status, report, _ = self.cli('--expect-slides', '2')
                self.assertEqual(status, 0, report)

    def test_native_chart_table_image_and_speaker_notes(self):
        parts = base_parts()
        body = ('<p:graphicFrame><a:graphic><a:graphicData><c:chart r:id="rChart"/></a:graphicData></a:graphic></p:graphicFrame>'
                '<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>Native cell</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
                '<p:pic><p:blipFill><a:blip r:embed="rImage"/></p:blipFill></p:pic>')
        parts['ppt/slides/z-final.xml'] = slide(body)
        parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(
            ('rChart', 'chart', '../charts/chart-one.xml', False),
            ('rImage', 'image', '../media/photo%20one.png', False),
            ('rNotes', 'notesSlide', '../notesSlides/note.xml', False))
        parts['ppt/charts/chart-one.xml'] = f'<c:chartSpace xmlns:c="{C}"><c:chart><c:plotArea/></c:chart></c:chartSpace>'
        parts['ppt/media/photo one.png'] = b'PNG placeholder - pixel validation is outside scope'
        parts['ppt/notesSlides/note.xml'] = (
            f'<p:notes {NS}><p:cSld><p:spTree>'
            '<p:sp><p:nvSpPr><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Speaker note</a:t></a:r></a:p></p:txBody></p:sp>'
            '<p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>9</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:notes>')
        self.write(parts)
        status, report, _ = self.cli('--require-chart', '1', '--require-table', '1', '--require-chart', '1')
        self.assertEqual(status, 0, report)
        first = report['slides'][0]
        self.assertEqual(first['counts'], {'native_charts': 1, 'tables': 1, 'images': 1})
        self.assertEqual(first['notes'], 'Speaker note')
        self.assertEqual(first['native_chart_parts'], ['ppt/charts/chart-one.xml'])
        self.assertIn('Native cell', first['text'])
        self.assertEqual(len(report['checks']), 3)

    def test_embedded_images_reject_incompatible_relationship_targets(self):
        for alteration in ('wrong_type', 'wrong_content_type', 'external'):
            with self.subTest(alteration=alteration):
                parts = base_parts()
                parts['ppt/slides/z-final.xml'] = slide('<p:pic><p:blipFill><a:blip r:embed="rImage"/></p:blipFill></p:pic>')
                kind = 'hyperlink' if alteration == 'wrong_type' else 'image'
                external = alteration == 'external'
                target = 'https://example.invalid/photo.png' if external else '../media/photo.png'
                parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(('rImage', kind, target, external))
                parts['ppt/media/photo.png'] = b'opaque image bytes'
                if alteration == 'wrong_content_type':
                    parts['[Content_Types].xml'] = parts['[Content_Types].xml'].replace('ContentType="image/png"', 'ContentType="application/xml"')
                self.write(parts)
                status, report, _ = self.cli()
                self.assertEqual(status, 1, report)
                self.assertEqual(report['slides'][0]['counts']['images'], 0)
                self.assertIn('invalid_image_relationship', [issue['code'] for issue in report['errors']])

    def test_valid_embedded_image_counts_as_image(self):
        parts = base_parts()
        parts['ppt/slides/z-final.xml'] = slide('<p:pic><p:blipFill><a:blip r:embed="rImage"/></p:blipFill></p:pic>')
        parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(('rImage', 'image', '../media/photo.png', False))
        parts['ppt/media/photo.png'] = b'opaque image bytes'
        self.write(parts)
        status, report, _ = self.cli()
        self.assertEqual(status, 0, report)
        self.assertEqual(report['slides'][0]['counts']['images'], 1)

    def test_screenshot_does_not_satisfy_native_chart_or_table(self):
        parts = base_parts()
        parts['ppt/slides/z-final.xml'] = slide('<p:pic><p:blipFill><a:blip r:embed="rImage"/></p:blipFill></p:pic>')
        parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(('rImage', 'image', '../media/chart.png', False))
        parts['ppt/media/chart.png'] = b'screenshot'
        self.write(parts)
        status, report, _ = self.cli('--require-chart', '1', '--require-table', '1', '--require-chart', '9')
        self.assertEqual(status, 1)
        self.assertEqual(report['slides'][0]['counts']['images'], 1)
        self.assertEqual(report['slides'][0]['counts']['native_charts'], 0)
        self.assertEqual(len(report['checks']), 3)
        self.assertTrue(all(not check['passed'] for check in report['checks']))

    def test_native_chart_cannot_be_faked_by_relationship_type_only(self):
        parts = base_parts()
        parts['ppt/slides/z-final.xml'] = slide('<p:graphicFrame><c:chart r:id="fake"/></p:graphicFrame>')
        parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(('fake', 'chart', '../charts/chart-one.xml', False))
        parts['ppt/charts/chart-one.xml'] = '<image/>'
        self.write(parts)
        status, report, _ = self.cli('--require-chart', '1')
        self.assertEqual(status, 1)
        self.assertEqual(report['slides'][0]['counts']['native_charts'], 0)
        self.assertIn('invalid_native_chart', [issue['code'] for issue in report['errors']])

    def test_broken_relationships_validated_beyond_slides(self):
        parts = base_parts()
        parts['ppt/unused.xml'] = '<unused/>'
        parts['ppt/_rels/unused.xml.rels'] = relationships(('lost', 'image', 'media/missing.png', False))
        self.write(parts)
        status, report, _ = self.cli()
        self.assertEqual(status, 1)
        broken = next(issue for issue in report['errors'] if issue['code'] == 'broken_relationship')
        self.assertEqual(broken['target_part'], 'ppt/media/missing.png')

    def test_external_links_are_listed_and_not_dereferenced(self):
        parts = base_parts()
        parts['ppt/slides/_rels/z-final.xml.rels'] = relationships(
            ('external', 'hyperlink', 'https://no-such-host.invalid/private?a=1&b=2', True),
            ('file', 'oleObject', 'file:///C:/private/secret.xlsx', True))
        self.write(parts)
        status, report, _ = self.cli()
        self.assertEqual(status, 0, report)
        self.assertEqual(len(report['external_links']), 2)
        self.assertEqual(report['external_links'][0]['target'], 'https://no-such-host.invalid/private?a=1&b=2')

    def test_bounds_fonts_groups_and_rotations_are_honest(self):
        parts = base_parts()
        group = '<p:grpSp><p:nvGrpSpPr><p:cNvPr id="3" name="Group"/></p:nvGrpSpPr>' + shape('Grouped', x=-10, font=None) + '</p:grpSp>'
        parts['ppt/slides/z-final.xml'] = slide(shape('Small outside', x=-1, font=1200, name='Outside') + group + shape('Rotated', x=-20, name='Rotated', rotation=5400000))
        self.write(parts)
        status, report, _ = self.cli('--min-font-pt', '18')
        self.assertEqual(status, 0)
        codes = [issue['code'] for issue in report['warnings']]
        self.assertEqual(codes.count('object_outside_slide'), 1)
        self.assertIn('group_bounds_not_checked', codes)
        self.assertIn('rotated_bounds_not_checked', codes)
        self.assertIn('small_explicit_font', codes)
        self.assertEqual([obj['bounds_check'] for obj in report['slides'][0]['objects']], ['outside_slide', 'skipped_group', 'skipped_rotated'])
        self.assertTrue(any('inherited' in text for text in report['limitations']))

    def test_missing_required_parts_and_slide_count_fail(self):
        self.write({'ppt/presentation.xml': base_parts()['ppt/presentation.xml']})
        status, report, _ = self.cli('--expect-slides', '3')
        self.assertEqual(status, 1)
        self.assertIn('missing_part', [issue['code'] for issue in report['errors']])
        self.assertFalse(report['checks'][0]['passed'])

    def test_malformed_xml_reports_failure_without_traceback(self):
        for part in ('ppt/presentation.xml', '[Content_Types].xml', 'ppt/slides/z-final.xml', 'ppt/_rels/presentation.xml.rels'):
            with self.subTest(part=part):
                parts = base_parts()
                parts[part] = '<broken'
                self.write(parts)
                status, report, stderr = self.cli()
                self.assertEqual(status, 1)
                self.assertIn('malformed_xml', [issue['code'] for issue in report['errors']])
                self.assertNotIn('Traceback', stderr)

    def test_bad_zip_and_io_errors_are_exit_two(self):
        self.path.write_bytes(b'not a ZIP')
        status, report, stderr = self.cli()
        self.assertEqual(status, 2)
        self.assertFalse(report['ok'])
        self.assertEqual(report['exit_code'], 2)
        self.assertNotIn('Traceback', stderr)
        status, report, _ = self.cli(path=self.path.with_name('missing.pptx'))
        self.assertEqual(status, 2)
        self.assertEqual(report['errors'][0]['code'], 'unreadable_package')

    def test_unknown_xml_encoding_is_a_reported_error(self):
        parts = base_parts()
        parts['ppt/slides/z-final.xml'] = '<?xml version="1.0" encoding="unsupported-encoding"?><root/>'
        self.write(parts)
        status, report, stderr = self.cli()
        self.assertEqual(status, 1)
        self.assertIn('malformed_xml', [issue['code'] for issue in report['errors']])
        self.assertNotIn('Traceback', stderr)

    def test_dtd_duplicate_and_traversal_packages_are_rejected(self):
        parts = base_parts()
        parts['ppt/presentation.xml'] = '<!DOCTYPE p [<!ENTITY evil "value">]><p>&evil;</p>'
        self.write(parts)
        self.assertEqual(self.cli()[0], 2)
        parts = base_parts()
        parts['../outside.xml'] = '<root/>'
        self.write(parts)
        self.assertEqual(self.cli()[0], 2)
        self.write()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.path, 'a') as archive:
                archive.writestr('ppt/presentation.xml', '<root/>')
        self.assertEqual(self.cli()[0], 2)

    def test_internal_target_resolution_encoded_relative_and_escape(self):
        resolve = inspector_module.target_part
        self.assertEqual(resolve('ppt/slides/s.xml', '../media/a%20b.png'), 'ppt/media/a b.png')
        self.assertEqual(resolve('ppt/slides/s.xml', '/ppt/media/a.png#view'), 'ppt/media/a.png')
        self.assertEqual(resolve('ppt/slides/s.xml', '#anchor'), 'ppt/slides/s.xml')
        for value in ('../../../outside.xml', 'https://example.com/private', '../media/%5cfile.xml', '../media/x.xml?q=1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve('ppt/slides/s.xml', value)

    def test_bounded_xml_size_limit(self):
        self.write()
        original = inspector_module.MAX_XML_BYTES
        inspector_module.MAX_XML_BYTES = 20
        self.addCleanup(setattr, inspector_module, 'MAX_XML_BYTES', original)
        with self.assertRaises(inspector_module.PackageFailure):
            inspector_module.Inspector(self.path).inspect()

    def test_usage_validation_and_text_report(self):
        self.write()
        for options in [('--require-chart', '0'), ('--require-table', '-2'), ('--min-font-pt', 'nan'), ('--min-font-pt', '0'), ('--expect-slides', '-1')]:
            with self.subTest(options=options):
                status, _, stderr = self.cli(*options, json_output=False)
                self.assertEqual(status, 2)
                self.assertIn('error:', stderr)
        status, output, _ = self.cli('--expect-slides', '2', json_output=False)
        self.assertEqual(status, 0)
        self.assertIn('PASS:', output)
        self.assertIn('Slides: 2', output)
        self.assertIn('LIMITATION:', output)


if __name__ == '__main__':
    unittest.main()
