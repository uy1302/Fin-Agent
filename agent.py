import os 
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain.schema import HumanMessage
from dotenv import load_dotenv
from typing import Annotated
import re
from datetime import datetime, timedelta


load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

class State(TypedDict):
    text: str
    classification: str
    entities: List[str]
    summary: str
    stock_symbols: List[str]
    symbol_data_list: List[str]
    chart_paths: List[str]
    errors: List[str]

llm = ChatVertexAI(model="gemini-2.0-flash", temperature=0.0, max_tokens=1000)

def classification_node(state: State):
    prompt = PromptTemplate(
        input_variables =["text"],
        template="Phân loại nội dung sau thành các tín hiệu: tích cực, trung bình, và tiêu cực. \n\nText: {text}\n\nSignal:"
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    classification = llm.invoke([message]).content.strip()

    return {"classification": classification}

def entity_extraction_node(state: State):
    prompt = PromptTemplate(
        input_variables =["text"],
        template="Extract all the entities (Person, Organization, Location) from the following text. Provide the result as a comma-separated list.\n\nText: {text}\n\nEntities:"
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    entities = llm.invoke([message]).content.strip().split(", ")
 
    return {"entities": entities}

def summarize_node(state: State):
    summarize_prompt = PromptTemplate.from_template(
        """Summarize the following text in one short sentence in Vietnamese.
        
        Text: {text}
        
        Summary:"""
    )

    chain = summarize_prompt | llm
    response = chain.invoke({"text": state["text"]})

    return {"summary": response.content}

def prepare_stock_data_node(state: State):
    """Prepares stock data for all stock symbols found."""
    stock_symbols = state.get("stock_symbols", [])
    
    if not stock_symbols:
        return {"symbol_data_list": [], "errors": ["No stock symbols found in the text"]}
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    interval = "1D"  
    
    symbol_data_list = []
    
    for symbol in stock_symbols:
        symbol_data = f"{symbol}|{start_date}|{end_date}|{interval}"
        symbol_data_list.append(symbol_data)
    
    return {"symbol_data_list": symbol_data_list}




workflow = StateGraph(State)

workflow.add_node("classification_node", classification_node)
workflow.add_node("entity_extraction", entity_extraction_node)
workflow.add_node("summarize", summarize_node)
workflow.add_node("prepare_stock_data", prepare_stock_data_node)

workflow.set_entry_point("classification_node")
workflow.add_edge("classification_node", "entity_extraction")
workflow.add_edge("entity_extraction", "summarize")
workflow.add_edge("summarize", "prepare_stock_data")
workflow.add_edge("summarize", END)

app = workflow.compile()

sample_text = """
Con trai Chủ tịch Hội đồng quản trị Chứng khoán SSI vừa bán 154.496 cổ phiếu SSI, chuyển quyền sở hữu cho Công ty TNHH Đầu tư NDH.

Theo công bố gửi Sở Giao dịch Chứng khoán TP HCM (HoSE), ông Nguyễn Duy Linh, con trai Chủ tịch Công ty Chứng khoán SSI Nguyễn Duy Hưng, vừa bán 154.496 cổ phiếu SSI trong ngày 27/3 nhằm chuyển quyền sở hữu cho doanh nghiệp gia đình. Sau giao dịch, ông Duy Linh không còn nắm giữ cổ phiếu SSI nào.

Số cổ phiếu này được chuyển nhượng cho Công ty TNHH Đầu tư NDH, giúp doanh nghiệp nâng tỷ lệ sở hữu tại SSI lên 8,364%, tương đương 164,26 triệu cổ phiếu. Công ty này do ông Nguyễn Duy Hưng giữ chức Chủ tịch Hội đồng quản trị (HĐQT).

Theo báo cáo vào cuối 2024, ông Nguyễn Duy Hưng nắm 15,18 triệu cổ phiếu SSI, tương đương hơn 0,7% vốn. Con trai cả của ông, Nguyễn Duy Khánh, thành viên HĐQT SSI, sở hữu 4,5 triệu cổ phiếu (0,232% vốn).

Ông Nguyễn Hồng Nam, Tổng giám đốc SSI - em trai ông Hưng - sở hữu 2,6 triệu cổ phiếu (0,135% vốn). Một người em khác của ông Hưng là ông Nguyễn Mạnh Hùng giữ 10,4 triệu cổ phiếu (0,531% vốn).

Sau giao dịch trên, tổng số cổ phiếu mà Công ty TNHH Đầu tư NDH cùng các cá nhân liên quan nắm giữ vượt 197 triệu đơn vị, chiếm 10,03% vốn điều lệ SSI.

Chứng khoán SSI được thành lập năm 1999, là một trong những công ty chứng khoán thành lập đầu tiên tại thị trường chứng khoán Việt Nam. Theo tài liệu phiên họp đại hội cổ đông thường niên 2025, dự kiến tổ chức ngày 18/4, SSI dự báo VN-Index dao động trong khoảng 1.450-1.500 điểm, với thanh khoản bình quân 19.500 tỷ đồng một phiên.

Trên cơ sở này, công ty đặt mục tiêu doanh thu hợp nhất năm nay đạt 9.695 tỷ đồng, lợi nhuận trước thuế 4.252 tỷ, lần lượt tăng 15% và 20% so với 2024.

Công ty cũng dự kiến chào bán chứng khoán riêng lẻ trong giai đoạn 2025-2026 để nâng vốn điều lệ lên hơn 20.779 tỷ đồng. Về phân phối lợi nhuận năm 2024, SSI đề xuất chia cổ tức tiền mặt tỷ lệ 10%, tức mỗi cổ phiếu nhận 1.000 đồng.
"""

state_input = {"text": sample_text}

result = app.invoke(state_input)

print("Classification:", result["classification"])
print("\nEntities:", result["entities"])
print("\nSummary:", result["summary"])
print("\nExtracted Stock Symbols:", result["stock_symbols"])

if "chart_path" in result:
    print("\nChart:", result["chart_path"])
elif "error" in result:
    print("\nError:", result["error"])