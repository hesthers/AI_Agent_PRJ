import streamlit as st
import requests
from pathlib import Path
import os
import time


# FastAPI 서버 주소
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="E-Commerce Growth",
    page_icon="🚀",
    layout="wide"
)

st.title("E-Commerce Growth Analytics & Agentic RAG System")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []  #대화 기록 저장

if "retrieved_docs" not in st.session_state:
    st.session_state.retrieved_docs = []   #검색된 문서 저장

# ==========================================
# ⬅️ 사이드바 (Sidebar) : 지식 인제스트 & 메뉴 선택
# ==========================================
with st.sidebar:
    st.sidebar.header("📄 문서 업로드")

    uploaded_file = st.sidebar.file_uploader(
        "PDF 파일을 선택하세요",
        type = ["pdf"],  #pdf 파일만 허용
        help = "PDF 파일을 업로드하면 자동으로 분석됩니다."
    )

    # 파일 업로드 
    if uploaded_file is not None:
        if st.sidebar.button("업로드 및 처리"):
            with st.sidebar.status("PDF 처리 중...", expanded=True) as status:
                    try: 
                        with st.spinner("PDF를 업로드하고 벡터 DB를 갱신 중입니다..."):
                            # # FastAPI /upload-pdf 엔드포인트로 파일 전송
                            files = {
                                "file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")
                            }
                            response = requests.post(f"{API_URL}/upload-pdf", files=files)
                            
                            # 응답 처리
                            if response.status_code == 200: #상태를 확인
                                result = response.json()
                                status.update(label = "처리완료!", state = "complete")
                                st.sidebar.success(result["message"])
                                
                                if "pages_count" in result:
                                    st.info(f"페이지 수: {result['pages_count']}")
                                    st.info(f"청크 수: {result['chunks_count']}")
                                
                            else:
                                status.update(label = "처리실패!", state = "error")
                                st.sidebar.error(f"오류: {response.json().get('detail', '알 수 없는 오류')}")
                    
                    except Exception as e:
                        status.update(label = "처리실패!", state = "error")
                        st.sidebar.error(f"오류: {str(e)}")

    else:
        st.warning("먼저 PDF 파일을 선택해주세요.")

    st.divider()
    
    # 웹 링크(URL) 인제스트 UI
    st.subheader("🌐 공식 문서 링크 학습")
    url_input = st.text_area("GA4, 빅쿼리 공식 문서 URL을 입력하세요. (여러 개일 경우 쉼표(,)로 구분)")

    if st.button("URL 학습시키기"):
        if url_input.strip():
            with st.spinner("웹 페이지를 파싱하여 벡터 DB에 적재 중입니다..."):
                url_list = [url.strip() for url in url_input.split(",") if url.strip()]
                
                # FastAPI /api/ingest-urls 엔드포인트로 전송
                res = requests.post(f"{API_URL}/api/ingest-urls", json={"urls": url_list})
                
                if res.status_code == 200:
                    st.success(res.json().get("message", "URL 적재 완료!"))
                else:
                    st.error(f"오류 발생: {res.text}")
        else:
            st.warning("URL을 입력해주세요.")    

    st.divider()
    
    # 메인 기능 메뉴 선택
    st.subheader("🚀 기능 선택")
    menu = st.radio(
        "사용할 기능을 선택하세요:",
        ["🤖 QA 챗봇", "📊 리포트 생성"]
    )              
    
    # 대화 기록 초기화 버튼
    if st.sidebar.button("🗑️ 대화 기록 초기화"):
        st.session_state.messages = []
        st.session_state.retrieved_docs = []
        st.rerun()  # 페이지 새로고침
               
