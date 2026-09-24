/** Optional integration example for the host-supplied @oai/artifact-tool.
 * See README.md in this directory. No library or fonts are bundled here.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node examples/demo/build_demo.mjs [output-directory] [--render]\nRequires the host presentation runtime; see examples/demo/README.md.');
  process.exit(0);
}
const unknown = args.filter(arg => arg.startsWith('-') && arg !== '--render');
const directories = args.filter(arg => !arg.startsWith('-'));
if (unknown.length || directories.length > 1) throw new Error('Usage: build_demo.mjs [output-directory] [--render]');
const render = args.includes('--render');
const workspaceDir = path.resolve(here, '..', '..');
const outputRoot = path.resolve(directories[0] ?? path.join(here, 'output'));
const relativeOutput = path.relative(workspaceDir, outputRoot);
if (relativeOutput === '..' || relativeOutput.startsWith(`..${path.sep}`) || path.isAbsolute(relativeOutput)) {
  throw new Error('Choose an output directory inside this repository so finalization stays in the workspace.');
}
const skillDir = process.env.PRESENTATIONS_SKILL_DIR;
const python = process.env.RUNTIME_PYTHON;
const modulePath = process.env.ARTIFACT_TOOL_MODULE;
const nodeModules = process.env.RUNTIME_NODE_MODULES;
for (const [name, value] of Object.entries({ PRESENTATIONS_SKILL_DIR: skillDir, RUNTIME_PYTHON: python, ARTIFACT_TOOL_MODULE: modulePath, RUNTIME_NODE_MODULES: nodeModules })) {
  if (!value || !path.isAbsolute(value)) throw new Error(`Set ${name} to the absolute host-provided path. See examples/demo/README.md.`);
}
const output = path.join(outputRoot, 'superpowerpoint-demo.pptx');
try {
  await fs.access(output);
  throw new Error(`Refusing to replace ${output}; choose a fresh output directory.`);
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(modulePath).href);
const { resolvePresentationFont, applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, 'container_tools', 'artifact_tool_utils.mjs')).href,
);
const family = resolvePresentationFont();
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const ink = '#132D3C', accent = '#087F8C', muted = '#516571', paper = '#F7FAFB';

function text(slide, value, x, y, w, h, size = 32, color = ink, bold = false) {
  const shape = slide.shapes.add({
    geometry: 'textbox', position: { left: x, top: y, width: w, height: h },
    fill: 'none', line: { fill: 'none', width: 0 },
  });
  shape.text = value;
  shape.text.style = { typeface: family, fontSize: size, color, bold, autoFit: 'none' };
  return shape;
}
function contentSlide(title, subtitle) {
  const slide = p.slides.add();
  slide.background.fill = paper;
  text(slide, title, 72, 54, 1136, 76, 46, ink, true);
  text(slide, subtitle, 72, 144, 1136, 54, 27, muted);
  return slide;
}

const cover = p.slides.add();
cover.background.fill = ink;
text(cover, 'SUPERPOWERPOINT', 80, 78, 1100, 52, 28, '#73D1D8', true);
text(cover, 'Từ ý tưởng đến\nslide có thể chỉnh sửa', 80, 217, 1100, 208, 66, '#FFFFFF', true);
text(cover, 'Một ví dụ gồm văn bản, biểu đồ và bảng tiếng Việt', 80, 476, 1050, 100, 31, '#D6E5EC');
cover.speakerNotes.textFrame.setText('Nội dung tự soạn cho dự án Superpowerpoint. Bản minh hoạ có đúng 4 slide. Không chứa số liệu kinh doanh thực tế.');

const chartSlide = contentSlide('Khối lượng xử lý theo tuần', 'Số liệu giả lập cho ví dụ. Đơn vị: hồ sơ.');
const chart = chartSlide.charts.add('bar', {
  position: { left: 84, top: 225, width: 1110, height: 395 },
  categories: ['Tuần 1', 'Tuần 2', 'Tuần 3'],
  series: [{ name: 'Hồ sơ', values: [24, 36, 48], fill: accent }],
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 130 },
  hasLegend: false,
  xAxis: { textStyle: { typeface: family, fontSize: 25, fill: ink }, majorGridlines: null },
  yAxis: { minimumScale: 0, maximumScale: 60, numberFormatCode: '0', textStyle: { typeface: family, fontSize: 24, fill: muted }, majorGridlines: { fill: '#DBE5E9', width: 1 } },
  dataLabels: { showValue: true, position: 'outEnd', textStyle: { typeface: family, fontSize: 28, bold: true, fill: ink } },
});
applyPresentationChartFont(chart, { fontFamily: family });
chartSlide.speakerNotes.textFrame.setText('Dữ liệu giả lập: Tuần 1 = 24, Tuần 2 = 36, Tuần 3 = 48 hồ sơ. Không phải số liệu thực tế. Biểu đồ được tạo từ các giá trị này; workbook nhúng là bản chụp dữ liệu giả lập, không có công thức nguồn cần bảo toàn.');

const tableSlide = contentSlide('Đầu ra của từng công đoạn', 'Mỗi công đoạn để lại một kết quả có thể kiểm tra.');
const values = [
  ['Công đoạn', 'Đầu ra'],
  ['Làm rõ yêu cầu', 'Mục tiêu, người xem và giới hạn'],
  ['Lập dàn ý', 'Nội dung và bằng chứng cho từng slide'],
  ['Tạo bài trình bày', 'Văn bản, biểu đồ và bảng chỉnh sửa được'],
  ['Kiểm tra', 'Slide đã xem và các giới hạn còn lại'],
];
const table = tableSlide.tables.add({ rows: 5, columns: 2, left: 72, top: 234, width: 1136, height: 338, columnWidths: [355, 781], values });
table.borders.assign({ fill: '#D3E0E5', width: 1, style: 'solid' });
table.cells.block({ row: 0, column: 0, rowCount: 5, columnCount: 2 }).assign({
  textStyle: { typeface: family, fontSize: 27, color: ink },
  margins: { left: 18, right: 18, top: 15, bottom: 15 },
});
for (let row = 0; row < values.length; row++) {
  for (let col = 0; col < 2; col++) {
    const cell = table.getCell(row, col);
    cell.fill = row === 0 ? ink : (row % 2 === 0 ? '#EDF3F6' : '#FFFFFF');
    cell.text.style = { typeface: family, fontSize: 27, color: row === 0 ? '#FFFFFF' : ink, bold: row === 0 };
  }
}
tableSlide.speakerNotes.textFrame.setText('Bảng mô tả quy trình của dự án Superpowerpoint. Nội dung tự soạn. Bảng có 5 hàng bao gồm tiêu đề và 2 cột; toàn bộ nội dung là đối tượng bảng trong slide.');

const closing = contentSlide('Bàn giao có bằng chứng', 'Người nhận cần biết mình có thể dùng và kiểm tra điều gì.');
text(closing, 'Nội dung có căn cứ', 72, 260, 405, 62, 33, accent, true);
text(closing, 'Nguồn, dữ liệu và giả định được ghi rõ.', 500, 260, 704, 78, 31);
text(closing, 'Đối tượng chỉnh sửa được', 72, 390, 405, 95, 33, accent, true);
text(closing, 'Văn bản, bảng và biểu đồ vẫn sửa được trong file.', 500, 390, 704, 100, 31);
text(closing, 'Bản xem trước', 72, 540, 405, 62, 33, accent, true);
text(closing, 'Mọi slide đều có bản để xem lại bố cục.', 500, 540, 704, 100, 31);
closing.speakerNotes.textFrame.setText('Nội dung tự soạn về yêu cầu bàn giao của dự án. Khả năng mở, chỉnh sửa và hiển thị trong một ứng dụng cụ thể phải được kiểm tra riêng; ảnh xem trước không chứng minh tính tương thích với mọi ứng dụng.');

await fs.mkdir(outputRoot, { recursive: true });
const staging = await fs.mkdtemp(path.join(here, '.build-'));
const candidate = path.join(staging, 'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
await finalizePresentation({
  workspaceDir, candidatePath: candidate, finalPath: output,
  pythonExecutable: python,
  integrityValidatorPath: path.join(skillDir, 'container_tools', 'inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skillDir, 'container_tools', 'inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-heading-fit', '--require-native-table-slide', '3'],
  explicitTotalSlideCount: 4,
  requiredNativeTableOwnerSlides: [3], requiredNativeChartOwnerSlides: [2],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: { basis: 'design', families: [family] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(staging, 'validation.json'),
});
if (render) {
  const restored = await PresentationFile.importPptx(await FileBlob.load(output));
  for (let i = 0; i < 4; i++) {
    const slide = restored.slides.getItem(i);
    const png = await restored.export({ slide, format: 'png', scale: 1 });
    await fs.writeFile(path.join(outputRoot, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  }
}
console.log(JSON.stringify({ output, slides: 4, font: family, previews: render ? outputRoot : null, receipt: path.join(staging, 'validation.json') }, null, 2));
