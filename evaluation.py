import os
import pandas as pd
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from query_graph import GraphRAGSystem

# Load môi trường
load_dotenv()

# 1. Thiết lập Flat RAG (Vector-based RAG)
def setup_flat_rag(csv_path):
    print("--- Đang khởi tạo Flat RAG (Vector Store) ---")
    df = pd.read_csv(csv_path)
    documents = []
    for _, row in df.iterrows():
        # Chuyển mỗi dòng thành một đoạn văn bản để index vào Vector DB
        text = (f"Công ty {row['Company']} (Stock: {row['Stock']}) có vốn hóa {row['Market Cap']}. "
                f"Quốc gia: {row['Country']}. Lĩnh vực: {row['Sector']}, Ngành: {row['Industry']}.")
        documents.append(Document(page_content=text, metadata={"company": row['Company']}))
    
    # Sử dụng model embedding nhẹ từ HuggingFace
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Tạo Vector Store bằng FAISS
    vector_store = FAISS.from_documents(documents, embeddings)
    return vector_store

import time

def query_flat_rag(vector_store, llm, question, max_retries: int = 5):
    # Bước tìm kiếm tương đồng
    docs = vector_store.similarity_search(question, k=3)
    context = "\n".join([d.page_content for d in docs])
    
    retry_count = 0
    backoff = 10
    while retry_count < max_retries:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Bạn là trợ lý ảo. Hãy trả lời câu hỏi dựa trên NGỮ CẢNH VĂN BẢN sau đây. Nếu không thấy thông tin trong ngữ cảnh, hãy dùng kiến thức của bạn.\n\nNGỮ CẢNH:\n{context}"),
                ("user", "{question}")
            ])
            chain = prompt | llm
            return chain.invoke({"context": context, "question": question}).content
        except Exception as e:
            retry_count += 1
            if "429" in str(e) or "too many requests" in str(e).lower():
                print(f"      [!] Flat RAG bị Rate Limit (429). Đang chờ {backoff}s...")
                time.sleep(backoff)
                backoff += 20
            else:
                time.sleep(2)
    return "Lỗi: Flat RAG không thể trả lời sau nhiều lần thử."

# 2. Danh sách 20 câu hỏi benchmark để đánh giá
questions = [
    "1. Những công ty nào trong top 10 có cùng quốc gia với Apple Inc và thuộc ngành Semiconductors?",
    "2. So sánh lĩnh vực hoạt động của Microsoft Corporation và Nvidia Corporation.",
    "3. Tìm các công ty ở South Korea trong danh sách này và cho biết họ làm về ngành gì?",
    "4. Adobe Inc và Salesforce có cùng ngành hoạt động không?",
    "5. Dựa trên danh sách, Nvidia Corporation có mối quan hệ gián tiếp nào với Microsoft không?",
    "6. Công ty nào có vốn hóa cao nhất ở Ireland?",
    "7. Ngành Semiconductors có bao nhiêu đại diện trong top 20?",
    "8. Công ty Broadcom Inc và ASML Holding N.V. có điểm gì chung về Sector và Industry?",
    "9. Các công ty ở Netherlands thường hoạt động trong lĩnh vực nào?",
    "10. Liệt kê các công ty thuộc mảng Software—Application và quốc gia của họ.",
    "11. Công ty Samsung Electronics Co., Ltd. có cùng Sector với Apple không?",
    "12. Trong top 50, có bao nhiêu công ty thuộc United States?",
    "13. So sánh Market Cap của Accenture plc và Oracle Corporation.",
    "14. Lĩnh vực Technology bao gồm những ngành (Industry) cụ thể nào trong top 15?",
    "15. Công ty nào đứng đầu ngành Semiconductor Equipment & Materials?",
    "16. Có bao nhiêu công ty trong top 10 hoạt động về Software—Infrastructure?",
    "17. Công ty Taiwan Semiconductor Manufacturing Company Limited đặt tại quốc gia nào?",
    "18. Lĩnh vực hoạt động chính của Salesforce là gì?",
    "19. Các công ty semiconductors trong danh sách thường tập trung ở những quốc gia nào?",
    "20. Sự khác biệt giữa Sector và Industry của các công ty Top 10 là gì?"
]

def main():
    csv_file = "Top 1000 technology companies.csv"
    
    # Khởi tạo 2 hệ thống
    vector_store = setup_flat_rag(csv_file)
    llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct", temperature=0)
    graph_rag = GraphRAGSystem()

    print("\n" + "="*80)
    print("BẮT ĐẦU SO SÁNH: FLAT RAG vs GRAPH RAG")
    print("="*80)

    for i, q in enumerate(questions):
        print(f"\n[CÂU HỎI {i+1}]: {q}")
        
        print("\n--- [HỆ THỐNG 1: FLAT RAG] ---")
        try:
            flat_ans = query_flat_rag(vector_store, llm, q)
            print(f"Trả lời: {flat_ans}")
        except Exception as e:
            print(f"Lỗi Flat RAG: {e}")
        
        print("\n--- [HỆ THỐNG 2: GRAPH RAG] ---")
        try:
            graph_ans = graph_rag.answer_single_question(q)
            print(f"Trả lời: {graph_ans}")
        except Exception as e:
            print(f"Lỗi Graph RAG: {e}")
        
        print("\n" + "-"*80)
        # Nghỉ 15 giây giữa các câu hỏi để tránh Rate Limit
        print("--- Đang chờ 15 giây trước câu hỏi tiếp theo... ---")
        time.sleep(15)

    graph_rag.close()

if __name__ == "__main__":
    main()
