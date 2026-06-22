import os
import shutil
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.responses import FileResponse

from langchain_service import LangChainService
from langgraph_service import run_agent

from dotenv import load_dotenv
load_dotenv()


# FastAPI
app = FastAPI(title="Commerce Growth AI Agent API", description="이커머스/GA4 데이터 에이전트 백엔드 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"], #["http://localhost:8501"]
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY 환경변수가 세팅되지 않았습니다. .env 파일을 확인하세요.")

# 업로드 폴더 생성
UPLOAD_DIR = Path("pdfs")
UPLOAD_DIR.mkdir(exist_ok=True)

# LangChainService 초기화 (한 번만, 정확한 파라미터로 선언!)
langchain_serivce = LangChainService(
    faiss_db_path="faiss_db",
    pdf_dir_path=str(UPLOAD_DIR)
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

langchain_serivce = LangChainService(
    faiss_db_path="faiss_db",
    pdf_dir_path=str(UPLOAD_DIR)
)

# --- Pydantic 요청/응답 모델 정의 ---
class QARequest(BaseModel):
    """ 질문 요청 모델 """
    question: str

class UrlIngestRequest(BaseModel):
    """ URL 링크 인제스트 요청 모델 """
    urls: List[str]

class ReportRequest(BaseModel):
    topic: str = "현재 이커머스 및 GA4 데이터 분석 분야의 최신 브리핑 리포트를 생성해줘."

class QueryResponse(BaseModel):
    """ 질문 응답 모델 """
    answer: str
    documents: list

@app.get("/")
def read_root():
    return {"message": "Commerce Growth QA SERVICE API"}    

# 질의응답 (Project A) API 엔드포인트
@app.post("/api/qa")
async def ask_question(req: QARequest):
    """ 사용자의 질문을 받아 QA 에이전트에게 전달하고 답변을 반환 """
    
    print(f"[API] QA 요청 수신: {req.question}")
    
    try:
        # LangGraph를 'qa' 모드로 호출
        answer = run_agent(task_type="qa", question=req.question)
        return {"answer": answer}
    
    except Exception as e:
        print(f"[API Error] {str(e)}")
        raise HTTPException(status_code=500, detail="서버에서 QA 처리 중 오류가 발생했습니다.")


# 리포트 자동 생성 (Project B) API 엔드포인트
@app.post("/api/report")
async def generate_report(req: ReportRequest):
    """ 트렌드 요약 리포트(PDF) 생성 에이전트를 가동 """
    
    print(f"[API] 리포트 생성 요청 수신: {req.topic}")
    
    try:
        summary_result = run_agent(task_type="report", question=req.topic)
        
        return {
            "status": "success",
            "message": "리포트 및 PDF가 성공적으로 생성되었습니다.",
            "summary": summary_result
        }
        
    except Exception as e:
        print(f"[API Error] {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다.")


# PDF 업로드 엔드포인트
@app.post("/upload-pdf")
def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    try:
        # 파일 저장
        file_path = UPLOAD_DIR / file.filename    # uploaded_files/A.pdf
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        langchain_serivce.ingest_all_resources()

        # PDF
        result = langchain_serivce.process_pdf(str(file_path))

        if result["status"] == "success":
            return {
                "message": f"파일 '{file.filename}'이 업로드되었으며, 지식 베이스(FAISS) 갱신이 완료되었습니다.",
                "filename": file.filename,
                "chunks_count": result["chunks_count"],
                "pages_count": result["pages_count"]
                
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 실패: {str(e)}")
    

# # 질의응답 앤드 포인트
# @app.post("/query/stream")
# def query_stream(request: QARequest):

#     def generate():
#         for chunk in langchain_serivce.query_stream(request.question):
#             yield chunk

#     return StreamingResponse(
#         generate(),
#         media_type="text/plain"
#     )
    
# @app.post("/query", response_model=QueryResponse)
# def query(request: QARequest):
#     result = langchain_serivce.query(request.question)
#     return result

# 공식 문서 및 외부 웹 링크 인제스트 엔드포인트
@app.post("/api/ingest-urls")
async def ingest_urls(req: UrlIngestRequest):
    """ 구글 Docs, GA4/빅쿼리 공식 문서 등 외부 링크를 전달받아 벡터 DB에 인제스트(적재) """
    print(f"[API] URL 인제스트 요청 수신: {req.urls}")
    
    if not req.urls:
        raise HTTPException(status_code=400, detail="적재할 URL 링크가 한 개 이상 필요합니다.")
        
    try:
        langchain_serivce.ingest_all_resources(urls=req.urls)
        
        return {
            "status": "success",
            "message": f"총 {len(req.urls)}개의 공식 문서 웹 링크가 성공적으로 벡터 DB에 적재되었습니다."
        }
    except Exception as e:
        print(f"[API Error] {str(e)}")
        raise HTTPException(status_code=500, detail=f"웹 문서 URL 처리 실패: {str(e)}")


# 생성된 PDF 파일 다운로드 API 엔드포인트
@app.get("/api/download-report")
async def download_report():
    """ 서버(outputs/ 폴더)에 생성된 최신 PDF 리포트 파일을 클라이언트에게 전송 """
    file_path = "outputs/latest_report.pdf"
    
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename="Commerce_Trend_Report.pdf", 
            media_type='application/pdf'
        )
    else:
       
        raise HTTPException(status_code=404, detail="생성된 리포트 파일이 없습니다. 먼저 리포트를 생성해주세요.")
    
# 관련 문서 검색 앤드 포인트
@app.post("/documents")
def get_documents(request: QARequest):
    documents = langchain_serivce.get_retrieved_docs(request.question)
    return {"documents": documents}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)