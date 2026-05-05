import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
from triple_indexer import Triple, Neo4jIndexer

# 1. Load cấu hình từ .env
load_dotenv()

def push_data():
    json_file = "indexed_triples.json"
    
    if not os.path.exists(json_file):
        print(f"Lỗi: Không tìm thấy file {json_file}")
        return

    # 2. Đọc dữ liệu từ JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Chuyển đổi list dictionary sang list Triple objects
    triples = [Triple(subject=d['subject'], relationship=d['relationship'], object=d['object']) for d in data]
    print(f"--- Đã đọc {len(triples)} bộ triples từ file JSON ---")

    # 3. Kết nối Neo4j
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_db = os.getenv("NEO4J_DATABASE", "neo4j")

    if not neo4j_uri or not neo4j_password:
        print("Lỗi: Thiếu cấu hình NEO4J_URI hoặc NEO4J_PASSWORD trong file .env")
        return

    print(f"--- Đang kết nối tới Neo4j (Database: {neo4j_db}) ---")
    indexer = Neo4jIndexer(uri=neo4j_uri, user=neo4j_user, password=neo4j_password, database=neo4j_db)
    
    if indexer.driver:
        print("--- Đang đẩy dữ liệu... ---")
        for i, t in enumerate(triples):
            indexer.add_triple(t)
            if (i + 1) % 10 == 0:
                print(f"   Đã đẩy {i + 1} bộ triples...")
        
        indexer.close()
        print("\n" + "="*50)
        print(f"THÀNH CÔNG: Đã đẩy toàn bộ {len(triples)} bộ triples vào Neo4j!")
        print("="*50)
    else:
        print("Lỗi: Không thể kết nối tới Neo4j. Vui lòng kiểm tra lại thông tin trong .env")

if __name__ == "__main__":
    push_data()
