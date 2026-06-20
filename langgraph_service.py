import operator
from typing import TypedDict, Annotated, Sequence, Optional
from datetime import date
import os

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader

from tavily import TavilyClient


from langchain_service import LangChainService
from pdf_generator import generate_pdf 


# --- 툴(Tools) 정의 영역 ---
@tool
def fetch_report_list(topic: str) -> str:
    """ Tavily Search API를 사용하여 입력된 주제(topic)와 관련된 최신 기사, 리포트, 트렌드 문서를 수집.
    사용자의 질문이 명확하지 않을 때(Condition C), 최신 트렌드 브리핑을 작성하기 위한 기초 데이터로 활용 """
    
    print(f"[Tool 실행] Tavily API로 '{topic}' 관련 심층 데이터 수집 중...")

    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        return "Error: 시스템에 TAVILY_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요."

    # Tavily 클라이언트 초기화
    client = TavilyClient(api_key=api_key)

    try:
        # search_depth="advanced"로 설정하면 더 깊이 있는 고품질 리서치 결과를 가져옵니다.
        response = client.search(
            query=topic,
            search_depth="advanced",
            max_results=3,       # 상위 3개 핵심 리포트만 추출
            include_answer=False # 자체 요약 답변 대신 원본 소스 데이터에 집중
        )

        results = response.get("results", [])
        
        if not results:
            return f"'{topic}'에 대한 최근 검색 결과가 없습니다."

        formatted_results = f"[{topic} - Tavily 심층 검색 결과]\n\n"
        
        for i, res in enumerate(results, 1):
            title = res.get("title", "제목 없음")
            content = res.get("content", "내용 없음")
            url = res.get("url", "링크 없음")
            
            formatted_results += f"{i}. 📑 문서 제목: {title}\n"
            formatted_results += f"   핵심 내용(본문 추출): {content}\n"
            formatted_results += f"   원본 출처: {url}\n\n"

        return formatted_results

    except Exception as e:
        return f"Tavily 리서치 중 오류 발생: {str(e)}"


@tool
def get_pdf_text(file_name: str) -> str:
    """ 지정된 PDF 파일의 내용을 파싱하여 원문 텍스트를 반환. (예: file_name="마케팅_가이드.pdf") """
    print(f"[Tool 실행] '{file_name}' PDF 파싱 중...")
    
    # pdfs 폴더 경로 설정 (langchain_service.py의 구조와 동일하게 맞춤)
    file_path = os.path.join("pdfs", file_name)
    
    if not os.path.exists(file_path):
        return f"Error: '{file_path}' 파일을 찾을 수 없습니다. 파일명을 확인해주세요."
        
    try:
        # 실제 PDF 로드 및 텍스트 추출
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        # 페이지별 텍스트를 하나로 결합
        text = "\n".join([page.page_content for page in pages])
        
        # LLM의 컨텍스트 윈도우(토큰 한도)를 초과하지 않도록 너무 긴 경우 자름 (예: 6000자)
        if len(text) > 6000:
            return text[:6000] + "\n\n...[텍스트가 너무 길어 생략됨]..."
            
        return text
        
    except Exception as e:
        return f"PDF 파싱 중 오류 발생: {str(e)}"


@tool
def get_web_text(url: str) -> str:
    """
    구글 GA4, 빅쿼리 공식 문서 등 특정 웹페이지 URL의 본문 내용을 파싱하여 텍스트로 반환합니다.
    """
    print(f"[Tool 실행] 웹 링크 파싱 중... URL: {url}")
    
    try:
        # 웹페이지 로드 및 텍스트 추출
        loader = WebBaseLoader(web_paths=[url])
        docs = loader.load()
        
        text = "\n".join([doc.page_content for doc in docs])
        
        # 마찬가지로 토큰 한도 관리를 위해 텍스트 길이 제한
        if len(text) > 6000:
            return text[:6000] + "\n\n...[텍스트가 너무 길어 생략됨]..."
            
        return text
        
    except Exception as e:
        return f"웹 페이지 파싱 중 오류 발생: {str(e)}"
