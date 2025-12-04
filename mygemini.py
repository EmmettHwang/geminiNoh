import sys
import os
import pymysql
from datetime import datetime
import html
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6 import uic
from dotenv import load_dotenv 

# Google GenAI 라이브러리 임포트
try:
    # 'google-genai' 라이브러리 시도
    from google import genai
except ImportError:
    print("🚨 오류: 'google-genai' 라이브러리를 찾을 수 없습니다.")
    print("설치하려면 터미널에서 'pip install google-genai' 명령을 실행하세요.")
    sys.exit(1)

# UI 파일 로드
try:
    form_class = uic.loadUiType("mygemini.ui")[0]
except Exception as e:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "UI 파일 오류", f"UI 파일을 찾을 수 없습니다.\n\n에러 내용: {e}")
    sys.exit()

class GeminiApp(QMainWindow, form_class):
    
    def __init__(self):
        super().__init__()        
        self.setupUi(self)
        
        # [수정] QTextBrowser 설정 추가
        # QTextBrowser는 기본적으로 읽기 전용입니다.
        # 링크가 포함된 답변이 올 경우 브라우저로 열리게 설정합니다.
        try:
            self.answerDisplay.setOpenExternalLinks(True)
        except AttributeError:
            pass # UI 파일에 해당 위젯이 없으면 무시

        # --- [수정된 부분] API 키 설정 (NameError 해결을 위해 함수 내부로 이동) ---
        # 1. .env 파일에서 환경 변수를 불러옵니다.
        load_dotenv()
        
        # 2. 환경 변수에서 GEMINI_API_KEY 값을 읽어옵니다
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        
        if not api_key: 
            # API 키가 설정되지 않았을 경우 경고 표시
            QMessageBox.critical(
                self, 
                "API 키 오류", 
                "⚠️ API 키가 설정되지 않았습니다.\n"
                ".env 파일에 GEMINI_API_KEY가 올바르게 있는지 확인해주세요."
            )
            # 클라이언트를 None으로 둡니다.
        else:
            try:
                # 환경 변수에서 API 키를 사용하여 클라이언트 초기화
                # 명시적으로 api_key를 전달하는 것이 안전합니다.
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                # API 초기화 실패 시 처리
                error_msg = f"Gemini API 클라이언트 초기화 오류: {e}"
                QMessageBox.critical(self, "API 오류", "Gemini API 클라이언트 초기화에 실패했습니다.\n\n" + error_msg)
                print(error_msg)
                self.client = None
            
        # 4. 버튼 클릭 시그널 연결
        self.btnSent.clicked.connect(self.ask_gemini) 
        self.btnSent.setVisible(False)
        # Enter 키 입력 시에도 작동하도록 연결
        self.lineEditMyQuestion.returnPressed.connect(self.ask_gemini)
        
        # 검색 버튼 연결 (UI에 btnSearch가 있다면 연결)
        try:
            self.btnSearch.clicked.connect(self.search_mysql)
        except Exception:
            pass

    def ask_gemini(self): 
        # API 클라이언트 초기화 실패 시 처리
        if not self.client:
            self.answerDisplay.setText("Gemini API 클라이언트가 초기화되지 않았습니다. API 키를 확인하세요. [제미나이nh]")
            return      

        question = self.lineEditMyQuestion.text().strip()

        if not question:
            self.answerDisplay.setText("질문을 입력해주세요. [제미나이nh]")
            return
        
        # 질문 입력창 비우기
        self.lineEditMyQuestion.clear()
        
        # 먼저 DB에서 검색 시도
        if self.search_mysql(search_text=question) == True:
            return  # 검색 결과가 있으면 새 질문 처리 중단


        # 응답 대기 메시지 표시 (HTML)
        waiting_html = f"<div>➡️ 질문: <b>{html.escape(question)}</b></div>" \
                   f"<div style='color:gray;'>Gemini가 응답을 생성하는 중입니다... 잠시만 기다려주세요.</div>"
        self.answerDisplay.setHtml(waiting_html)
        QApplication.processEvents() # UI 갱신 (반드시 필요)

        try:
            # API 호출
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=question
            )

            # 응답 표시 및 [제미나이nh] 추가
            esc_question = html.escape(question).replace('\n', '<br>')
            esc_response = html.escape(response.text).replace('\n', '<br>')
            html_content = (
                f"<div>➡️ 질문: <b>{esc_question}</b></div>"
                f"<hr>"
                f"<div style='color:green; white-space:pre-wrap;'>{esc_response}</div>"
                f"<div style='color:gray; margin-top:8px;'>[제미나이nh]</div>"
            )
            self.answerDisplay.setHtml(html_content)
            
            # (답변 표시 후)
            self.save_to_mysql(question, response.text)
            
        except Exception as e:
            # API 호출 중 예외 처리
            error_message = f"API 호출 중 오류 발생: {e}"
            print(error_message)
            err_html = f"<div>➡️ 질문: <b>{html.escape(question)}</b></div>" \
                       f"<div style='color:red;'>🚨 오류: {html.escape(str(error_message))}</div>" \
                       f"<div style='color:gray; margin-top:8px;'>[제미나이nh]</div>"
            self.answerDisplay.setHtml(err_html)

    def save_to_mysql(self, question, answer):
        conn = None
        conn2 = None
        try:
            # 1. 현재 시간 구하기
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 2. DB 연결
            conn = pymysql.connect( 
                host='bitnmeta2.synology.me',
                user='iyrc',
                passwd='Dodan1004!',
                db='gemini_ai',
                charset='utf8',
                port=3307,  
                cursorclass=pymysql.cursors.DictCursor
            )

            with conn.cursor() as cursor:
                sql = "INSERT INTO chat_history (question, answer, create_at) VALUES (%s, %s, %s)"
                cursor.execute(sql, (question, answer, current_time))
            
            conn.commit()
            print(f"✅ MySQL 저장 성공: {current_time}")
        
        except Exception as e:
            # MySQL Data too long for column -> 에러코드 1406 처리
            err_str = str(e)
            print(f"❌ 데이터를 요약하고 있습니다.: {err_str}")

            is_data_too_long = False
            try:
                if hasattr(e, 'args') and e.args:
                    if isinstance(e.args[0], int) and e.args[0] == 1406:
                        is_data_too_long = True
                if '1406' in err_str or 'Data too long' in err_str:
                    is_data_too_long = True
            except Exception:
                is_data_too_long = False

            if is_data_too_long:
                # 기존 연결 안전하게 종료
                if conn:
                    try: conn.close()
                    except: pass
                    conn = None

                # 요약 시도
                summarized = None
                try:
                    if self.client:
                        prompt = ("아래 텍스트를 한국어로 500자 이내로 요약해 주세요.\n\n" + str(answer))
                        summ_resp = self.client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        summarized = summ_resp.text.strip()
                except Exception as se:
                    print(f"요약 시도 중 오류: {se}")

                if not summarized:
                    summarized = str(answer)[:500]
                if len(summarized) > 500:
                    summarized = summarized[:500]

                # 재시도: 새 연결로 안전하게 INSERT
                try:
                    conn2 = pymysql.connect(
                        host='bitnmeta2.synology.me',
                        user='iyrc',
                        passwd='Dodan1004!',
                        db='gemini_ai',
                        charset='utf8',
                        port=3307,
                        cursorclass=pymysql.cursors.DictCursor
                    )
                    with conn2.cursor() as cursor2:
                        sql = "INSERT INTO chat_history (question, answer, create_at) VALUES (%s, %s, %s)"
                        cursor2.execute(sql, (question, summarized, current_time))
                    conn2.commit()
                    print(f"✅ MySQL 요약 저장 성공: {current_time}")
                    
                    # 사용자에게 알림
                    notice_html = f"<div style='color:gray;'>원문이 길어 요약(500자 이내)으로 저장했습니다.</div>"
                    try:
                        prev_html = self.answerDisplay.toHtml()
                        self.answerDisplay.setHtml(prev_html + notice_html)
                    except Exception:
                        self.answerDisplay.append("원문이 길어 요약(500자 이내)으로 저장했습니다.")
                        
                except Exception as re:
                    print(f"❌ 요약 재저장 실패: {re}")
        
        finally:
            if conn:
                try: conn.close()
                except: pass
            if conn2:
                try: conn2.close()
                except: pass

    def search_mysql(self, search_text=None):
        """
        DB 검색 함수.
        search_text 인자가 있으면 그것으로 검색하고,
        없으면 입력창(lineEditMyQuestion)의 텍스트를 가져와서 검색합니다.
        """
        if search_text is not None:
            keyword = search_text.strip()
        else:
            keyword = self.lineEditMyQuestion.text().strip()

        try:
            conn = pymysql.connect(
                host='bitnmeta2.synology.me',
                user='iyrc',
                passwd='Dodan1004!',
                db='gemini_ai',
                charset='utf8',
                port=3307,
                cursorclass=pymysql.cursors.DictCursor
            )

            with conn.cursor() as cursor:
                if keyword:
                    sql = ("SELECT question, answer, create_at "
                           "FROM chat_history "
                           "WHERE question LIKE %s OR answer LIKE %s "
                           "ORDER BY create_at DESC LIMIT 100")
                    like_kw = f"%{keyword}%"
                    cursor.execute(sql, (like_kw, like_kw))
                else:
                    # 검색어가 없으면 작동하지 않도록 수정하거나, 최근 대화를 보여주도록 설정
                    # 여기서는 검색어가 없으면 False 반환하여 Gemini에게 질문하도록 함
                    return False

                rows = cursor.fetchall()

            if not rows:
                # 검색 결과가 없으면 Gemini에게 질문하기 위해 False 반환
                return False

            # 결과 포맷팅
            lines = []
            lines.append(f"<div style='color:blue; font-weight:bold;'>[DB 검색 결과: '{keyword}']</div><hr>")
            
            for i, row in enumerate(rows, start=1):
                created = row.get('create_at') or row.get('created_at') or ''
                q = row.get('question', '')
                a = row.get('answer', '')
                esc_q = html.escape(str(q)).replace('\n', '<br>')
                esc_a = html.escape(str(a)).replace('\n', '<br>')
                block = (
                    f"<div style='color:blue; margin-bottom:15px;'>"
                    f"<div><b>{i}. [{html.escape(str(created))}]</b></div>"
                    f"<div><b>Q:</b> {esc_q}</div>"
                    f"<div><b>A:</b> {esc_a}</div>"
                    f"</div>"
                )
                lines.append(block)

            result_html = "".join(lines)
            self.answerDisplay.setHtml(result_html)
            return True

        except Exception as e:
            err = f"DB 검색 중 오류 발생: {e}"
            print(err)
            self.answerDisplay.setText(err)
            return False

        finally:
            if 'conn' in locals() and conn:
                conn.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeminiApp()
    window.show()
    sys.exit(app.exec())