import os
import markdown
import pdfkit

def generate_pdf(text: str, file_path: str) -> bool:
    """
    LLM이 생성한 마크다운 텍스트를 HTML로 변환한 뒤 PDF로 저장하는 함수
    """
    try:
        # 1. 마크다운을 HTML로 변환 (표, 코드블록 등 확장 기능 활성화)
        html_body = markdown.markdown(text, extensions=['tables', 'fenced_code'])

        # 2. 한글 깨짐 방지 및 깔끔한 보고서 스타일링을 위한 CSS 래핑
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    padding: 2em;
                }}
                h1, h2, h3 {{ 
                    color: #2c3e50; 
                    border-bottom: 1px solid #eee; 
                    padding-bottom: 8px; 
                    margin-top: 24px;
                }}
                pre {{ 
                    background-color: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px; 
                    overflow-x: auto; 
                }}
                code {{ font-family: Consolas, monospace; }}
                table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin-bottom: 20px; 
                }}
                th, td {{ 
                    border: 1px solid #dee2e6; 
                    padding: 12px; 
                    text-align: left; 
                }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
            </style>
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """

        # 3. PDF 여백 및 인코딩 옵션 설정
        options = {
            'encoding': "UTF-8",
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm'
        }

        # 4. 저장할 디렉토리가 없으면 자동 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 5. HTML을 PDF로 최종 변환 및 저장
        pdfkit.from_string(html_content, file_path, options=options)
        return True

    except Exception as e:
        print(f"[PDF Error] PDF 생성 중 오류 발생: {str(e)}")
        return False