# @tool
# def send_report_email(content: str, email_address: str) -> str:
#     """작성된 브리핑 보고서를 이메일로 발송합니다."""
#     # 실제로는 smtplib 등을 활용한 이메일 발송 로직이 들어갑니다.
#     print(f"[Tool 실행] 이메일 발송 중... 받는 사람: {email_address}")
#     return "이메일 발송이 성공적으로 완료되었습니다."

tools = [fetch_report_list, get_pdf_text, get_web_text]
tool_node = ToolNode(tools) 

# 에이전트 상태(State) 정의
class AgentState(TypedDict):
    task_type: str            # "qa" (질의응답) or "report" (리포트 생성)
    question: Optional[str]   # 사용자가 입력한 질문 (QA 모드일 때 사용)
    answer: Optional[str]     # LLM 생성 답변
    report_status: Optional[str] # 리포트 생성 상태 메시지
    summary_result: Optional[str] # LangChain LLM 요약 결과 저장
    error: Optional[str]      # 에러 기록
    messages: Annotated[Sequence[BaseMessage], add_messages] # LLM이 툴을 호출하고 결과를 기억

# LangChainService 인스턴스 초기화
llm_service = LangChainService(faiss_db_path="faiss_db")

# 라우터 (조건부 엣지 함수)
def route_task(state: AgentState) -> str:
    """task_type에 따라 실행할 노드를 결정"""
    if state["task_type"] == "qa":
        return "qa_node"
    elif state["task_type"] == "report":
        return "report_node"
    else:
        return END

# 질의응답 처리
def qa_node(state: AgentState) -> dict:
    """ 사용자 질문을 받아 LangChainService를 통해 답변 생성 """
    
    print("[Node] QA 노드 실행 중...")
    question = state.get("question")
    
    if not question:
        return {"error": "질문 내용이 없습니다."}

    try:
        
        if llm_service.chain is None:
            loaded = llm_service._load_vector_store()
            if not loaded:
                return {
                    "answer": "벡터 DB가 로드되지 않았습니다. 문서를 먼저 인제스트 해주세요."
                }
        
        # 앞서 만든 langchain_service.py의 체인을 실행
        response = llm_service.chain.invoke(question)
        return {"answer": response}
    
    except Exception as e:
        return {"error": f"QA 처리 중 오류 발생: {str(e)}"}


