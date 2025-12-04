# 내가 수정한 내용이 있다. 
# 이것은 다른 친구가 내용을 수정해서 push 한것이라고 가정하고 
import sys
import os
''' pymysql은 MySQL과 연동하기 위한 라이브러리입니다. 설치가 필요할 수 있습니다.
터미널에서 'pip install pymysql' 명령어'
를 실행하여 설치하세요. '''
import pymysql
''' datetime은 날짜와 시간을 다루기 위한 표준 라이브러리입니다. 설치가 필요하지 않습니다. '''
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, 
    QWidget, 
    QLineEdit, 
    QTextEdit, 
    QPushButton,
    QVBoxLayout,  # 수직 레이아웃 관리
    QHBoxLayout,  # 수평 레이아웃 관리
    QMessageBox,  # 메시지 박스 사용 (sys.exit 대신 권장)
    QLabel
)
from PyQt6.QtCore import Qt
# Google GenAI 라이브러리 임포트
try:
    # 'google-genai' 대신 'google-generativeai'를 사용하는 경우도 있으므로
    # 최신 라이브러리인 'google-genai'를 시도합니다.
    from google import genai
except ImportError:
    # 만약 'google' 모듈이 없다면 설치 안내 후 종료
    print("🚨 오류: 'google-genai' 라이브러리를 찾을 수 없습니다.")
    print("설치하려면 터미널에서 'pip install google-genai' 명령을 실행하세요.")
    sys.exit(1)

# --- ⚠️ 중요: Gemini API 키 설정 ⚠️ ---
# 사용자가 제공한 API 키를 환경 변수에 설정합니다.
# 실제 키를 여기에 넣어주세요.
os.environ["GEMINI_API_KEY"] = "AIzaSyDFYx3mr8dY8HwRMaPD2egzjVso7mkgops"
# ------------------------------------
# [추가된 부분 1] .env 파일을 읽기 위한 라이브러리
from dotenv import load_dotenv 

# Google GenAI 라이브러리 임포트
try:
    from google import genai
except ImportError:
    print("🚨 오류: 'google-genai' 라이브러리를 찾을 수 없습니다.")
    sys.exit(1)

# --- [수정된 부분] API 키 설정 ---
# 1. .env 파일에서 환경 변수를 불러옵니다.
load_dotenv()
# 2. 환경 변수에서 GEMINI_API_KEY 값을 읽어옵니다
api_key = os.getenv("GEMINI_API_KEY")
# ------------------------------------
class GeminiApp(QWidget):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini Q&A 챗봇")
        self.setGeometry(100, 100, 800, 600)  # 창 크기 설정
        
        # 1. Gemini 클라이언트 초기화 및 API 키 확인
        self.client = None
        
        if not api_key or api_key == "YOUR_ACTUAL_GEMINI_API_KEY_HERE":
            # API 키가 설정되지 않았거나 더미 값일 경우 경고 표시
            QMessageBox.critical(
                self, 
                "API 키 오류", 
                "⚠️ API 키가 설정되지 않았거나 유효하지 않은 더미 값입니다.\n"
                "코드 상단 os.environ[\"GEMINI_API_KEY\"] = \"...\" 부분에 실제 키를 입력해야 합니다."
            )
            # 클라이언트를 None으로 두어 API 호출을 방지합니다.
        else:
            try:
                # 환경 변수에서 API 키를 자동으로 로드 시도
                self.client = genai.Client()
            except Exception as e:
                # API 초기화 실패 시 클라이언트를 None으로 설정하고 사용자에게 오류 메시지 표시
                error_msg = f"Gemini API 클라이언트 초기화 오류: {e}"
                QMessageBox.critical(self, "API 오류", "Gemini API 클라이언트 초기화에 실패했습니다.\n\n" + error_msg)
                print(error_msg)
                self.client = None
            
        # 2. UI 위젯 생성 (UI 파일을 대체)
        self.answerDisplay = QTextEdit()  # 응답 출력 (QTextEdit)
        self.answerDisplay.setReadOnly(True) 
        self.answerDisplay.setText("질문을 입력하고 '전송' 버튼을 누르세요. (Gemini 2.5 Flash 사용)\n\n[제미나이nh]")
        
        self.lineEditMyQuestion = QLineEdit() # 질문 입력 (QLineEdit)
        self.lineEditMyQuestion.setPlaceholderText("여기에 질문을 입력하세요...")
        
        self.btnSent = QPushButton("전송 (Sent)") # 전송 버튼 (QPushButton)
        self.btnSent.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")

        # 3. 레이아웃 설정
        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Gemini 응답:"))
        main_layout.addWidget(self.answerDisplay)
        main_layout.addWidget(QLabel("나의 질문:"))
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.lineEditMyQuestion)
        input_layout.addWidget(self.btnSent)
        
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

        # 4. 버튼 클릭 시그널 연결
        self.btnSent.clicked.connect(self.ask_gemini) 
        # Enter 키 입력 시에도 작동하도록 연결
        self.lineEditMyQuestion.returnPressed.connect(self.ask_gemini)

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

        # 응답 대기 메시지 표시
        self.answerDisplay.setText(f"➡️ 질문: {question}\n\nGemini가 응답을 생성하는 중입니다... 잠시만 기다려주세요.")
        QApplication.processEvents() # UI 갱신 (반드시 필요)

        try:
            # API 호출
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=question
            )

            # 응답 표시 및 [제미나이nh] 추가
            # 이전 질문을 포함하여 응답을 표시
            full_response_text = f"➡️ 질문: {question}\n\n" + response.text + "\n\n[제미나이nh]"
            self.answerDisplay.setText(full_response_text)
            
            # (답변 표시 후)
            self.save_to_mysql(question, response.text)
            
        except Exception as e:
            # API 호출 중 예외 처리
            error_message = f"API 호출 중 오류 발생: {e}"
            print(error_message)
            self.answerDisplay.setText(f"➡️ 질문: {question}\n\n🚨 오류: {error_message}\n\n[제미나이nh]")

    def save_to_mysql(self, question, answer):
        try:
            # 1. 현재 시간 구하기
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 2. DB 연결 (요청마다 연결하고 끊는 것이 끊김 현상 방지에 좋습니다)
            conn = pymysql.connect( 
                host='bitnmeta2.synology.me', # MySQL 호스트 주소
                user='iyrc', # MySQL 사용자명
                passwd='Dodan1004!', # MySQL 비밀번호
                db='gemini_ai', # 사용할 데이터베이스 이름
                charset='utf8', # 문자셋 설정
                port=3307,  
                cursorclass=pymysql.cursors.DictCursor # 딕셔너리 커서 사용
            )

            with conn.cursor() as cursor:
                # 3. SQL 쿼리 작성 
                # ★ 'chat_history' 부분을 실제 테이블 이름으로 바꿔주세요!
                sql = "INSERT INTO chat_history (question, answer, create_at) VALUES (%s, %s, %s)"
                
                # 4. 실행 (데이터 매핑)
                cursor.execute(sql, (question, answer, current_time))
            
            # 5. 저장 확정 (Commit)
            conn.commit()
            print(f"✅ MySQL 저장 성공: {current_time}")

        except Exception as e:
            print(f"❌ MySQL 저장 실패: {e}")
        
        finally:
            # 6. 연결 종료 (자원 해제)
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    
    # 창 생성 및 표시
    
    window = GeminiApp()
    window.show()
    
    # 이벤트 루프 실행

    sys.exit(app.exec())
