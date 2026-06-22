import os
import shutil
from turtle import st
from typing import List, Dict
from pathlib import Path

from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader, PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader

load_dotenv()


class LangChainService:
    """PDF 문서 또는 링크 기반 QA 서비스"""
    def __init__(self, faiss_db_path: str = "faiss_db", pdf_dir_path: str = "pdfs"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", 
            openai_api_key=api_key
        )
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0, 
            max_tokens=2048, 
            openai_api_key=api_key
        )
        self.faiss_db_path = faiss_db_path
        self.pdf_dir_path = pdf_dir_path
        self.vector_store = None
        self.retriever = None
        self.chain = None

        if Path(faiss_db_path).exists():
            self._load_vector_store()
    
    def ingest_all_resources(self, urls: List[str] = None):
        """
        [핵심] 지정된 pdfs/ 폴더 안의 PDF 파일들과 구글 Docs URL들을 
        동시에 크롤링/파싱하여 하나의 통합 벡터 스토어로 구축합니다.
        """
        all_documents = []
        
        try:

            # 1. 로컬 PDF 파일들 로드 (pdfs/ 디렉토리 내의 모든 PDF 자동 스캔)
            if os.path.exists(self.pdf_dir_path) and os.listdir(self.pdf_dir_path):
                print(f"[Ingest] 로컬 PDF 문서 로딩 중... 경로: {self.pdf_dir_path}")
                pdf_loader = PyPDFDirectoryLoader(self.pdf_dir_path)
                pdf_docs = pdf_loader.load()
                
                all_documents.extend(pdf_docs)
                print(f"[Ingest] PDF 로드 완료: {len(pdf_docs)} 페이지 발견.")


            # 2. 구글 Docs 웹 URL 로드
            if urls:
                print(f"[Ingest] 구글 공식 웹 문서 로딩 중... ({len(urls)}개 URL)")
                web_loader = WebBaseLoader(web_paths=urls)
                web_docs = web_loader.load()
                all_documents.extend(web_docs)
                print(f"[Ingest] 웹 문서 로드 완료: {len(web_docs)}개 페이지 검색됨.")


            if not all_documents:
                print("[Warning] 적재할 문서(PDF 또는 URL)가 데이터베이스에 존재하지 않습니다.")
                return


            # 3. 데이터가 섞여도 출처를 보존할 수 있도록 통합 텍스트 분할(Split)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200,
                chunk_overlap=150,
                separators=["\n\n", "\n", " ", ""]
            )
            splits = text_splitter.split_documents(all_documents)
            print(f"[Ingest] 통합 청크 분할 완료: 총 {len(splits)}개 청크 생성.")
            
            
            # 4. 통합 FAISS 벡터 스토어 빌드 및 로컬 저장            
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(splits, self.embeddings)
                
            else:
                self.vector_store.merge_from(FAISS.from_documents(splits, self.embeddings))

            self.vector_store.save_local(self.faiss_db_path)
            print(f"[Ingest] 'PDF + URL' 통합 벡터 DB가 '{self.faiss_db_path}'에 저장되었습니다.")
        
        except Exception as e:
            return {
                "answer": f"오류 발생: {str(e)}",
                "documents": []
            }

    def _load_vector_store(self):  
        """저장된 FAISS 벡터 store loading"""
        
        try: 
            self.vector_store = FAISS.load_local(
                self.faiss_db_path, 
                self.embeddings, 
                index_name = "index",
                allow_dangerous_deserialization=True
            )
            self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
            
            self._setup_chain()
        
        except Exception as e:
            st.error(f"벡터 스토어 로드 실패: {str(e)}")

    def _setup_chain(self):
        """
        통합 저장소(PDF 내용 + GA4/BQ Docs)를 한 번에 뒤져서 답변하는 쿼리 체인
        """
        if not self.vector_store:
            if not self._load_vector_store():
                return "임베딩된 지식 베이스가 없습니다. 인제스트를 먼저 실행해주세요."

        
        template = ChatPromptTemplate.from_messages([
            ("system", "당신은 이커머스 관련 그로스 해커이자 빅쿼리 데이터 엔지니어링 전문 AI입니다."),
            ("system", "pdf 형식의 마케팅/데이터 운영 관련 가이드라인과 구글 공식 문서(GA4 이벤트 태깅, 마케팅 캠페인 지표, 빅쿼리 데이터 마트 생성 기준 등)를 기반으로 복합 추론 QA 서비스를 제공합니다."),
            ("system", "아래 context 정보를 이용해서 답변하세요. PDF 문서 내용이 구글 공식 문서와 동일한 경우 구글 공식 문서를 우선으로 기반으로 합니다. 문서에 없는 정보는 '해당 내용은 제공된 설명서에서 확인할 수 없습니다'라고 답하세요.\ncontext:\n{context}"),
            ("human",  "question: \n{question}"),
            ("system", "answer (in Korean, Markdown format):")
        ])
        
        def format_docs(docs):
            formatted = []
            for doc in docs:
                # 메타데이터에서 출처(URL 또는 파일명)를 추출하여 LLM에게 힌트 제공
                source = doc.metadata.get('source', 'Unknown Source')
                formatted.append(f"[Source: {source}]\n{doc.page_content}")
            return "\n\n---\n\n".join(formatted)
        
        data = {
            "question": RunnablePassthrough(),
            "context": self.retriever | format_docs
        }
        self.chain = data | template | self.llm | StrOutputParser()

    def get_retrieved_docs(self, question: str) -> List[Dict]:
        """
        사용자의 질문과 가장 유사한 문서(PDF 청크 및 웹 링크 내용)를 FAISS 벡터 DB에서 검색하여 메타데이터와 함께 반환.
        """
        if not self.vector_store:
            if not self._load_vector_store():
                return []
        
        try:
            # FAISS DB에서 관련된 청크 검색
            docs = self.retriever.invoke(question)
            
            # FastAPI에서 JSON 형태로 프론트엔드에 전송할 수 있도록 딕셔너리로 변환
            result = []
            for doc in docs:
                result.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata  # 여기에 source, page 등의 정보가 들어있음
                })
                
            return result
        except Exception as e:
            print(f"[Search Error] 문서 검색 중 오류: {str(e)}")
            return []
    