# 노드(Node) 정의: 리포트 생성 처리
def report_node(state: AgentState) -> dict:
    """ 최신 트렌드 요약 및 리포트 생성 작업을 수행 """
    
    print("[Node] 리포트 생성 노드 실행 중...")
    
    try:
        
        report_prompt =  """
# Role
당신은 이커머스 마케팅, GA4 데이터 분석, 그리고 데이터 마트 구축에 특화된 전문 AI 에이전트입니다. 사용자의 질문 의도를 정확히 파악하여, 아래에 정의된 3가지 케이스 중 하나로 분류하고 지정된 [출력 포맷]에 맞추어 답변해야 합니다.

---
# Rules & Process
사용자의 입력(Input)을 분석하여 다음 조건(Condition)에 따라 답변을 생성하세요.

* **[Condition A: 개념 질의]** 특정 마케팅/데이터/IT '개념'이나 '용어'에 대해 질문한 경우
* **[Condition B: 트러블슈팅 및 쿼리]** 데이터 마트 적재 과정의 '이슈(에러)', '데이터 모델링', 'SQL/빅쿼리 작성'에 대해 질문한 경우
* **[Condition C: 기본/기타 질의]** 위 두 가지에 해당하지 않거나, 광범위한 질문인 경우
---

# Output Formats
각 조건(Condition)에 따라 반드시 아래의 마크다운 형식을 엄격하게 지켜서 답변하세요.

## [Condition A: 개념 질의]
■ 📚 개념 가이드: [질문한 개념명]

- **정의**: (해당 개념에 대한 명확하고 간결한 정의)
- **배경 및 목적**: (왜 이 개념/기술이 등장했고, 어떤 목적을 가지는지)
- **핵심 조건 및 특징**: (핵심적인 작동 원리나 주요 특징 3가지 이내)
- **적용 예시**: (이커머스 또는 마케팅 실무에서의 실제 활용 예시)
- **장단점**: (도입 시의 이점과 한계점)
- **유사 개념과 비교**: (혼동하기 쉬운 유사 개념과의 차이점 대조표 또는 요약)
- **주의 사항**: (실무 적용 시 유의해야 할 점)

## [Condition B: 트러블슈팅 및 쿼리]
■ 🛠️ 데이터 엔지니어링 & 쿼리 솔루션

- **이슈 진단**: (질문한 문제나 쿼리 요구사항에 대한 원인 분석)
- **해결 방법 (접근 로직)**: (문제를 해결하기 위한 단계별 로직. 예: 10개년 매출 청구 데이터 적재 시, 시점별로 컬럼 수가 다른 테이블을 통합하기 위한 매핑 규칙 등)
- **예시 쿼리문 (SQL)**:
  ```sql
  -- 여기에 최적화된 표준 SQL 또는 BigQuery 문법을 작성하세요.
  ```
- 쿼리 설명: (사용한 주요 함수나 로직에 대한 부연 설명)

## [Condition C: 기본/기타 질의]
■ 📈 E-Commerce & GA4 최신 트렌드 브리핑
(사용자의 질문이 구체적이지 않은 경우, 현재 이커머스 및 GA4 데이터 분석에서 가장 주목받는 핵심 이슈 3가지를 정리하여 제공합니다.)

[트렌드 키워드 1]: (상세 내용 및 실무적 시사점)
    - 주제: (주제)
    - 내용: (한 두 문장 요약)
[트렌드 키워드 2]: (상세 내용 및 실무적 시사점)
    - 주제: (주제)
    - 내용: (한 두 문장 요약)
[트렌드 키워드 3]: (상세 내용 및 실무적 시사점)
    - 주제: (주제)
    - 내용: (한 두 문장 요약)

## Constraints
모든 답변은 이모티콘 사용을 자제하고 (포맷에 포함된 기본 이모티콘 제외), 전문적이고 간결한 한국어로 작성하세요.
        """
        if llm_service.chain is None:
            llm_service._load_vector_store()
            
        summary = llm_service.chain.invoke(report_prompt)
        
        # 추후 pdf_generator.py 모듈을 연결하여 PDF를 생성하는 로직 추가
        # generate_pdf(summary, "outputs/latest_report.pdf")
        output_pdf_path = "outputs/latest_report.pdf"
        generate_pdf(text=summary, file_path=output_pdf_path)
        print(f"[Process] 리포트가 {output_pdf_path}에 성공적으로 생성되었습니다.")
        
        return {
            "summary_result": summary,
            "report_status": f"{output_pdf_path} 생성 완료"
        }
        
    except Exception as e:
        return {"error": f"리포트 생성 중 오류 발생: {str(e)}"}


# 5. LangGraph 워크플로우 빌드
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("qa_node", qa_node)
workflow.add_node("report_node", report_node)

# 진입점 설정 (시작하자마자 route_task를 통해 분기)
workflow.set_conditional_entry_point(
    route_task,
    {
        "qa": "qa_node",
        "report": "report_node"
    }
)

# 노드 종료점 연결 (각 작업이 끝나면 그래프 종료)
workflow.add_edge("qa_node", END)
workflow.add_edge("report_node", END)

# 그래프 컴파일 (실행 가능한 앱으로 변환)
agent_app = workflow.compile()


# 외부(FastAPI/Streamlit)에서 호출하기 위한 함수
def run_agent(task_type: str, question: str = "") -> dict:
    """ UI나 API에서 쉽게 에이전트를 호출할 수 있는 함수 """
    
    initial_state = {
        "task_type": task_type,
        "question": question,
        "answer": None,
        "report_status": None,
        "summary_result": None,
        "error": None,
        "messages": [] 
    }
    
    # 그래프 실행
    result = agent_app.invoke(initial_state)
    
    return result["answer"] if task_type == "qa" else result["summary_result"]