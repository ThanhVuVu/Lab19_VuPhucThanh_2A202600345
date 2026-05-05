# Bảng so sánh kết quả Benchmark: Flat RAG vs GraphRAG

| STT | Câu hỏi | Flat RAG (Vector Search) | GraphRAG (Neo4j) | Đánh giá |
|:---:|:---|:---:|:---:|:---|
| 1 | Các công ty cùng quốc gia với Apple và thuộc Semiconductors? | Trả lời chung chung | **Chính xác (Nvidia, Broadcom)** | GraphRAG kết nối tốt qua node Country. |
| 2 | So sánh Microsoft và Nvidia? | Tốt | Tốt | Cả hai đều lấy được dữ liệu ngành. |
| 3 | Các công ty ở South Korea và ngành của họ? | Thiếu sót | **Chính xác (Samsung...)** | Flat RAG gặp khó với truy vấn địa lý diện rộng. |
| 4 | Adobe và Salesforce có cùng ngành không? | Tốt | Tốt | Cả hai đều tìm thấy Industry tương ứng. |
| 5 | Quan hệ gián tiếp giữa Nvidia và Microsoft? | **Ảo giác** | **Chính xác (Cùng Sector)** | GraphRAG thấy quan hệ qua node 'Technology'. |
| 6 | Công ty vốn hóa cao nhất ở Ireland? | Tốt | Tốt | |
| 7 | Ngành Semiconductors trong top 20? | Hay đếm thiếu | **Chính xác** | |
| 8 | Điểm chung giữa Broadcom và ASML? | Khá | **Rất tốt** | |
| 9 | Lĩnh vực phổ biến ở Netherlands? | Trung bình | **Tốt** | |
| 10 | Phần mềm ứng dụng (Software—Application) và quốc gia? | Khá | **Tốt** | |
| 11 | Samsung có cùng Sector với Apple không? | Tốt | Tốt | |
| 12 | Có bao nhiêu công ty Mỹ trong top 50? | **Ảo giác (đếm sai)** | **Chính xác** | Vector search không giỏi đếm. |
| 13 | So sánh Accenture và Oracle? | Tốt | Tốt | |
| 14 | Ngành cụ thể trong Technology của top 15? | Thiếu | **Đầy đủ** | |
| 15 | Công ty đứng đầu Semiconductor Equipment? | Tốt | Tốt | |
| 16 | Top 10 có bao nhiêu Software—Infrastructure? | Trung bình | **Chính xác** | |
| 17 | TSMC đặt tại quốc gia nào? | Tốt | Tốt | |
| 18 | Lĩnh vực chính của Salesforce? | Tốt | Tốt | |
| 19 | Semiconductors tập trung ở quốc gia nào? | Trung bình | **Rất tốt** | GraphRAG thấy các cụm node quốc gia. |
| 20 | Khác biệt Sector/Industry của Top 10? | Khá | **Sâu sắc hơn** | GraphRAG phân tích cấu trúc đồ thị. |

**Kết luận**: GraphRAG vượt trội ở các câu hỏi yêu cầu **liên kết thông tin (multi-hop)** và **thống kê/đếm**, trong khi Flat RAG dễ bị nhầm lẫn khi thông tin nằm ở các đoạn văn bản cách xa nhau.
