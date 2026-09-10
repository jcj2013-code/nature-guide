import os
import json
import base64
from io import BytesIO
from datetime import datetime
import streamlit as st
from google import genai
from PIL import Image

# ==========================================
# 1. 페이지 설정 및 디자인 (모바일 화면 최적화)
# ==========================================
st.set_page_config(
    page_title="나만의 AI 생태 도감",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 모바일 UI 스타일링
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        padding: 10px 16px;
        font-weight: bold;
    }
    .info-card {
        background-color: #f7faf8;
        border: 1px solid #dce7e1;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터베이스(도감) 저장 관리
# ==========================================
DB_FILE = "my_nature_book.json"

def load_book():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_book(entry):
    book = load_book()
    book.insert(0, entry)  # 최신 관찰 기록을 맨 앞으로
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=2)

def image_to_base64(img):
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# 스마트폰 내장 브라우저 한국어 음성 재생(TTS) 자바스크립트 컴포넌트
def speak_button(text, button_label="🔊 음성으로 듣기"):
    safe_text = json.dumps(text)
    html_code = f"""
    <div style="margin: 8px 0;">
        <button onclick='window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance({safe_text}); msg.lang = "ko-KR"; msg.rate = 0.95; window.speechSynthesis.speak(msg);' 
                style="background-color: #2e7d32; color: white; border: none; border-radius: 8px; padding: 8px 14px; font-size: 14px; cursor: pointer;">
            {button_label}
        </button>
        <button onclick='window.speechSynthesis.cancel();' 
                style="background-color: #757575; color: white; border: none; border-radius: 8px; padding: 8px 14px; font-size: 14px; cursor: pointer; margin-left: 5px;">
            ⏹ 정지
        </button>
    </div>
    """
    st.components.v1.html(html_code, height=45)

# ==========================================
# 3. Gemini API 초기화
# ==========================================
# 여기에 본인의 Gemini API 키를 넣으세요.
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "여기에_로컬_테스트용_키")
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 4. 세션 상태 관리 (스마트폰 인터랙션용)
# ==========================================
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "saved_status" not in st.session_state:
    st.session_state.saved_status = False

# ==========================================
# 5. 상단 네비게이션 (관찰하기 vs 내 도감 보기)
# ==========================================
tab1, tab2 = st.tabs(["📷 산책 관찰 카메라", "📚 나만의 생태 도감"])

