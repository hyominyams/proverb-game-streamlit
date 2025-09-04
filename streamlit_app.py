# streamlit_app.py
# -*- coding: utf-8 -*-
import os, csv, time, random, difflib, unicodedata, hashlib, pathlib, threading
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from streamlit.components.v1 import html

# ===================== 기본 설정 =====================
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
ss = st.session_state
ANSWER_KEY = "answer_box"

# 전역 스타일
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; }  /* 상단 잘림 방지 */
.stTextInput input { font-size: 1.3rem; padding: 16px 14px; }
</style>
""", unsafe_allow_html=True)

# ===================== CSV 로드 =====================
CSV_CANDIDATES = ["question.csv", "data/question.csv"]

@st.cache_data(show_spinner="문제 파일(question.csv)을 읽고 있습니다...")
def load_question_bank() -> List[Dict[str, str]]:
    path = None
    for cand in CSV_CANDIDATES:
        if os.path.exists(cand):
            path = cand
            break
    bank: List[Dict[str, str]] = []
    if path:
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            # 허용 헤더: prefix, answer (대소문자 무시)
            for row in r:
                p = (row.get("prefix") or row.get("PREFIX") or "").strip()
                a = (row.get("answer") or row.get("ANSWER") or "").strip()
                if p and a:
                    bank.append({"prefix": p, "answer": a})
    if not bank:
        # FALLBACK 데이터를 삭제하고, 파일이 없을 경우 에러 메시지를 표시
        st.error("❌ question.csv 파일을 찾을 수 없거나 내용이 비어있습니다. 파일을 확인해주세요.")
        st.stop()
    random.shuffle(bank)
    return bank

BANK = load_question_bank()
# 앱 시작 시 한 번만 로드 성공 메시지 표시
if '__loaded_toast__' not in ss:
    st.toast(f"✅ {len(BANK)}개의 문제를 불러왔습니다.")
    ss['__loaded_toast__'] = True


# ===================== 유틸(채점/힌트/선택) =====================
def normalize(t: str) -> str:
    s = unicodedata.normalize("NFKC", t or "")
    s = "".join(ch for ch in s if ch.isalnum() or ord(ch) > 0x3130)
    return s.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

_CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
def chosung_hint(s: str) -> str:
    base = 0xAC00; out=[]
    for ch in s:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - base; cho_idx = idx // 588
            out.append(_CHO[cho_idx])
        elif ch.isspace(): out.append(" ")
        else: out.append(ch)
    return "".join(out).replace("  "," ").replace(" "," · ")

def pick_next(used:set) -> Tuple[str,str]:
    remain = [row for row in BANK if row["prefix"] not in used]
    if not remain:
        used.clear()
        remain = BANK[:]
        random.shuffle(remain)
    row = random.choice(remain)
    return row["prefix"], row["answer"]

# ===================== 사운드/이펙트 (수정 없음) =====================
def play_tick_sound(running: bool):
    if running:
        html("""...""", height=0) # 내용은 생략 (기존 코드와 동일)
    else:
        html("""...""", height=0)

def play_correct_sound_and_confetti():
    st.balloons()
    html("""...""", height=0)

def flash_answer_overlay(text:str, success:bool):
    color = "#10b981" if success else "#ef4444"
    html(f"""...""", height=0)

def render_stats(score:int, end_ts:float, hints:int):
    now_rem = max(0, int(round(end_ts - time.time()))) if end_ts else 0
    html(f"""...""", height=118)

# ===================== Gemini 이미지 (비동기+캐시) =====================
IMG_DIR = pathlib.Path("assets/images")
IMG_DIR.mkdir(parents=True, exist_ok=True)

def _slug(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def image_path_for(prefix: str, answer: str) -> str:
    return str(IMG_DIR / f"{_slug(prefix+' '+answer)}.png")

@st.cache_resource(show_spinner=False)
def get_executor():
    return ThreadPoolExecutor(max_workers=2)

_inflight_lock = threading.Lock()
_inflight = set()

def _get_gemini_api_key() -> str | None:
    return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

def _generate_image_with_gemini(prefix: str, answer: str, out_path: str) -> bool:
    try:
        import google.generativeai as genai
    except Exception:
        return False

    api_key = _get_gemini_api_key()
    if not api_key:
        return False

    try:
        genai.configure(api_key=api_key)
        # 3번 요청: 프롬프트를 빠르고 간단한 스케치 스타일로 변경
        prompt = (
            "간단한 선 스케치 스타일. 아이들이 속담을 쉽게 이해할 수 있도록, "
            "채색이나 복잡한 디자인 없이 특징만 빠르게 그려줘. "
            f"속담: '{prefix} … {answer}'. "
            "그림에 글자는 절대 넣지마."
        )
        model = genai.GenerativeModel("gemini-1.5-flash") # 이미지 생성 가능한 모델
        response = model.generate_content(prompt, generation_config={"response_mime_type": "image/png"})

        if response.parts:
            pathlib.Path(out_path).write_bytes(response.parts[0].inline_data.data)
            return True
        return False
    except Exception:
        return False

def ensure_image_async(prefix: str, answer: str) -> tuple[str, bool]:
    path = image_path_for(prefix, answer)
    if os.path.exists(path):
        return path, True

    key = path
    with _inflight_lock:
        if key in _inflight:
            return path, False
        _inflight.add(key)

    def _job():
        try:
            _generate_image_with_gemini(prefix, answer, path)
        finally:
            with _inflight_lock:
                _inflight.discard(key)

    get_executor().submit(_job)
    return path, False

# ===================== 상태 기본값 =====================
defaults = dict(
    page="home", started=False, score=0, best=0, used=set(),
    current=(None,None), next_item=None,
    duration=90, threshold=0.85, hint_used_total=0, show_hint=False,
    end_time=None, reveal_text="", reveal_success=False, just_correct=False
)
for k,v in defaults.items():
    if k not in ss: ss[k]=v

# ===================== 콜백/핵심 로직 =====================
def start_game():
    ss.started = True
    ss.score = 0
    ss.used = set()
    ss.hint_used_total = 0
    ss.current = pick_next(ss.used)
    ss.next_item = pick_next(ss.used)
    ensure_image_async(*ss.current)
    ensure_image_async(*ss.next_item)
    ss.end_time = time.time() + ss.duration
    ss.page = "game"
    ss.show_hint = False

def process_submission(user_text: str):
    if not (ss.started and ss.current[0]):
        return
    prefix, answer = ss.current
    is_correct = (fuzzy_match(user_text or "", answer) >= ss.threshold)

    ss.reveal_text = f"정답: {answer}"
    ss.reveal_success = is_correct

    if is_correct:
        ss.score += 1
        ss.best = max(ss.best, ss.score)
        ss.just_correct = True
    else:
        ss.just_correct = False

    ss.used.add(prefix)
    ss.current = ss.next_item
    ss.next_item = pick_next(ss.used)
    # 1번 요청: 다음 문제로 넘어갈 때 힌트 상태 초기화
    ss.show_hint = False

    ensure_image_async(*ss.current)
    ensure_image_async(*ss.next_item)

    st.rerun()

def skip_question():
    if not ss.started: return
    prefix, _ = ss.current
    ss.used.add(prefix)
    ss.current = ss.next_item
    ss.next_item = pick_next(ss.used)
    ss.show_hint = False
    ensure_image_async(*ss.current)
    ensure_image_async(*ss.next_item)
    st.rerun()

def use_hint():
    if ss.hint_used_total < 2 and not ss.show_hint and ss.started:
        ss.hint_used_total += 1
        ss.show_hint = True
        st.rerun()

def go_home():
    ss.page = "home"
    ss.started = False
    ss.reveal_text = ""
    ss.show_hint = False
    play_tick_sound(False)

# ===================== 홈 화면 =====================
if ss.page == "home":
    play_tick_sound(False)
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>제한 시간 안에 많이 맞혀보세요! (오타 일부 허용)</p>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.subheader("게임 설정")
        ss.duration  = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
        ss.threshold = st.slider("🎯 정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)
        st.button("▶️ 게임 시작", use_container_width=True, on_click=start_game)
    st.caption("※ 브라우저 자동재생 정책상 소리는 첫 클릭 이후 활성화됩니다.")

# ===================== 게임 화면 =====================
if ss.page == "game":
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, key="__ticker__")

    if not ss.current or not ss.current[0]:
        ss.current = pick_next(ss.used)

    remaining = max(0, int(round((ss.end_time or time.time()) - time.time())))
    if ss.started and remaining == 0:
        play_tick_sound(False)
        st.markdown("### ⏰ TIME OUT!")
        st.success(f"최종 점수: {ss.score}점 / 힌트 사용 {ss.hint_used_total}/2")
        col = st.columns([1,2,1])[1]
        with col:
            st.button("다시 시작", use_container_width=True, on_click=start_game)
            st.button("🏠 첫 화면", use_container_width=True, on_click=go_home)
    else:
        render_stats(ss.score, ss.end_time or time.time(), ss.hint_used_total)
        play_tick_sound(ss.started and remaining > 0)

        _, mid, _ = st.columns([1,2,1])
        with mid:
            prefix, answer = ss.current
            st.markdown(f"""...""", unsafe_allow_html=True) # 내용은 생략

            img_path, ready = ensure_image_async(prefix, answer)
            if ready:
                st.image(img_path, use_column_width=True, caption="AI 그림 힌트")
            else:
                st.markdown("<div style='text-align:center; color:#888'>🎨 그림 힌트 준비 중…</div>", unsafe_allow_html=True)

        _, mid2, _ = st.columns([1,2,1])
        with mid2:
            st.markdown("""...""", unsafe_allow_html=True) # 내용은 생략

            with st.form("answer_form", clear_on_submit=True):
                st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed",
                              help="오타 조금은 괜찮아요!")
                submitted = st.form_submit_button("제출", use_container_width=True)
                if submitted:
                    process_submission(st.session_state.get(ANSWER_KEY, ""))

            colH, colS = st.columns([1,1])
            colH.button("💡 초성 힌트", use_container_width=True,
                        disabled=(not ss.started) or (ss.hint_used_total>=2) or ss.show_hint or remaining==0,
                        on_click=use_hint)
            colS.button("➡️ 스킵", use_container_width=True,
                        disabled=(not ss.started or remaining==0),
                        on_click=skip_question)

            if ss.show_hint:
                st.info(f"힌트: **{chosung_hint(answer)}**")

            st.markdown("</div>", unsafe_allow_html=True)

        if ss.reveal_text:
            flash_answer_overlay(ss.reveal_text, ss.reveal_success)
            ss.reveal_text = ""
        if ss.just_correct:
            play_correct_sound_and_confetti()
            ss.just_correct = False
