# 🚀 E-Commerce Growth Analytics & Marketing Agentic RAG System

이 프로젝트는 **GA4(Google Analytics 4) 로그 데이터, 마케팅 캠페인 성과 지표, BigQuery 데이터 마트 적재 가이드**를 통합하여, 이커머스 마케터와 데이터 분석가가 복잡한 데이터 인프라와 그로스 지표를 조회하고 인사이트를 얻을 수 있도록 돕는 **LangChain & LangGraph 기반 고급 에이전트 시스템**입니다.

---

## 📝 1. 프로젝트 개요

### 🤖 Project A — Agentic RAG 질의응답 봇
* **서비스명**: 커머스그로스 가이드 (CommerceGrowth-QA)
* **한 줄 설명**: GA4 이벤트 태깅, 마케팅 캠페인 지표, 빅쿼리 데이터 마트 생성 기준을 이커머스 마케터 및 데이터 분석가에게 실시간 답변하는 LangGraph 기반의 복합 추론 QA 봇
* **도메인**: 이커머스 마케팅, 그로스 해킹 및 데이터 엔지니어링 (Marketing & Data Analytics)
* **사용할 문서**: GA4 가이드라인, 마케팅 캠페인 성과 분석 가이드 PDF, [Google Cloud BigQuery 공식 문서](https://cloud.google.com/bigquery/docs) (GA4 export 스키마 레퍼런스 포함)
* **핵심 질문 예시 3가지**:
  1. "GA4에서 수집된 `purchase` 이벤트 데이터를 빅쿼리 마트에 적재할 때, 맞춤 매개변수(Custom Parameters)를 언네스트(Unnest)하는 SQL 표준 쿼리는 무엇인가요?"
  2. "신규 런칭한 퍼포먼스 마케팅 캠페인의 ROAS와 코호트 리텐션을 연계하여 마트 테이블을 설계하는 기준이 어떻게 되나요?"
  3. "GA4 데이터의 결측치나 중복 데이터가 발견되었을 때, 마트 적재 전 단계에서 수행해야 할 정제 프로토콜은 무엇인가요?"

### 📊 Project B — 자료 수집 → 요약 → 리포트 다운로드 및 발송 (선택형)
* **서비스명**: 그로스 마케팅 & 테크 트렌드 브리핑 (Growth Tech Briefing)
* **한 줄 설명**: 국내외 이커머스 마케팅 트렌드, GA4 업데이트 소식, 빅쿼리 기반 데이터 분석 아키텍처 사례를 LangGraph 에이전트가 자동 수집·검증 및 요약하여 **PDF 리포트로 빌드하거나 이메일로 발송**하는 서비스
* **수집 분류**: 산업 / 해외 / 시장 (그로스 마케팅 및 데이터 테크 동향)
* **보고서 형식**: 핵심 이슈 3개 + 커머스 분석 도입을 위한 Growth Action Point (Bullet 형태)
* **산출물 인도 방식 (선택 가능)**:
  * 📥 **Streamlit 웹 UI에서 PDF 파일로 즉시 다운로드**
  * 📧 **지정된 수신자(본인 및 팀원) 이메일로 자동 발송**

---

## 🏗️ 2. 시스템 구조 (Architecture)
### 🔄 LangGraph 에이전트 워크플로우 개요
백엔드의 비즈니스 레이어를 **LangChain 독립 서비스**와 워크플로우 상태 제어를 담당하는 **LangGraph Agent Engine**으로 세분화

[사용자 질문 / 태스크]

│

▼

┌───────────────┐

│ Router Agent  │ ──(질의응답 상태인 경우)──> [LangChain RAG / Vector Search] ──> [문서 품질 검증 (Grade)] ──┐

└───────────────┘                                                                                   │ (부족하면 재검색)

│                                                                                                   ▼

(리포트 요청인 경우)                                                                             [최종 답변 생성]

│                                                                                                   │

▼                                                                                                   ▼

[자료 수집 노드] ──> [LangChain LLM 요약 노드] ──> [PDF Generator 모듈] ───────────────────────────> [결과 반환]


### 📁 디렉토리 구조
```text
project1/
├── langgraph_agent.py    # LangGraph 워크플로우 상태(State) 정의, 노드 및 엣지 제어 가이드 🛠️ (New)
├── langchain_service.py  # 개별 노드에서 실행될 RAG 및 요약 핵심 비즈니스 로직 (LangChainService)
├── pdf_generator.py      # 수집/요약 데이터 기반 PDF 리포트 생성 모듈 
├── main.py               # FastAPI 서버 (Port: 8000) - LangGraph 호출 및 이메일 발송 API
├── app.py                # Streamlit UI (Port: 8501) - 챗봇 웹 인터페이스 및 리포트 다운로드 구현
├── requirements.txt      # 의존성 패키지 목록 (langgraph, langchain, fastapi, streamlit 등)
├── pdfs/                 # GA4 및 빅쿼리 참조 문서 저장소
└── faiss_db/             # 벡터 저장소 (실행 시 로컬에 자동 생성되는 임베딩 DB)
```

### 🚀 3. 실행 방법 (How to Run)

1. 환경 변수 설정

프로젝트 루트 디렉토리에 .env 파일을 생성하고 필요한 API 키를 설정합니다.
```text
OPENAI_API_KEY=your_openai_api_key_here
```

2. 패키지 설치

```Bash
pip install -r requirements.txt
```

3. 백엔드 API 서버 실행 (FastAPI)

```Bash
uvicorn main:app --reload --port 8000
```

4. 프론트엔드 대시보드 UI 실행 (Streamlit)

```Bash
streamlit run app.py --server.port 8501
```

## 🛠️ 4. 주요 기술 스택 (Tech Stack)
- Orchestration & State: LangGraph (순환 그래프 기반 다중 에이전트 상태 제어)

- LLM Components: LangChain (LangChainService 모듈 기반 LCEL 체인 및 툴 정의)

- UI/UX Framework: Streamlit (인터랙티브 웹 UI 및 파일 다운로드 인터페이스)

- Backend API: FastAPI (비동기 에이전트 호출 엔드포인트)

- Vector DB: FAISS (GA4/캠페인 가이드 문서 임베딩 검색 엔진)

- Search API: Tavily (실시간 웹 트렌드 리서치 및 본문 추출)

- PDF Engine: ReportLab / pdfkit / WeasyPrint


## 📅 5. 개발 일정 및 업데이트 이력 (Changelog)
> 2026/06/19

- 프로젝트 초기 기획 및 요구사항 정의안 작성 (Project A & B 기획)

- 에이전트 아키텍처 및 디렉토리 구조 설계

> 2026/06/20

- 백엔드 핵심 비즈니스 로직 파일(3종) 구현 완료

- langchain_service.py: FAISS 벡터 DB 구축 및 RAG 검색 체인 구현

- langgraph_service.py: LangGraph 기반 에이전트 라우팅 및 외부 툴 호출(Tavily API, PDF/Web 파싱) 로직 구현

- pdf_generator.py: LLM 요약 결과를 지정된 스타일의 PDF 리포트로 변환하는 모듈 구현


## License
이 프로젝트는 **CC BY-NC 4.0** 라이선스가 적용되어 있습니다.
개인적인 학습 및 비영리 목적의 코드 활용과 수정은 자유롭게 가능하지만, **상업적인 용도로의 사용은 엄격히 금지**됩니다. 자세한 내용은 `LICENSE` 파일을 참고해 주세요.