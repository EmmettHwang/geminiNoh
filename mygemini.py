import sys
import os
import pymysql
from datetime import datetime
import html
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6 import uic
from dotenv import load_dotenv 
from konlpy.tag import Kkma
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve   # 애니메이션용
from PyQt6.QtCore import QPoint # QPoint 임포트 추가

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
        
        # label_2 원래 위치 저장
        self.label2_origin = self.label_2.pos()

        # 좌우 흔들기 애니메이션
        self.label2_anim = QPropertyAnimation(self.label_2, b"pos")
        self.label2_anim.setDuration(600)   # 0.6초 왕복
        self.label2_anim.setLoopCount(-1)   # 무한 반복
        self.label2_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 흔들림 범위 설정 (좌우 10px)
        x, y = self.label2_origin.x(), self.label2_origin.y()
        self.label2_anim.setStartValue(self.label2_origin)
        self.label2_anim.setKeyValueAt(0.5, self.label2_origin + QPoint(10, 0))
        self.label2_anim.setEndValue(self.label2_origin)
    
    def start_label2_animation(self):
        self.label2_anim.start()

    def stop_label2_animation(self):
        self.label2_anim.stop()
        self.label_2.move(self.label2_origin)   # 위치 원위치 복귀

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
        self.start_label2_animation()  # 애니메이션 시작
        if self.search_mysql(search_text=question) == True:
            self.stop_label2_animation()  # 애니메이션 중지 
            return  # 검색 결과가 있으면 새 질문 처리 중단


        # 응답 대기 메시지 표시 (HTML)
        waiting_html = f"<div>➡️ 질문: <b>{html.escape(question)}</b></div>" \
                   f"<div style='color:gray;'>Gemini가 응답을 생성하는 중입니다... 잠시만 기다려주세요.</div>"
        self.answerDisplay.setPlainText("")             # 먼저 지우고
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
                f"<div style='color:#1E90FF; font-weight:bold;'>[Gemini 생성 응답]</div>"                
                f"<div>➡️ 질문: <b><span style='color:red;'>{esc_question}</span></b></div>"
                f"<hr>"
                f"<div style='color:green; white-space:pre-wrap;'>{esc_response}</div>"
                f"<div style='color:gray; margin-top:8px;'>[제미나이nh]</div>"
            )

            self.answerDisplay.setPlainText("")                   # 먼저 지우고
            self.answerDisplay.setHtml(html_content )   # 새 결과 출력
            
            # (답변 표시 후)
            self.save_to_mysql(question, response.text)
            
        except Exception as e:
            # API 호출 중 예외 처리
            error_message = f"API 호출 중 오류 발생: {e}"
            print(error_message)
            err_html = f"<div>➡️ 질문: <b>{html.escape(question)}</b></div>" \
                       f"<div style='color:red;'>🚨 오류: {html.escape(str(error_message))}</div>" \
                       f"<div style='color:gray; margin-top:8px;'>[by geminiNoh]</div>"
            self.answerDisplay.setPlainText("")            # 먼저 지우고
            self.answerDisplay.setHtml(err_html)
        finally:
            self.stop_label2_animation()  # 애니메이션 중지

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
                        prev_html = self.answerDisplay.toHtml() # 기존 내용 가져오기가 필요 없을땐 생략 가능
                        self.answerDisplay.setPlainText("")            # 먼저 지우고
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
        DB 검색 함수(명사 추출 기반 다중 검색).
        - search_text가 있으면 그것 기반으로 수행.
        - 없으면 lineEditMyQuestion 내용으로 검색.
        - konlpy를 이용해 명사를 추출하고, 각 명사를 LIKE 검색 조건으로 사용한다.
        """
        if search_text is not None:
            text = search_text.strip()
        else:
            text = self.lineEditMyQuestion.text().strip()

        # ---------------------------
        # 1) konlpy로 명사 추출
        # ---------------------------
        kkma = Kkma()
        nouns = kkma.nouns(text)

        # 명사가 없으면 원래 단일 검색어로 사용
        if not nouns:
            nouns = [text]

        # 너무 짧은(1자) 명사는 보통 의미가 약하므로 필터링(원하면 제거 가능)
        nouns = [n for n in nouns if len(n) > 1]




        # 명사가 하나도 안 남으면 전체 문장을 사용
        if not nouns:
            nouns = [text]

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
                if nouns:
                    # --------------------------------------------
                    # 2) 명사들로 다중 LIKE 조건 생성
                    # --------------------------------------------
                    # question LIKE '%키워드%' OR answer LIKE '%키워드%'
                    conditions = []
                    params = []

                    for n in nouns:
                        like_n = f"%{n}%"
                        conditions.append("(question LIKE %s OR answer LIKE %s)")
                        params.extend([like_n, like_n])

                    where_clause = " OR ".join(conditions)

                    sql = (
                        "SELECT * "
                        "FROM chat_history "
                        f"WHERE {where_clause} "
                        
                    )

                    cursor.execute(sql, params)

                else:
                    return False

            rows = cursor.fetchall()
            if not rows:
                return False

            # --- 2차 필터: 명사 80% 이상 겹치는 row만 선별 ---
            kkma = Kkma()
            filtered_rows = []

            for row in rows:
                q_text = str(row.get('question', ''))
                a_text = str(row.get('answer', ''))

                row_q_n = kkma.nouns(q_text)
                row_a_n = kkma.nouns(a_text)
                row_nouns = set([n for n in row_q_n + row_a_n if len(n) > 1])

                # 교집합 개수
                overlap = len(row_nouns.intersection(set(nouns)))

                # *** 추가: 겹침 비율 계산 ***
                if len(nouns) > 0:
                    overlap_ratio = overlap / len(nouns)
                else:
                    overlap_ratio = 0

                # *** 조건: 겹침 비율이 0.8 이상일 때만 인정 ***
                if overlap_ratio >= 0.8:
                    filtered_rows.append(row)

            
            # 필터 후 결과 없으면 Gemini 호출로 이동
            if not filtered_rows:
                return False

            # 결과 표시
            lines = []
            lines.append(
                f"<div style='color:#8A2BE2; font-weight:bold;'>[DB 검색 응답]</div>"
                f"<div style='color:gray;'>검색어: {', '.join(nouns)}</div><hr>"
            )

            for i, row in enumerate(filtered_rows, start=1):
                print("created_at raw value:", row['created_at'], type(row['created_at']))
                created = row.get('created_at', '')              
                # created_at이 None이거나 빈 문자열인 경우 처리
                if created is None or created == '':
                    created = "저장된 날짜가 없어서 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                q = row.get('question', '')
                a = row.get('answer', '')
                esc_q = html.escape(str(q)).replace('\n', '<br>')
                esc_a = html.escape(str(a)).replace('\n', '<br>')

                block = (
                    f"<div style='color:blue; margin-bottom:15px;'>"
                    f"<div><b>{i}. [{html.escape(str(created))}]</b></div>"
                    f"<div><b>Q:</b> <span style='color:red;'>{esc_q}</span></div>"
                    f"<div><b>A:</b> {esc_a}</div>"
                    f"</div>"
                )
                lines.append(block)
            result_html = "".join(lines)
            self.answerDisplay.setPlainText("")            # 먼저 지우고
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