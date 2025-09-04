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

# ===================== CSV 로드 (중복 데이터 경고 추가) =====================
CSV_CANDIDATES = ["question.csv"]

@st.cache_data(show_spinner="문제 파일을 읽고 있습니다...")
def load_question_bank() -> List[Dict[str, str]]:
    path = None
    for cand in CSV_CANDIDATES:
        if os.path.exists(cand):
            path = cand
            break
    bank: List[Dict[str, str]] = []
    seen_prefixes = set()
    duplicates = []
    if path:
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                p = (row.get("prefix") or row.get("PREFIX") or "").strip()
                a = (row.get("answer") or row.get("ANSWER") or "").strip()
                if p and a:
                    if p in seen_prefixes:
                        duplicates.append(p)
                    else:
                        bank.append({"prefix": p, "answer": a})
                        seen_prefixes.add(p)
    if duplicates:
        st.warning(f"⚠️ **경고:** `question.csv` 파일에 중복된 문제가 있습니다. 다음 문제는 제외되었습니다: `{', '.join(set(duplicates))}`")
    random.shuffle(bank)
    return bank

BANK = load_question_bank()
if not BANK:
    st.error("`question.csv`를 찾을 수 없거나, `prefix,answer` 데이터가 비어 있습니다. CSV를 업로드한 뒤 다시 실행하세요.")
    st.stop()

TOTAL_Q = len(BANK)

# ===================== 유틸(채점/힌트/선택, 리셋 알림 추가) =====================
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
        st.toast("🎉 모든 문제를 다 풀었습니다! 처음부터 다시 시작합니다.")
        time.sleep(1) # 토스트 메시지를 볼 시간을 줍니다.
        used.clear()
        remain = BANK[:]
        random.shuffle(remain)
    row = random.choice(remain)
    return row["prefix"], row["answer"]

# ===================== 사운드/이펙트 (수정 없음) =====================
def play_tick_sound(running: bool):
    if running: html("""...""", height=0)
    else: html("""...""", height=0)
def play_correct_sound_and_confetti():
    st.balloons(); html("""...""", height=0)
def flash_answer_overlay(text:str, success:bool):
    color = "#10b981" if success else "#ef4444"; html(f"""...""", height=0)
def render_stats(score:int, end_ts:float, hints:int):
    now_rem = max(0, int(round(end_ts - time.time()))) if end_ts else 0; html(f"""...""", height=118)

# ===================== Gemini 이미지 (디버깅 로그 추가) =====================
IMG_DIR = pathlib.Path("assets/images")
IMG_DIR.mkdir(parents=True, exist_ok=True)

def _slug(s: str) -> str: return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]
def image_path_for(prefix: str, answer: str) -> str: return str(IMG_DIR / f"{_slug(prefix+' '+answer)}.png")

@st.cache_resource(show_spinner=False)
def get_executor(): return ThreadPoolExecutor(max_workers=2)

_inflight_lock = threading.Lock()
_inflight = set()

def _get_gemini_api_key() -> str | None: return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

def _generate_image_with_gemini(prefix: str, answer: str, out_path: str) -> bool:
    try: import google.generativeai as genai
    except Exception as e:
        print(f"[Init Error] google.generativeai 라이브러리를 임포트할 수 없습니다: {e}"); return False

    api_key = _get_gemini_api_key()
    if not api_key:
        print("[Config Error] Gemini API 키가 설정되지 않았습니다."); return False

    sketch_prompt = ("아이들이 속담을 쉽게 이해하도록, 채색과 디테일을 최소화한 '간단한 선 스케치' 스타일로 그려줘. "
                     "텍스트는 절대 넣지 말고, 밝고 친근한 느낌으로.")
    prompt = f"{sketch_prompt}\n속담: '{prefix} … {answer}'"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash") # 속도가 빠른 모델 사용
        response = model.generate_content(prompt, generation_config={"response_mime_type": "image/png"})

        if response.parts:
            pathlib.Path(out_path).write_bytes(response.parts[0].inline_data.data)
            return True
        else:
            print(f"[API Error] 이미지 데이터가 비어있는 응답: {response}")
            return False
    except Exception as e:
        print(f"[Image Generation Error] 이미지 생성 중 예외 발생: {e}") # ◀️ 실패 원인 로그 출력
        return False

def ensure_image_async(prefix: str, answer: str) -> tuple[str, bool]:
    path = image_path_for(prefix, answer)
    if os.path.exists(path): return path, True
    key = path
    with _inflight_lock:
        if key in _inflight: return path, False
        _inflight.add(key)
    def _job():
        try: _generate_image_with_gemini(prefix, answer, path)
        finally:
            with _inflight_lock: _inflight.discard(key)
    get_executor().submit(_job)
    return path, False

# ===================== 상태 기본값 =====================
defaults = dict(page="home", started=False, score=0, best=0, used=set(), current=(None,None),
                next_item=None, duration=90, threshold=0.85, hint_used_total=0, hint_shown_for=None,
                end_time=None, reveal_text="", reveal_success=False, just_correct=False)
for k,v in defaults.items():
    if k not in ss: ss[k]=v

