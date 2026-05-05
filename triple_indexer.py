import os
import pandas as pd
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 1. Load môi trường
load_dotenv()

# 2. Định nghĩa cấu trúc Triple (Bộ tam)
class Triple(BaseModel):
    subject: str = Field(description="Chủ thể (Subject) - ví dụ: Tên công ty, thực thể")
    relationship: str = Field(description="Mối quan hệ/Vị ngữ (Relationship/Predicate) - ví dụ: 'trụ sở tại', 'thuộc lĩnh vực'")
    object: str = Field(description="Tân ngữ (Object) - ví dụ: Địa điểm, giá trị, thực thể khác")

class TripleList(BaseModel):
    triples: List[Triple]

# 3. Khởi tạo LLM NVIDIA NIM
# Lưu ý: Cần NVIDIA_API_KEY trong file .env
llm = ChatNVIDIA(
    model="meta/llama-3.1-70b-instruct",
    temperature=0
)

# 4. Thiết kế Prompt trích xuất theo yêu cầu trong ảnh
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Bạn là một chuyên gia trích xuất thực thể và quan hệ (Knowledge Graph Extractor).
Nhiệm vụ của bạn là phân tích văn bản và chuyển đổi thành các bộ tam (triples) theo cấu trúc:
(Chủ thể) -> [Mối quan hệ] -> (Tân ngữ)

Yêu cầu:
- Trích xuất chính xác các thực thể.
- Mối quan hệ phải ngắn gọn, súc tích.
- Trả về danh sách các bộ tam dưới dạng cấu trúc JSON."""),
    ("user", "Hãy trích xuất các triples từ nội dung sau:\n\n{text}")
])

# Sử dụng structured output để đảm bảo dữ liệu trả về đúng định dạng
extractor = prompt_template | llm.with_structured_output(TripleList)

import time

# 5. Hàm Indexing (Trích xuất) từ văn bản với cơ chế RETRY
def index_text_to_triples(text: str, max_retries: int = 5):
    retry_count = 0
    backoff_time = 5  # Tăng thời gian bắt đầu lên 5s
    
    while retry_count < max_retries:
        try:
            result = extractor.invoke({"text": text})
            return result.triples
        except Exception as e:
            retry_count += 1
            error_msg = str(e).lower()
            
            # Kiểm tra xem có phải lỗi Too Many Requests không
            if "429" in error_msg or "too many requests" in error_msg:
                wait_time = backoff_time * 2
                print(f"   [!] PHÁT HIỆN RATE LIMIT (429): Đang chờ {wait_time}s để hồi phục...")
                time.sleep(wait_time)
                backoff_time = wait_time # Tiếp tục tăng cho lần sau
            elif retry_count < max_retries:
                print(f"   [!] Lỗi API (Lần {retry_count}): {e}")
                time.sleep(backoff_time)
                backoff_time *= 2
            else:
                print(f"   [X] Thất bại sau {max_retries} lần thử: {e}")
                return []

# 6. Hàm Indexing từ file CSV
def index_csv_to_triples(file_path: str, limit: int = 5, delay_between_rows: int = 3):
    print(f"--- Đang đọc file CSV: {file_path} (Giới hạn: {limit} dòng) ---")
    print(f"--- Khoảng nghỉ giữa các dòng: {delay_between_rows} giây để tránh Rate Limit ---")
    if not os.path.exists(file_path):
        print(f"Lỗi: Không tìm thấy file {file_path}")
        return

    df = pd.read_csv(file_path)
    all_results = []
    
    for index, row in df.head(limit).iterrows():
        context = (
            f"Công ty {row['Company']} có vốn hóa thị trường là {row['Market Cap']}. "
            f"Công ty này đặt tại {row['Country']} và hoạt động trong lĩnh vực {row['Sector']}, "
            f"ngành {row['Industry']}."
        )
        
        print(f"\n[Dòng {index+1}] Đang xử lý: {row['Company']}")
        triples = index_text_to_triples(context)
        
        if triples:
            for t in triples:
                print(f"   -> ({t.subject}) -> [{t.relationship}] -> ({t.object})")
                all_results.append(t)
        
        # Thêm khoảng nghỉ để tránh lỗi Too Many Requests
        if index < limit - 1:
            time.sleep(delay_between_rows)
            
    return all_results

# 7. (Tùy chọn) Lưu vào Neo4j (Đã cập nhật chọn Database)
class Neo4jIndexer:
    def __init__(self, uri, user, password, database="neo4j"):
        self.database = database
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"Không thể kết nối Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def add_triple(self, triple: Triple):
        if not self.driver: return
        # Sử dụng database được cấu hình
        with self.driver.session(database=self.database) as session:
            session.execute_write(self._create_relationship, triple)

    @staticmethod
    def _create_relationship(tx, triple: Triple):
        query = (
            "MERGE (s:Entity {name: $sub}) "
            "MERGE (o:Entity {name: $obj}) "
            "MERGE (s)-[r:RELATION {type: $rel}]->(o)"
        )
        tx.run(query, sub=triple.subject, obj=triple.object, rel=triple.relationship)

# 8. Main Execution
if __name__ == "__main__":
    csv_file = "Top 1000 technology companies.csv"
    output_file = "indexed_triples.json"
    
    # 1. Thực hiện indexing (giới hạn 15 dòng)
    results = index_csv_to_triples(csv_file, limit=10)
    
    if results:
        # 2. Lưu vào file JSON
        json_data = [t.model_dump() for t in results]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(f"\n[1/2] Đã lưu {len(results)} bộ triples vào '{output_file}'")

        # 3. Đẩy vào Neo4j (nếu cấu hình trong .env)
        neo4j_uri = os.getenv("NEO4J_URI")
        if neo4j_uri:
            neo4j_db = os.getenv("NEO4J_DATABASE", "neo4j")
            print(f"[2/2] Đang đẩy dữ liệu vào Neo4j (Database: {neo4j_db}) tại {neo4j_uri}...")
            
            indexer = Neo4jIndexer(
                uri=neo4j_uri, 
                user=os.getenv("NEO4J_USER", "neo4j"), 
                password=os.getenv("NEO4J_PASSWORD"),
                database=neo4j_db
            )
            
            if indexer.driver:
                for t in results:
                    indexer.add_triple(t)
                indexer.close()
                print(f">>> Đã đẩy xong dữ liệu vào database '{neo4j_db}' thành công!")
            else:
                print(">>> Thất bại: Không thể kết nối Neo4j. Vui lòng kiểm tra cấu hình .env")
        else:
            print("\n[Bỏ qua] Không tìm thấy cấu hình Neo4j trong .env để đẩy dữ liệu.")
            
        print("\n" + "="*50)
        print("HOÀN THÀNH QUÁ TRÌNH INDEXING")
        print("="*50)
