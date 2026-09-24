# Ví dụ chạy được

[Brief và storyboard](brief.md) xác định đúng 4 slide. Mọi số liệu trong biểu đồ đều giả lập. File PPTX cuối cùng có văn bản, bảng và biểu đồ gốc để chỉnh sửa.

`build_demo.mjs` là ví dụ tích hợp tuỳ chọn cho môi trường có sẵn `@oai/artifact-tool` và skill Presentations. Thư viện này không phải gói được dự án phân phối; không dùng `npm install` để giả định có thể lấy nó công khai. Bộ skill và công cụ kiểm tra Python hoạt động độc lập với ví dụ này.

Trong Codex có hỗ trợ tài liệu, gọi `load_workspace_dependencies` để tìm Node/Python và module được cấp, rồi đọc skill Presentations đã cài. Đặt bốn biến môi trường thành đường dẫn tuyệt đối:

- `ARTIFACT_TOOL_MODULE`: file `@oai/artifact-tool/dist/artifact_tool.mjs` trong các gói Node được cấp.
- `PRESENTATIONS_SKILL_DIR`: thư mục skill Presentations chứa `container_tools/artifact_tool_utils.mjs`.
- `RUNTIME_PYTHON`: Python được cấp bởi môi trường.
- `RUNTIME_NODE_MODULES`: thư mục chứa các gói Node được cấp, dùng để tìm font và các công cụ phụ trợ.

Tuân theo bước đánh dấu bắt đầu thao tác của skill Presentations trong môi trường đó, sau đó chạy bằng Node được cấp:

```text
node examples/demo/build_demo.mjs examples/demo/output
```

Script mặc định xuất và kiểm tra PPTX, từ chối thay thế PPTX đã tồn tại. Khi dựng lại, chọn một thư mục đầu ra mới bên trong repository. Bản nháp và biên nhận kỹ thuật nằm trong thư mục `.build-*` được bỏ qua bởi Git.

Để tạo thêm PNG, thêm `--render`. Các PNG được render từ PPTX cuối cùng sau khi nhập lại, không chỉ từ trạng thái trước khi xuất. Ví dụ đã có đủ 4 ảnh xem trước được kiểm tra.

**Giới hạn runtime đã quan sát:** trên Windows với Node 24.19.0 và `@oai/artifact-tool` 2.8.59 được cấp ở phiên kiểm thử này, bước render tạo đủ ảnh nhưng tiến trình native bị lỗi khi thoát (`0xC0000409`). Nhập PPTX và dựng file không render kết thúc bình thường. Vì vậy render là tuỳ chọn riêng; script không che mã lỗi hoặc coi lỗi tiến trình là thành công. Có thể xem ngay các PNG đã lưu, hoặc dùng renderer khác có sẵn. Đây là giới hạn của bản runtime đã thử, không phải kết luận cho mọi hệ điều hành hay phiên bản.

Kiểm tra độc lập bằng Python tiêu chuẩn:

```text
python skills/reviewing-powerpoint/scripts/inspect_pptx.py examples/demo/output/superpowerpoint-demo.pptx --expect-slides 4 --require-chart 2 --require-table 3 --json
```

Kết quả cấu trúc không thay thế việc xem slide. Xem [báo cáo xác minh](../../docs/validation.md) để biết những gì đã thực sự được kiểm tra.
