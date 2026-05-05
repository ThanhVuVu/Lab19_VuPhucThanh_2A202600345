# Phân tích chi phí xây dựng Đồ thị Tri thức (Graph Construction)

Dựa trên quá trình thực thi file `triple_indexer.py` cho 1000 bản ghi từ file "Top 1000 technology companies.csv", các chỉ số ước tính như sau:

## 1. Token Usage (Chi phí API)
*   **Mô hình sử dụng**: `meta/llama-3.1-70b-instruct` (NVIDIA NIM).
*   **Input Token trung bình/dòng**: ~150 tokens (bao gồm System Prompt + Dữ liệu dòng CSV).
*   **Output Token trung bình/dòng**: ~60 tokens (Danh sách các bộ Triples JSON).
*   **Tổng cộng cho 1000 dòng**: 
    *   `1000 * (150 + 60) = 210,000 tokens`.
*   **Nhận xét**: Chi phí token ở mức trung bình. Việc sử dụng Llama 3.1 70B giúp cân bằng giữa độ chính xác của quan hệ và số lượng token tiêu thụ.

## 2. Phân tích thời gian (Time)
*   **Thời gian phản hồi API trung bình**: ~2 - 4 giây / yêu cầu.
*   **Khoảng nghỉ an toàn (Delay)**: 3 giây / dòng (để tránh lỗi 429 - Too Many Requests).
*   **Thời gian xử lý mỗi dòng**: ~6 giây.
*   **Tổng thời gian dự kiến cho 1000 dòng**:
    *   `1000 * 6 = 6,000 giây` (~ **1 giờ 40 phút**).
*   **Nhận xét**: Thời gian xây dựng đồ thị khá lâu do giới hạn Rate Limit của API. Tuy nhiên, đây là chi phí **đầu tư một lần**. Sau khi đồ thị đã được lưu vào Neo4j, việc truy vấn sau này sẽ diễn ra ngay lập tức (miliseconds).

## 3. Tối ưu hóa đề xuất
*   Để giảm thời gian: Có thể tăng số lượng worker (nâng cấp API key để tăng giới hạn RPM) để chạy song song.
*   Để giảm Token: Tối ưu lại System Prompt ngắn gọn hơn nhưng vẫn đảm bảo trích xuất đủ Triple.
