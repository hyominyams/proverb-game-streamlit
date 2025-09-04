# streamlit_app.py
# -*- coding: utf-8 -*-
import os, csv, time, random, difflib, unicodedata
from typing import Dict, Tuple, List
import streamlit as st
from streamlit.components.v1 import html

# ===================== 기본 설정 =====================
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
ss = st.session_state
ANSWER_KEY = "answer_box"
ANSWER_THRESHOLD = 0.8

# 전역 스타일
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; }
.stTextInput input { font-size: 1.3rem; padding: 16px 14px; }
</style>
""", unsafe_allow_html=True)

# ===================== CSV 로드 =====================
@st.cache_data(show_spinner="문제 파일을 읽고 있습니다...")
def load_question_bank() -> List[Dict[str, str]]:
    path = "question.csv"
    if not os.path.exists(path):
        return []
    bank: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            p = (row.get("prefix") or "").strip()
            a = (row.get("answer") or "").strip()
            if p and a:
                bank.append({"prefix": p, "answer": a})
    random.shuffle(bank)
    return bank

BANK = load_question_bank()
if not BANK:
    st.error("`question.csv` 파일을 찾을 수 없거나 내용이 비어 있습니다. CSV 파일을 확인하고 GitHub에 추가해주세요.")
    st.stop()

TOTAL_Q = len(BANK)

# ===================== 유틸 (채점/힌트/선택) =====================
def normalize(t: str) -> str:
    s = unicodedata.normalize("NFKC", t or "")
    s = "".join(ch for ch in s if ch.isalnum() or ord(ch) > 0x3130)
    return s.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

_CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
def chosung_hint(s: str) -> str:
    base=0xAC00; out=[]
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
        time.sleep(1)
        used.clear()
        remain = BANK[:]
        random.shuffle(remain)
    row = random.choice(remain)
    return row["prefix"], row["answer"]

# ===================== 사운드/이펙트/UI (사운드 로직 최종 수정) =====================
SOUND_MANAGER_HTML = """
<script>
(function() {
    if (window.soundManager) return; // 이미 초기화되었다면 실행 안 함

    const soundManager = {};
    let audioCtx;

    // 오디오 컨텍스트 초기화 (사용자 첫 인터랙션 시)
    const initAudioContext = () => {
        if (!audioCtx) {
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }
            } catch (e) {
                console.error("AudioContext를 지원하지 않는 브라우저입니다.", e);
            }
        }
    };
    document.addEventListener('click', initAudioContext, { once: true });
    document.addEventListener('touchstart', initAudioContext, { once: true });

    // 틱 소리 재생
    soundManager.playTick = function() {
        if (!audioCtx || audioCtx.state !== 'running') return;
        const o = audioCtx.createOscillator();
        const g = audioCtx.createGain();
        o.type = 'sine';
        o.frequency.setValueAtTime(1200, audioCtx.currentTime);
        g.gain.setValueAtTime(0, audioCtx.currentTime);
        g.gain.linearRampToValueAtTime(0.15, audioCtx.currentTime + 0.01);
        g.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.1);
        o.connect(g);
        g.connect(audioCtx.destination);
        o.start();
        o.stop(audioCtx.currentTime + 0.1);
    };

    // 정답 효과음 재생
    soundManager.playCorrect = function() {
        if (!audioCtx || audioCtx.state !== 'running') return;
        const t = audioCtx.currentTime;
        const freqs = [523.25, 783.99, 1046.5];
        freqs.forEach((f, i) => {
            const o = audioCtx.createOscillator(), g = audioCtx.createGain();
            o.type = 'triangle';
            o.frequency.setValueAtTime(f, t + i * 0.12);
            g.gain.setValueAtTime(0, t + i * 0.12);
            g.gain.exponentialRampToValueAtTime(0.3, t + i * 0.12 + 0.03);
            g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.12 + 0.18);
            o.connect(g);
            g.connect(audioCtx.destination);
            o.start(t + i * 0.12);
            o.stop(t + i * 0.12 + 0.2);
        });
    };

    // 타이머 제어
    let tickInterval = null;
    soundManager.startTicking = function() {
        if (tickInterval) return;
        tickInterval = setInterval(soundManager.playTick, 1000);
    };
    soundManager.stopTicking = function() {
        if (tickInterval) {
            clearInterval(tickInterval);
            tickInterval = null;
        }
    };

    window.soundManager = soundManager;
})();
</script>
"""
html(SOUND_MANAGER_HTML, height=0)

def control_ticking_sound(running: bool):
    script = "window.soundManager && window.soundManager.startTicking();" if running else "window.soundManager && window.soundManager.stopTicking();"
    html(f"<script>{script}</script>", height=0)

def play_correct_effect():
    st.balloons()
    html("""
    <div id="confetti" style="position:fixed;left:50%;bottom:-20px;transform:translateX(-50%);font-size:40px;opacity:0;transition:all .6s ease-out;z-index:9999;">🎉🎊✨</div>
    <script>
        window.soundManager && window.soundManager.playCorrect();
        const el = document.getElementById('confetti');
        if(el){
            setTimeout(() => { el.style.opacity=1; el.style.bottom='40%'; }, 10);
            setTimeout(() => { el.style.opacity=0; el.remove(); }, 900);
        }
    </script>
    """, height=0)

def flash_answer_overlay(text:str, success:bool):
    color = "#10b981" if success else "#ef4444"; html(f"""<style>@keyframes pop{{0%{{transform:scale(.9);opacity:.0;}}50%{{transform:scale(1.03);opacity:1;}}100%{{transform:scale(1.0);opacity:1;}}}}</style><div id="ansflash" style="position:fixed;left:50%;top:12%;transform:translateX(-50%);background:{color};color:white;padding:10px 18px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.2);font-size:18px;font-weight:700;z-index:9999;animation:pop .25s ease-out;">{text}</div><script>setTimeout(()=>{{const el=document.getElementById('ansflash');if(el)el.remove();}},1200);</script>""", height=0)

def render_stats(score:int, end_ts:float, hints:int):
    now_rem = max(0, int(round(end_ts - time.time()))) if end_ts else 0
    html(f"""
    <div class="stats">
      <div class="card"><div class="label">점수</div><div class="value">{score}</div></div>
      <div class="card"><div class="label">남은 시간</div><div class="value"><span id="timer_div">{now_rem}</span>s</div></div>
      <div class="card"><div class="label">힌트 사용</div><div class="value">{hints}/2</div></div>
    </div>
    <style>
      .stats {{ display:flex; gap:12px; justify-content:center; margin:18px 0 10px; }}
      .card {{ padding:12px 16px; border:1px solid #e9ecef; border-radius:12px; min-width:160px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.04); }}
      .card .label {{ font-size:.95rem; color:#666; margin-bottom:6px; }}
      .card .value {{ font-size:2.2rem; font-weight:800; line-height:1.1; }}
    </style>
    <script>
      (function(){{
        const end = {int(end_ts*1000) if end_ts else 0};
        const timerDiv = document.getElementById('timer_div');
        if (!window.mainTimerInterval) {{
            const update = () => {{
                if (!end || !timerDiv) return;
                const rem = Math.max(0, Math.round((end - Date.now())/1000));
                timerDiv.textContent = rem.toString();
            }};
            update();
            window.mainTimerInterval = setInterval(update, 1000);
        }}
      }})();
    </script>
    """, height=118)

# ===================== 상태 기본값 =====================
defaults = dict(page="home", started=False, score=0, best=0, used=set(), current=(None,None),
                duration=90, hint_used_total=0, hint_shown_for=None, end_time=None,
                reveal_text="", reveal_success=False, just_correct=False)
for k,v in defaults.items():
    if k not in ss: ss[k]=v

# ===================== 콜백/핵심 로직 =====================
def start_game():
    ss.started=True; ss.score=0; ss.used=set(); ss.hint_used_total=0; ss.hint_shown_for=None
    ss.current=pick_next(ss.used); ss.end_time=time.time()+ss.duration; ss.page="game"

def process_submission(user_text: str):
    if not (ss.started and ss.current[0]): return
    prefix, answer = ss.current
    is_correct = (fuzzy_match(user_text or "", answer) >= ANSWER_THRESHOLD)
    ss.reveal_text = f"정답: {answer}"; ss.reveal_success = is_correct
    if is_correct:
        ss.score += 1; ss.best = max(ss.best, ss.score); ss.just_correct = True
    else: ss.just_correct = False
    ss.used.add(prefix); ss.current = pick_next(ss.used); ss.hint_shown_for = None
    st.rerun()

def skip_question():
    if not ss.started: return
    prefix, _ = ss.current
    ss.used.add(prefix); ss.current = pick_next(ss.used); ss.hint_shown_for = None
    st.rerun()

def use_hint_for_current():
    if not (ss.started and ss.current[0] and ss.hint_used_total < 2): return
    cur_id = ss.current[0]
    if ss.hint_shown_for == cur_id: return
    ss.hint_used_total += 1; ss.hint_shown_for = cur_id; st.rerun()

def go_home():
    ss.page="home"; ss.started=False; ss.reveal_text=""; ss.hint_shown_for=None; control_ticking_sound(False)

# ===================== 화면 구성 =====================
if ss.page == "home":
    control_ticking_sound(False)
    # 2. 메인 화면 중앙 정렬을 위한 CSS
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        min-height: 70vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center'>제한 시간 안에 많이 맞혀보세요! (총 {TOTAL_Q}문제)</p>", unsafe_allow_html=True)
    
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.subheader("게임 설정")
        ss.duration = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
        st.button("▶️ 게임 시작", use_container_width=True, on_click=start_game)

elif ss.page == "game":
    if hasattr(st, "autorefresh"): st.autorefresh(interval=1000, key="__ticker__")
    if not ss.current or not ss.current[0]: ss.current = pick_next(ss.used)

    remaining = max(0, int(round((ss.end_time or time.time()) - time.time())))

    if ss.started and remaining == 0:
        control_ticking_sound(False); ss.started = False; st.rerun()

    if ss.started:
        render_stats(ss.score, ss.end_time or time.time(), ss.hint_used_total); control_ticking_sound(True)
        prefix, answer = ss.current
        
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.markdown(f"""<div style="border:1px solid #e9ecef;border-radius:14px;padding:24px 18px;box-shadow:0 2px 8px rgba(0,0,0,.04);margin-top:2px;"><div style="text-align:center;font-size:2.35rem;font-weight:800;">{prefix}</div></div>""", unsafe_allow_html=True)

        _, mid2, _ = st.columns([1, 2, 1])
        with mid2:
            st.markdown("""<div style="margin-top:12px;"></div>""", unsafe_allow_html=True)
            with st.form("answer_form", clear_on_submit=True):
                st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed", help="오타 조금은 괜찮아요!")
                submitted = st.form_submit_button("제출", use_container_width=True)
                if submitted: process_submission(st.session_state.get(ANSWER_KEY, ""))
            
            colH, colS = st.columns([1, 1])
            colH.button("💡 힌트", use_container_width=True, disabled=(remaining==0) or (ss.hint_used_total>=2) or (ss.hint_shown_for == prefix), on_click=use_hint_for_current)
            colS.button("➡️ 스킵", use_container_width=True, disabled=(remaining==0), on_click=skip_question)
            
            if ss.hint_shown_for == prefix:
                st.info(f"힌트: **{chosung_hint(answer)}**")

        if ss.reveal_text: flash_answer_overlay(ss.reveal_text, ss.reveal_success); ss.reveal_text = ""
        if ss.just_correct: play_correct_effect(); ss.just_correct = False

    elif not ss.started and ss.page == "game":
        st.markdown("### ⏰ TIME OUT!")
        st.success(f"최종 점수: {ss.score}점 / 힌트 사용 {ss.hint_used_total}/2")
        col = st.columns([1, 2, 1])[1]
        with col:
            st.button("다시 시작", use_container_width=True, on_click=start_game)
            st.button("🏠 첫 화면", use_container_width=True, on_click=go_home)
