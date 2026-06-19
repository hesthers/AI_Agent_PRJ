# 🚀 E-Commerce Growth Analytics & Marketing RAG Agent

이 프로젝트는 **GA4(Google Analytics 4) 웹/앱 로그 데이터, 마케팅 캠페인 성과 데이터, 그리고 BigQuery 데이터 마트 적재 가이드**를 통합하여, 이커머스 마케터와 데이터 분석가가 복잡한 데이터 인프라와 지표를 쉽게 조회하고 인사이트를 얻을 수 있도록 돕는 **AI 에이전트 시스템**입니다.

---

## 📝 1. 프로젝트 개요

### 🤖 Project A — RAG 질의응답 봇

- **서비스명**: 커머스그로스 가이드 (CommerceGrowth-QA)
- **한 줄 설명**: GA4 이벤트 태깅, 마케팅 캠페인 지표, 빅쿼리 데이터 마트 생성 기준을 이커머스 마케터 및 데이터 분석가에게 실시간 답변하는 RAG 기반 챗봇
- **도메인**: 이커머스 마케팅, 그로스 해킹 및 데이터 엔지니어링 (Marketing & Data Analytics)
- **사용할 문서**: GA4 가이드라인, 마케팅 캠페인 성과 분석 가이드 PDF, [Google Cloud BigQuery 공식 문서](https://cloud.google.com/bigquery/docs) (GA4 export 스키마 레퍼런스 포함)
- **핵심 질문 예시 3가지**:
  1. "GA4에서 수집된 `purchase` 이벤트 데이터를 빅쿼리 마트에 적재할 때, 맞춤 매개변수(Custom Parameters)를 언네스트(Unnest)하는 SQL 표준 쿼리는 무엇인가요?"
  2. "신규 런칭한 퍼포먼스 마케팅 캠페인의 ROAS와 코호트 리텐션을 연계하여 마트 테이블을 설계하는 기준이 어떻게 되나요?"
  3. "GA4 데이터의 결측치나 중복 데이터가 발견되었을 때, 마트 적재 전 단계에서 수행해야 할 정제 프로토콜은 무엇인가요?"

### 📊 Project B — 자료 수집 → 요약 → 발송

- **서비스명**: 그로스 마케팅 & 테크 트렌드 브리핑 (Growth Tech Briefing)
- **한 줄 설명**: 국내외 이커머스 마케팅 트렌드, GA4 업데이트 소식, 빅쿼리 기반 데이터 분석 아키텍처 사례를 자동 수집하여 요약 리포트를 발송하는 서비스
- **수집 분류**: 산업 / 해외 / 시장 (글로스 마케팅 및 데이터 테크 동향)
- **보고서 형식**: 핵심 이슈 3개 + 커머스 분석 도입을 위한 Growth Action Point (Bullet 형태)
- **수신자**: 본인 이메일 및 사내 그로스 마케팅/데이터 팀원

---

## 🏗️ 2. 시스템 구조 (Architecture)

프론트엔드(Streamlit)와 백엔드(FastAPI)를 분리하고 비즈니스 로직(LangChain)을 모듈화

- 문서 업로드(GA4/마케팅/BQ Docs) ──> FAISS 벡터 저장 ──> 질문 입력 ──> 유사 청크 검색 ──> GA4 & BQ Ref 참조 ──> LLM 답변 생성

### 📁 디렉토리 구조

```text
project1/
├── langchain_service.py  # RAG 핵심 로직 (GA4, 캠페인, 빅쿼리 지식을 처리하는 LangChainService)
├── main.py               # FastAPI 서버 (Port: 8000) - 마케팅 봇 API 엔드포인트
├── app.py                # Streamlit UI (Port: 8501) - 마케터/분석가용 웹 인터페이스
├── requirements.txt      # 의존성 패키지 목록 (langchain, fastapi, streamlit, faiss-cpu 등)
├── pdfs/                 # GA4 가이드, 캠페인 전략 가이드북 가이드 샘플 PDF 저장소
└── faiss_db/             # 벡터 저장소 (실행 시 로컬에 자동 생성되는 임베딩 DB)
```

## 🚀 3. 실행 방법 (How to Run)

1. 환경 변수 설정
   프로젝트 루트 디렉토리에 .env 파일을 생성하고 필요한 API 키를 설정합니다.
   OPENAI_API_KEY=your_openai_api_key_here

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

- UI/UX Framework: Streamlit (인터랙티브 분석 웹 UI)

- Backend API: FastAPI (비동기 처리 및 엔드포인트 구축)

- LLM Orchestration: LangChain (LangChainService 클래스 기반 구조화)

- Vector DB: FAISS (Facebook AI Similarity Search)

- Data Sources: Google Analytics 4 (GA4), Google Cloud BigQuery