# ===================== 콜백/핵심 로직 =====================
def start_game():
    ss.started = True; ss.score = 0; ss.used = set(); ss.hint_used_total = 0; ss.hint_shown_for = None
    ss.current = pick_next(ss.used); ss.next_item = pick_next(ss.used)
    ensure_image_async(*ss.current); ensure_image_async(*ss.next_item)
    ss.end_time = time.time() + ss.duration; ss.page = "game"

def process_submission(user_text: str):
    if not (ss.started and ss.current[0]): return
    prefix, answer = ss.current
    is_correct = (fuzzy_match(user_text or "", answer) >= ss.threshold)
    ss.reveal_text = f"정답: {answer}"; ss.reveal_success = is_correct
    if is_correct:
        ss.score += 1; ss.best = max(ss.best, ss.score); ss.just_correct = True
    else: ss.just_correct = False
    ss.used.add(prefix); ss.current = ss.next_item; ss.next_item = pick_next(ss.used)
    ss.hint_shown_for = None
    ensure_image_async(*ss.current); ensure_image_async(*ss.next_item)
    st.rerun()

def skip_question():
    if not ss.started: return
    prefix, _ = ss.current
    ss.used.add(prefix); ss.current = ss.next_item; ss.next_item = pick_next(ss.used)
    ss.hint_shown_for = None
    ensure_image_async(*ss.current); ensure_image_async(*ss.next_item)
    st.rerun()

def use_hint_for_current():
    if not (ss.started and ss.current[0] and ss.hint_used_total < 2): return
    cur_id = ss.current[0]
    if ss.hint_shown_for == cur_id: return
    ss.hint_used_total += 1; ss.hint_shown_for = cur_id; st.rerun()

def go_home():
    ss.page = "home"; ss.started = False; ss.reveal_text = ""; ss.hint_shown_for = None; play_tick_sound(False)

# ===================== 홈 화면 =====================
if ss.page == "home":
    play_tick_sound(False)
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center'>제한 시간 안에 많이 맞혀보세요! (총 {TOTAL_Q}문제, 오타 일부 허용)</p>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.subheader("게임 설정"); ss.duration = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
        ss.threshold = st.slider("🎯 정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)
        st.button("▶️ 게임 시작", use_container_width=True, on_click=start_game)
    st.caption("※ 브라우저 자동재생 정책상 소리는 첫 클릭 이후 활성화됩니다.")

# ===================== 게임 화면 (타임아웃 로직 수정) =====================
if ss.page == "game":
    if hasattr(st, "autorefresh"): st.autorefresh(interval=1000, key="__ticker__")
    if not ss.current or not ss.current[0]: ss.current = pick_next(ss.used)

    remaining = max(0, int(round((ss.end_time or time.time()) - time.time())))

    # 2번 해결: 타임아웃 발생 시 started 상태를 False로 변경하여 게임을 확실히 멈춤
    if ss.started and remaining == 0:
        play_tick_sound(False)
        ss.started = False
        st.rerun() # 상태 변경 후 즉시 재실행하여 타임아웃 화면을 표시

    # 게임 진행 중 화면
    if ss.started:
        render_stats(ss.score, ss.end_time or time.time(), ss.hint_used_total); play_tick_sound(True)
        _, mid, _ = st.columns([1,2,1])
        with mid:
            prefix, answer = ss.current
            st.markdown(f"""...""", unsafe_allow_html=True) # 문제 박스 UI
            img_path, ready = ensure_image_async(prefix, answer)
            if ready: st.image(img_path, use_column_width=True, caption="AI 그림 힌트")
            else: st.markdown("<div style='text-align:center; color:#888'>🎨 그림 힌트 준비 중…</div>", unsafe_allow_html=True)

        _, mid2, _ = st.columns([1,2,1])
        with mid2:
            st.markdown("""...""") # 입력 안내 UI
            with st.form("answer_form", clear_on_submit=True):
                st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed", help="오타 조금은 괜찮아요!")
                submitted = st.form_submit_button("제출", use_container_width=True)
                if submitted: process_submission(st.session_state.get(ANSWER_KEY, ""))
            colH, colS = st.columns([1,1])
            colH.button("💡 힌트", use_container_width=True,
                        disabled=(remaining==0) or (ss.hint_used_total>=2) or (ss.hint_shown_for == ss.current[0]),
                        on_click=use_hint_for_current)
            colS.button("➡️ 스킵", use_container_width=True, disabled=(remaining==0), on_click=skip_question)
            if ss.hint_shown_for == ss.current[0]: st.info(f"힌트: **{chosung_hint(ss.current[1])}**")
            st.markdown("</div>", unsafe_allow_html=True)
        if ss.reveal_text: flash_answer_overlay(ss.reveal_text, ss.reveal_success); ss.reveal_text = ""
        if ss.just_correct: play_correct_sound_and_confetti(); ss.just_correct = False

    # 타임아웃 화면 (ss.started가 False이고 ss.page가 'game'일 때)
    elif not ss.started and ss.page == "game":
        st.markdown("### ⏰ TIME OUT!")
        st.success(f"최종 점수: {ss.score}점 / 힌트 사용 {ss.hint_used_total}/2")
        col = st.columns([1,2,1])[1]
        with col:
            st.button("다시 시작", use_container_width=True, on_click=start_game)
            st.button("🏠 첫 화면", use_container_width=True, on_click=go_home)
