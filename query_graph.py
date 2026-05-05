import os
import time
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from neo4j import GraphDatabase

# 1. Load cấu hình từ file .env
load_dotenv()

class GraphRAGSystem:
    def __init__(self):
        # Khởi tạo LLM NVIDIA
        self.llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct", temperature=0)
        
        # Kết nối Neo4j
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))
        )
        self.database = os.getenv("NEO4J_DATABASE", "techgraph")

    def close(self):
        self.driver.close()

    # --- BƯỚC 2: Trích xuất thực thể chính (Có cơ chế Retry mạnh) ---
    def extract_entity(self, question: str, max_retries: int = 5):
        retry_count = 0
        backoff = 10
        while retry_count < max_retries:
            try:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Bạn là một AI chuyên trích xuất thực thể. Hãy tìm thực thể chính (tên công ty/tổ chức) trong câu hỏi. CHỈ TRẢ VỀ TÊN, không giải thích."),
                    ("user", f"Trích xuất thực thể từ câu hỏi: {question}")
                ])
                chain = prompt | self.llm
                return chain.invoke({}).content.strip()
            except Exception as e:
                retry_count += 1
                if "429" in str(e) or "too many requests" in str(e).lower():
                    print(f"      [!] Bị giới hạn API (429). Đang chờ {backoff}s...")
                    time.sleep(backoff)
                    backoff += 20 # Chờ lâu hơn ở lần sau
                else:
                    time.sleep(2)
        return "Unknown"

    # --- BƯỚC 3: Truy vấn đồ thị 2-hop ---
    def get_graph_context(self, entity_name: str):
        # Query Cypher lấy quan hệ trong vòng 2 bước nhảy
        query = (
            "MATCH (e:Entity {name: $name})-[r1:RELATION]-(n1) "
            "OPTIONAL MATCH (n1)-[r2:RELATION]-(n2) "
            "RETURN e.name as s1, type(r1) as r1_type, n1.name as o1, "
            "type(r2) as r2_type, n2.name as o2"
        )
        
        context_parts = []
        with self.driver.session(database=self.database) as session:
            results = session.run(query, name=entity_name)
            for record in results:
                # Thông tin 1-hop
                context_parts.append(f"({record['s1']}) có quan hệ [{record['r1_type']}] với ({record['o1']})")
                # Thông tin 2-hop (nếu có)
                if record['o2']:
                    context_parts.append(f"({record['o1']}) có quan hệ [{record['r2_type']}] với ({record['o2']})")
        
        return "\n".join(list(set(context_parts))) # Loại bỏ trùng lặp

    def answer_single_question(self, question: str, max_retries: int = 5):
        # 1. Trích xuất thực thể
        entity = self.extract_entity(question)
        
        # 2. Lấy dữ liệu từ đồ thị
        graph_context = self.get_graph_context(entity)
        
        # 3. Gửi cho LLM trả lời với ngữ cảnh đồ thị
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là trợ lý ảo chuyên sâu về công nghệ. 
Dưới đây là thông tin thực tế từ Đồ thị Tri thức (Knowledge Graph) của chúng tôi. 
Hãy sử dụng nó để trả lời câu hỏi của người dùng một cách chính xác nhất.

THÔNG TIN TỪ ĐỒ THỊ:
{context}"""),
            ("user", "{question}")
        ])
        
        answer_chain = final_prompt | self.llm
        
        retry_count = 0
        backoff = 10
        while retry_count < max_retries:
            try:
                response = answer_chain.invoke({"context": graph_context, "question": question})
                return response.content
            except Exception as e:
                retry_count += 1
                if "429" in str(e) or "too many requests" in str(e).lower():
                    print(f"      [!] Bị giới hạn API (429) khi tạo câu trả lời. Đang chờ {backoff}s...")
                    time.sleep(backoff)
                    backoff += 20
                else:
                    time.sleep(2)
        return "Lỗi: Không thể nhận câu trả lời từ API sau nhiều lần thử."

    # --- BƯỚC 4: Tổng hợp và Trả lời (Vòng lặp Chat) ---
    def chat(self):
        print("--- HỆ THỐNG TRUY VẤN GRAPH RAG ĐÃ SẴN SÀNG ---")
        while True:
            user_input = input("\nĐặt câu hỏi của bạn (gõ 'exit' để thoát): ")
            if user_input.lower() in ['exit', 'quit']: break
            
            print(f"[*] Đang xử lý câu hỏi...")
            answer = self.answer_single_question(user_input)
            
            print("\n[TRẢ LỜI]:")
            print(answer)

if __name__ == "__main__":
    system = GraphRAGSystem()
    try:
        system.chat()
    finally:
        system.close()
