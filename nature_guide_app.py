import os
import json
import base64
from io import BytesIO
from datetime import datetime
import streamlit as st
from google import genai
from PIL import Image

# ==============================================================================
# 1. 페이지 설정 및 프리미엄 모바일 테마 스타일링
# ==============================================================================
st.set_page_config(
    page_title="Flora & Fauna - 감성 생태 도감",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

CUSTOM_CSS = """
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* 배경 톤을 은은한 미색으로 조정 */
    .stApp {
        background-color: #F8FAF8;
    }

    /* 상단 기본 헤더/여백 미세 조정 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }

    /* 메인 히어로 배너 */
    .hero-banner {
        background: linear-gradient(135deg, #2D5A27 0%, #1E3F20 100%);
        border-radius: 20px;
        padding: 24px 20px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0 8px 20px rgba(45, 90, 39, 0.15);
    }
    .hero-banner h1 {
        color: #FFFFFF !important;
        font-size: 24px !important;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .hero-banner p {
        color: #D2E7D6;
        font-size: 13px;
        margin: 0;
    }

    /* 카드 컨테이너 공통 */
    .nature-card {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid #E9F0E9;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    }

    /* 종 분류 뱃지 */
    .badge-plant { background-color: #E8F5E9; color: #2E7D32; }
    .badge-animal { background-color: #FFF3E0; color: #E65100; }
    .badge-insect { background-color: #EDE7F6; color: #512DA8; }
    .badge-etc { background-color: #ECEFF1; color: #455A64; }
    
    .category-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    /* 생물명 헤드라인 */
    .species-title {
        font-size: 22px;
        font-weight: 800;
        color: #1F2937;
        margin-bottom: 4px;
    }
    .species-sci {
        font-size: 13px;
        font-style: italic;
        color: #6B7280;
        margin-bottom: 12px;
    }

    /* 섹션 레이블 타이틀 */
    .section-label {
        font-size: 15px;
        font-weight: 700;
        color: #2D5A27;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .section-body {
        font-size: 14px;
        line-height: 1.65;
        color: #374151;
        background: #F9FAF9;
        padding: 14px;
        border-radius: 12px;
        border-left: 3px solid #2D5A27;
        margin-bottom: 14px;
    }

    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #EBF2EC;
        padding: 5px;
        border-radius: 14px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 14px;
        color: #4B5563;
        flex: 1;
        text-align: center;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2D5A27 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    /* 버튼 모던화 */
    .stButton>button {
        border-radius: 14px;
        padding: 12px 20px;
        font-weight: 700;
        font-size: 15px;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 2. 데이터베이스 및 보조 함수
# ==============================================================================
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
    book.insert(0, entry)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=2)

def image_to_base64(img):
    buffered = BytesIO()
    fmt = img.format if img.format else "JPEG"
    img.save(buffered, format=fmt)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def render_voice_player(text, label="이 이야기 음성으로 듣기"):
    """세련된 둥근 캡슐형 음성 재생 컨트롤러 UI"""
    safe_text = json.dumps(text)
    html = f"""
    <div style="display:flex; align-items:center; gap:8px; margin: 10px 0 16px 0;">
        <button onclick='window.speechSynthesis.cancel(); var msg = new SpeechSynthesisUtterance({safe_text}); msg.lang = "ko-KR"; msg.rate = 0.93; window.speechSynthesis.speak(msg);' 
                style="flex:1; display:flex; align-items:center; justify-content:center; gap:6px; background-color: #2D5A27; color: white; border: none; border-radius: 30px; padding: 10px 18px; font-size: 13px; font-weight: 600; cursor: pointer; box-shadow: 0 3px 8px rgba(45,90,39,0.2);">
            <span>🔊</span> {label}
        </button>
        <button onclick='window.speechSynthesis.cancel();' 
                style="display:flex; align-items:center; justify-content:center; background-color: #F3F4F6; color: #4B5563; border: 1px solid #E5E7EB; border-radius: 30px; padding: 10px 14px; font-size: 13px; font-weight: 600; cursor: pointer;">
            ⏹ 멈춤
        </button>
    </div>
    """
    st.components.v1.html(html, height=52)

# ==============================================================================
# 3. Gemini API 초기화
# ==============================================================================
GEMINI_API_KEY = st.secrets.get"AQ.Ab8RN6LWGQ6hcCBcsiPXMcXddnvMaZoG2tNRex9Nx01G9XqmeA"
client = genai.Client(api_key=GEMINI_API_KEY)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "saved_status" not in st.session_state:
    st.session_state.saved_status = False

# ==============================================================================
# 4. 상단 브랜드 헤더
# ==============================================================================
st.markdown("""
<div class="hero-banner">
    <h1>🌿 숲과 들의 이야기</h1>
    <p>식물 · 동물 · 곤충의 이름과 숨겨진 이야기를 찾아 떠나는 산책</p>
</div>
""", unsafe_allow_html=True)

tab_scan, tab_book = st.tabs(["📷 관찰 카메라", "📚 내 도감 서재"])

# ------------------------------------------------------------------------------
# TAB 1: 관찰 카메라 & 인터랙티브 분석
# ------------------------------------------------------------------------------
with tab_scan:
    # 촬영 / 파일 업로드 선택
    photo_input = st.camera_input("주변의 동·식물을 직접 찍어보세요")
    if not photo_input:
        photo_input = st.file_uploader("또는 사진 앨범에서 선택", type=["jpg", "jpeg", "png"])

    if photo_input:
        image = Image.open(photo_input)
        st.session_state.current_image = image

        if st.button("🌱 이 생물 관찰 분석 시작하기", type="primary", use_container_width=True):
            st.session_state.saved_status = False
            with st.spinner("자연의 무늬와 특징을 꼼꼼하게 살피는 중입니다..."):
                prompt = """
                당신은 품격 있고 따뜻한 어조의 한국 숲 해설사이자 생태학자입니다.
                사진 속 생물을 식별하고, 반드시 아래의 JSON 포맷으로만 답변하세요.
                마크다운 코드블록(```json ... ```) 형태로 출력해주세요.

                {
                  "category": "식물 / 동물 / 곤충 / 기타 중 택 1",
                  "common_name": "한국어 표준 국명 (예: 산수국)",
                  "scientific_name": "학명 (이탤릭 표기 대상 영문 학명)",
                  "family": "과(Family) 명칭 (예: 수국과)",
                  "summary_tag": "이 생물을 가장 잘 나타내는 한 줄 핵심 수식어 (예: 산골짜기 물가에 피는 진짜 수국)",
                  "ecology": "자생 환경, 개화/결실/활동 시기, 잎 뒷면의 털, 수피, 독특한 번식 전략 등 관찰 핵심 포인트",
                  "similar_species": "사람들이 흔히 혼동하는 유사종 1~2종과 이를 현장에서 쉽게 가려내는 결정적 차이",
                  "storytelling": "이름의 어원, 민담이나 설화, 꽃말, 선조들의 지혜가 담긴 쓰임새 등 재미있는 인문학적 이야기"
                }
                """
                try:
                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[image, prompt]
                    )
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    st.session_state.analysis_result = json.loads(text)
                except Exception as e:
                    st.error(f"분석 도중 문제가 발생했습니다: {e}")

    # 카드형 결과 뷰
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        cat = res.get("category", "기타")
        badge_cls = "badge-plant" if "식물" in cat else "badge-animal" if "동물" in cat else "badge-insect" if "곤충" in cat else "badge-etc"

        st.markdown("<br>", unsafe_allow_html=True)
        
        # [히어로 카드: 기본 정보]
        st.markdown(f"""
        <div class="nature-card">
            <span class="category-badge {badge_cls}">● {cat}</span>
            <div class="species-title">{res.get('common_name')}</div>
            <div class="species-sci">{res.get('scientific_name')} · {res.get('family')}</div>
            <p style="color:#2D5A27; font-weight:600; font-size:14px; margin:0;">
                “{res.get('summary_tag', '')}”
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 1. 이름 음성 안내
        name_voice = f"발견하신 생물은 {cat} 분류에 속하는 {res.get('common_name')}입니다. 학명은 {res.get('scientific_name')}이며, {res.get('summary_tag', '')}입니다."
        render_voice_player(name_voice, "이름과 소개 음성 듣기")

        # [상세 정보 아코디언 카드]
        with st.expander("🌿 1. 생태적 특징 & 헷갈리는 유사종 비교", expanded=True):
            st.markdown("""<div class="section-label">📌 식생 및 관찰 특징</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="section-body">{res.get('ecology')}</div>""", unsafe_allow_html=True)
            
            st.markdown("""<div class="section-label">🔍 쌍둥이처럼 닮은 종 구별법</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="section-body">{res.get('similar_species')}</div>""", unsafe_allow_html=True)
            
            eco_voice = f"생태적 특징입니다. {res.get('ecology')} 혼동하기 쉬운 유사종 구별법입니다. {res.get('similar_species')}"
            render_voice_player(eco_voice, "생태 & 유사종 설명 듣기")

        with st.expander("📖 2. 이름의 유래와 흥미로운 스토리텔링", expanded=False):
            st.markdown("""<div class="section-label">📜 옛이야기와 어원</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="section-body">{res.get('storytelling')}</div>""", unsafe_allow_html=True)
            
            story_voice = f"이름의 유래와 이야기입니다. {res.get('storytelling')}"
            render_voice_player(story_voice, "스토리텔링 구연 듣기")

        # [도감 저장 액션 카드]
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; font-weight:700; color:#374151; font-size:15px; margin-bottom:12px;">
            이 발견을 나의 생태 도감에 기록해둘까요?
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 도감에 저장", type="primary", use_container_width=True, disabled=st.session_state.saved_status):
                entry = {
                    "date": datetime.now().strftime("%Y.%m.%d %H:%M"),
                    "category": res.get("category", "기타"),
                    "common_name": res.get("common_name"),
                    "scientific_name": res.get("scientific_name"),
                    "family": res.get("family"),
                    "summary_tag": res.get("summary_tag", ""),
                    "ecology": res.get("ecology"),
                    "similar_species": res.get("similar_species"),
                    "storytelling": res.get("storytelling"),
                    "image_b64": image_to_base64(st.session_state.current_image)
                }
                save_to_book(entry)
                st.session_state.saved_status = True
                st.toast("🌱 나만의 도감에 안전하게 기록되었습니다!", icon="✅")
        with c2:
            if st.button("✖️ 저장 안 함", use_container_width=True):
                st.toast("저장하지 않고 관찰을 마쳤습니다.")

# ------------------------------------------------------------------------------
# TAB 2: 나만의 생태 도감 (디지털 앨범 뷰)
# ------------------------------------------------------------------------------
with tab_book:
    book_items = load_book()
    
    # 상단 도감 카테고리 필터
    cats = ["전체", "식물", "동물", "곤충", "기타"]
    selected_filter = st.segmented_control("분류 선택", cats, default="전체") if hasattr(st, "segmented_control") else st.radio("분류 선택", cats, horizontal=True)

    filtered = [x for x in book_items if selected_filter == "전체" or x.get("category") == selected_filter]
    
    st.caption(f"수집된 기록 : 총 {len(filtered)}권")

    if not filtered:
        st.markdown("""
        <div class="nature-card" style="text-align:center; padding: 40px 20px;">
            <p style="font-size:32px; margin:0;">🍃</p>
            <p style="color:#6B7280; font-size:14px; margin-top:8px;">아직 저장된 관찰 일지가 없습니다.<br>야외 산책 중 새로운 만남을 기록해 보세요!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, item in enumerate(filtered):
            cat = item.get("category", "기타")
            badge_cls = "badge-plant" if "식물" in cat else "badge-animal" if "동물" in cat else "badge-insect" if "곤충" in cat else "badge-etc"
            
            with st.container():
                st.markdown(f"""
                <div class="nature-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="category-badge {badge_cls}">● {cat}</span>
                        <span style="font-size:11px; color:#9CA3AF;">{item.get('date')}</span>
                    </div>
                    <div class="species-title" style="font-size:19px;">{item.get('common_name')}</div>
                    <div class="species-sci">{item.get('scientific_name')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 촬영했던 사진 출력
                if item.get("image_b64"):
                    img_data = base64.b64decode(item["image_b64"])
                    st.image(Image.open(BytesIO(img_data)), use_container_width=True)

                with st.expander("📖 기록된 도감 내용 다시 읽기"):
                    st.markdown(f"**[특징]** {item.get('ecology')}")
                    st.markdown(f"**[유사종]** {item.get('similar_species')}")
                    st.markdown(f"**[이야기]** {item.get('storytelling')}")
                    
                    full_read = f"{item.get('common_name')}. {item.get('ecology')} {item.get('storytelling')}"
                    render_voice_player(full_read, "전체 설명 다시 듣기")
                
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)