# ----------------------------------------------------
# 탭 1: 산책 관찰 카메라
# ----------------------------------------------------
with tab1:
    st.markdown("### 🌿 AI 생태 해설사")
    st.caption("공원이나 숲길에서 마주친 생물을 촬영해 보세요.")

    # 스마트폰 카메라 활성화 (갤러리 선택도 가능)
    camera_photo = st.camera_input("카메라로 직접 촬영")
    uploaded_photo = st.file_uploader("또는 사진첩에서 가져오기", type=["jpg", "jpeg", "png"])
    
    active_photo = camera_photo or uploaded_photo

    if active_photo:
        image = Image.open(active_photo)
        st.session_state.current_image = image

        if st.button("🔍 이 생물 알아보기", type="primary"):
            st.session_state.saved_status = False
            with st.spinner("생물의 특징을 정밀하게 분석 중입니다..."):
                prompt = """
                당신은 현장 경험이 풍부한 한국의 생태학자이자 전문 숲 해설사입니다.
                사진 속 생물을 식별하고, 반드시 아래 명시된 유효한 JSON 형식으로만 답하세요. 
                마크다운 코드블록(```json ... ```)을 포함해도 됩니다.

                {
                  "category": "식물 / 동물 / 곤충 / 기타 중 택 1",
                  "common_name": "한국어 표준 국명 (예: 산철쭉)",
                  "scientific_name": "학명 (예: Rhododendron yedoense var. poukhanense)",
                  "family": "과(Family) 명칭",
                  "ecology": "자생 환경, 개화/결실/활동 시기, 잎이나 수피, 깃털 등 식생적 핵심 특징을 자연스러운 구어체로 설명",
                  "similar_species": "혼동하기 쉬운 비슷한 다른 종과 이를 한눈에 구별할 수 있는 결정적인 관찰 포인트",
                  "storytelling": "이름에 얽힌 유래, 어원, 설화, 민간 전설이나 옛 선조들의 재미있는 생활 속 쓰임새 스토리"
                }
                """
                try:
                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[image, prompt]
                    )
                    
                    # JSON 응답 파싱
                    raw_text = response.text.strip()
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    
                    st.session_state.analysis_result = json.loads(raw_text)
                except Exception as e:
                    st.error(f"분석 중 문제가 발생했습니다: {e}")

    # 분석 결과 출력 화면
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        
        st.markdown("---")
        # 1단계: 이름 알림
        st.markdown(f"## 🏷️ [{res.get('category')}] {res.get('common_name')}")
        st.markdown(f"*{res.get('scientific_name')}* | `{res.get('family')}`")
        
        name_voice = f"이 생물은 {res.get('category')} 분류에 속하는 {res.get('common_name')}입니다. 학명은 {res.get('scientific_name')}입니다."
        speak_button(name_voice, "🔊 이름 듣기")

        # 2단계: 생태 특징 및 유사종 정보 (버튼 토글 / 아코디언)
        with st.expander("🌱 자세한 생태적 특징 및 헷갈리는 유사종 보기", expanded=False):
            st.markdown(f"**[식생/생태 특징]**\n\n{res.get('ecology')}")
            st.markdown(f"**[혼동하기 쉬운 유사종 비교]**\n\n{res.get('similar_species')}")
            
            detail_voice = f"생태적 특징입니다. {res.get('ecology')} 유사종 구별법입니다. {res.get('similar_species')}"
            speak_button(detail_voice, "🔊 생태/유사종 설명 듣기")

        # 3단계: 스토리텔링 정보 (버튼 토글 / 아코디언)
        with st.expander("📖 흥미로운 이름의 유래와 스토리텔링 보기", expanded=False):
            st.markdown(f"{res.get('storytelling')}")
            
            story_voice = f"이름에 얽힌 이야기입니다. {res.get('storytelling')}"
            speak_button(story_voice, "🔊 스토리텔링 듣기")

        # 4단계: 나만의 도감 저장 여부 선택
        st.markdown("---")
        st.write("📌 **이 발견을 나만의 생태 도감에 보관하시겠습니까?**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 도감에 저장", type="primary", disabled=st.session_state.saved_status):
                new_entry = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "category": res.get("category", "기타"),
                    "common_name": res.get("common_name"),
                    "scientific_name": res.get("scientific_name"),
                    "family": res.get("family"),
                    "ecology": res.get("ecology"),
                    "similar_species": res.get("similar_species"),
                    "storytelling": res.get("storytelling"),
                    "image_b64": image_to_base64(st.session_state.current_image)
                }
                save_to_book(new_entry)
                st.session_state.saved_status = True
                st.success("도감에 성공적으로 기록되었습니다! '나만의 생태 도감' 탭에서 확인하세요.")
        
        with col2:
            if st.button("❌ 저장하지 않음"):
                st.info("기록을 건너뛰었습니다. 새 사진을 촬영할 수 있습니다.")

# ----------------------------------------------------
# 탭 2: 나만의 생태 도감 (자동 분류 및 아카이빙)
# ----------------------------------------------------
with tab2:
    st.markdown("### 📚 나의 야외 관찰 도감")
    book_data = load_book()

    if not book_data:
        st.info("아직 저장된 도감 기록이 없습니다. 산책하며 생물을 관찰해 보세요!")
    else:
        # 식물, 동물, 곤충, 기타 카테고리 필터
        categories = ["전체", "식물", "동물", "곤충", "기타"]
        selected_cat = st.radio("분류 필터", categories, horizontal=True)

        filtered_book = [item for item in book_data if selected_cat == "전체" or item.get("category") == selected_cat]
        st.caption(f"총 {len(filtered_book)}개의 기록이 있습니다.")

        for idx, item in enumerate(filtered_book):
            with st.container():
                st.markdown(f"#### [{item.get('category')}] {item.get('common_name')}")
                st.caption(f"📅 관찰 일시: {item.get('date')} | 학명: {item.get('scientific_name')}")
                
                # 저장된 이미지 표시
                if item.get("image_b64"):
                    img_data = base64.b64decode(item["image_b64"])
                    st.image(Image.open(BytesIO(img_data)), use_container_width=True)
                
                with st.expander("자세한 기록 다시 보기"):
                    st.markdown(f"**생태 특성:** {item.get('ecology')}")
                    st.markdown(f"**유사종 구별:** {item.get('similar_species')}")
                    st.markdown(f"**스토리텔링:** {item.get('storytelling')}")
                    
                    full_text = f"{item.get('common_name')}. {item.get('ecology')} {item.get('storytelling')}"
                    speak_button(full_text, f"🔊 전체 이야기 다시 듣기")
                st.markdown("---")