# =======================================================
# 🖥️ 메인 화면 (Main Area) : 기능별 UI 구현 (메인 인터페이스)
# =======================================================
if menu == "🤖 QA 챗봇":
    st.subheader("💬 CommerceGrowth-QA 챗봇")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("질문을 입력하세요 (예: 퍼포먼스 마케팅 ROAS 마트 설계 기준은?)"):
        
        # 에이전트 메시지를 최종 문자열로 세션에 한 번만 저장 (중복 제거)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
    
        # AI 응답 생성 및 스트리밍 표시
        with st.chat_message("assistant"):
            message_placeholder = st.empty()  
            full_response = ""
            
            try:
            
                response = requests.post(
                    f"{API_URL}/api/qa", # main.py에 있는 스트리밍 엔드포인트 사용
                    json={
                        "question": prompt
                    },
                    stream=True
                )
                
                if response.status_code == 200:
                    answer = response.json().get("answer", "답변을 가져오지 못했습니다.")                    
                
                    for char in answer:
                        full_response += char
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.03)  # 속도 조절 
                    
                    # 타이핑이 끝나면 커서(▌)를 지우고 깔끔하게 렌더링
                    message_placeholder.markdown(full_response)
                    
                else:
                    st.error(f"서버 에러: {response.status_code}")
                    full_response = "답변을 가져오지 못했습니다."
                    
            except requests.exceptions.ConnectionError:
                st.error("FastAPI 백엔드 서버가 켜져 있는지 확인해주세요. (포트 8000)")
                
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
        
        
            st.session_state.messages.append(
                {
                    "role": "assistant", 
                    "content": full_response
                }
            )
   
         # 📚 관련 문서 검색 및 하단 표시 (UI 고도화)
        
        try:
            doc_response = requests.post(
                f"{API_URL}/documents",
                json={"question": prompt}
            )
            
            if doc_response.status_code == 200:
                retrieved_docs = doc_response.json().get("documents", [])
                
                if retrieved_docs:
                    st.divider()
                    st.markdown("#### 📚 참고한 관련 문서 및 링크")
                    
                    for idx, doc in enumerate(retrieved_docs, 1):
                        with st.expander(f"참고 문서 {idx}"):
                            metadata = doc.get("metadata", {})
                            source = metadata.get("source", "알 수 없는 출처")
                            
                            # 웹 링크(URL)인지 파일(PDF)인지 구분하여 표시
                            if source.startswith("http"):
                                st.markdown(f"**🌐 출처 (웹 링크):** [{source}]({source})")
                                
                            else:
                                file_name = os.path.basename(source)
                                st.markdown(f"**📄 출처 (PDF 파일):** `{file_name}`")
                                if "page" in metadata:
                                    st.caption(f"페이지: {metadata['page']}p")
                            
                            st.markdown("**본문 내용 요약:**")
                            # 검색된 청크의 텍스트가 너무 길면 UI가 지저분해지므로 400자로 제한
                            content_preview = doc.get("content", "")
                            st.info(f"{content_preview[:400]}..." if len(content_preview) > 400 else content_preview)
                                
        except Exception as e:
            st.warning(f"관련 문서를 불러오는 데 실패했습니다: {str(e)}")

elif menu == "📊 리포트 생성":
    st.title("📋 이커머스 & 데이터 테크 브리핑")
    st.markdown("최신 마케팅/데이터 트렌드를 조사하고 PDF 리포트로 다운로드합니다.")
    
    # 리포트 주제 입력
    topic_input = st.text_input(
        "리포트 주제를 구체적으로 입력하세요:", 
        value="현재 이커머스 및 GA4 데이터 분석 분야의 최신 브리핑 리포트를 생성해줘."
    )
    
    if st.button("🔄 에이전트 가동 및 리포트 생성", type="primary"):
        with st.spinner("에이전트가 웹 리서치 및 문서 파싱을 통해 리포트를 작성 중입니다. (약 30초~1분 소요)"):
            try:
                # 백엔드에 리포트 생성 요청
                res = requests.post(f"{API_URL}/api/report", json={"topic": topic_input})
                
                if res.status_code == 200:
                    data = res.json()
                    summary_markdown = data.get("summary", "내용이 없습니다.")
                    
                    st.success("✅ 리포트가 성공적으로 생성되었습니다!")
                    
                    # 화면에 마크다운 결과 렌더링
                    with st.container(border=True):
                        st.markdown(summary_markdown)
                        
                    # PDF 다운로드 버튼 활성화 (백엔드에서 파일 바이트 가져오기)
                    pdf_res = requests.get(f"{API_URL}/api/download-report")
                    if pdf_res.status_code == 200:
                        st.download_button(
                            label="📥 PDF 리포트 다운로드",
                            data=pdf_res.content,
                            file_name="Commerce_Trend_Report.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    else:
                        st.error("PDF 파일을 가져오는 데 실패했습니다.")
                else:
                    st.error(f"서버 에러: {res.text}")
            except requests.exceptions.ConnectionError:
                st.error("FastAPI 백엔드 서버가 켜져 있는지 확인해주세요. (포트 8000)")
      
      
# # 사용 방법 안내
# with st.sidebar.expander("ℹ️ 사용 방법"):
#     st.markdown("""
#     **PDF 업로드 및 처리**
#     - 사이드바에서 PDF 파일을 선택합니다
#     - 업로드 및 처리 버튼을 클릭합니다

#     **질문하기**
#     - 메인 화면 하단의 입력창에 질문을 입력합니다
#     - AI가 문서를 기반으로 답변을 생성합니다

#     **검색된 문서 확인**
#     - 답변 하단에 관련 문서 3개가 표시됩니다
#     - 각 문서를 클릭하여 상세 내용을 확인할 수 있습니다
#     """)