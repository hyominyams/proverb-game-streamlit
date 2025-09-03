# streamlit_app.py
# -*- coding: utf-8 -*-
"""
속담 이어말하기 (안정화 버전)
- 1초 카운트다운 + 틱 사운드
- 정답/오답 제출 직후 정답 공개(오버레이), 정답이면 사운드+다음 문제, 입력칸 자동초기화
- 힌트(초성) 게임당 2회, 숨기기 없음(다음 문제로 넘기면 자동 초기화)
- 문제/입력칸은 구분선 위쪽, 중앙 배치
"""

import streamlit as st
import random, difflib, unicodedata, time
from typing import Dict, Tuple
from streamlit.components.v1 import html

# -------- rerun 호환 --------
def safe_rerun():
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()

# -------- 데이터 --------
PROVERBS: Dict[str, str] = {
    "낮말은 새가 듣고": "밤말은 쥐가 듣는다",
    "가는 말이 고와야": "오는 말이 곱다",
    "고래 싸움에": "새우 등 터진다",
    "돌다리도": "두들겨 보고 건너라",
    "백지장도": "맞들면 낫다",
    "등잔 밑이": "어둡다",
    "티끌 모아": "태산",
    "쇠귀에": "경 읽기",
    "말 한마디로": "천냥 빚을 갚는다",
    "호랑이 굴에 가야": "호랑이 새끼를 잡는다",
    "원숭이도": "나무에서 떨어진다",
    "서당 개 삼 년이면": "풍월을 읊는다",
    "소 잃고": "외양간 고친다",
    "배보다": "배꼽이 더 크다",
    "우물 안": "개구리",
    "뛰는 놈 위에": "나는 놈 있다",
    "바늘 도둑이": "소 도둑 된다",
    "수박 겉": "핥기",
    "세 살 버릇": "여든까지 간다",
    "누워서": "침 뱉기",
    "고생 끝에": "낙이 온다",
    "궁하면": "통한다",
    "바쁠수록": "돌아가라",
    "백문이": "불여일견",
    "팔은": "안으로 굽는다",
}

# -------- 유틸 --------
def normalize(t: str) -> str:
    s = unicodedata.normalize("NFKC", t or "")
    s = "".join(ch for ch in s if ch.isalnum() or ord(ch) > 0x3130)
    return s.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

_CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
def chosung_hint(s: str) -> str:
    base = 0xAC00; out = []
    for ch in s:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - base; cho_idx = idx // 588
            out.append(_CHO[cho_idx])
        elif ch.isspace(): out.append(" ")
        else: out.append(ch)
    return "".join(out).replace("  ", " ").replace(" ", " · ")

def pick_prompt(used: set) -> Tuple[str, str]:
    remain = [k for k in PROVERBS.keys() if k not in used]
    if not remain:
        used.clear(); remain = list(PROVERBS.keys())
    p = random.choice(remain)
    return p, PROVERBS[p]

# -------- 효과음/이펙트 --------
def play_tick_sound(running: bool):
    if running:
        html("""
        <script>
        (function(){
          if (window._tickInterval) return;
          const AC = window.AudioContext || window.webkitAudioContext;
          const ctx = new AC();
          const resume = ()=>{ ctx.resume(); document.removeEventListener('click', resume); };
          document.addEventListener('click', resume, {once:true});
          function tick(){
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.type='square'; o.frequency.value=1000;
            g.gain.setValueAtTime(0.0001, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime+0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime+0.08);
            o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.1);
          }
          window._tickInterval = setInterval(tick, 1000);
        })();
        </script>""", height=0)
    else:
        html("""
        <script>
        if (window._tickInterval){ clearInterval(window._tickInterval); window._tickInterval=null; }
        </script>""", height=0)

def play_correct_sound():
    html("""
    <script>
    (function(){
      const AC = window.AudioContext || window.webkitAudioContext;
      const ctx = new AC(); const t=ctx.currentTime;
      function beep(f, d, du){
        const o=ctx.createOscillator(), g=ctx.createGain();
        o.type='sine'; o.frequency.value=f;
        g.gain.setValueAtTime(0.0001, t+d);
        g.gain.exponentialRampToValueAtTime(0.35, t+d+0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t+d+du);
        o.connect(g); g.connect(ctx.destination); o.start(t+d); o.stop(t+d+du+0.03);
      }
      beep(523.25,0.00,0.12); beep(659.25,0.12,0.12); beep(783.99,0.24,0.18);
    })();
    </script>""", height=0)

def flash_answer(text: str, success: bool):
    color = "#10b981" if success else "#ef4444"
    html(f"""
    <style>
      @keyframes pop {{
        0%  {{ transform: scale(.9);  opacity:.0; }}
        50% {{ transform: scale(1.03); opacity:1;  }}
        100%{{ transform: scale(1.0); opacity:1;  }}
      }}
    </style>
    <div id="ansflash" style="
        position:fixed; left:50%; top:12%;
        transform:translateX(-50%);
        background:{color}; color:white; padding:10px 18px;
        border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,.2);
        font-size:18px; font-weight:700; z-index:9999; animation: pop .25s ease-out;">
        {text}
    </div>
    <script>
      setTimeout(() => {{
        const el = document.getElementById('ansflash');
        if (el) el.remove();
      }}, 1200);
    </script>
    """, height=0)

# -------- 상태 --------
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
ss = st.session_state
if "page" not in ss: ss.page="home"
if "started" not in ss: ss.started=False
if "score" not in ss: ss.score=0
if "best" not in ss: ss.best=0
if "used" not in ss: ss.used=set()
if "current" not in ss: ss.current=(None, None)
if "start_time" not in ss: ss.start_time=None
if "duration" not in ss: ss.duration=90
if "threshold" not in ss: ss.threshold=0.85
if "hint_used_total" not in ss: ss.hint_used_total=0   # 게임 전체 2회
if "show_hint" not in ss: ss.show_hint=False          # 현재 문제에만 표시
ANSWER_KEY="answer_text"

# -------- HOME --------
if ss.page == "home":
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>제한 시간 안에 많이 맞혀보세요! (오타 일부 허용)</p>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.subheader("게임 설정")
        ss.duration  = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
        ss.threshold = st.slider("🎯 정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)
        if st.button("▶️ 게임 시작", use_container_width=True):
            ss.started=True; ss.score=0; ss.best=max(ss.best, 0)
            ss.hint_used_total=0; ss.used=set()
            ss.start_time=time.time()
            ss.current=pick_prompt(ss.used)   # 문제 세팅
            ss.page="game"; ss.show_hint=False; ss[ANSWER_KEY]=""
            safe_rerun()
    st.caption("※ 브라우저 자동재생 정책에 따라 소리는 시작 버튼 클릭 후 활성화됩니다.")

# -------- GAME --------
if ss.page == "game":
    # 1초 자동 갱신
    if hasattr(st, "autorefresh"): st.autorefresh(interval=1000, key="__ticker__")

    # 문제 가드: current가 비었거나 prefix가 없으면 보충
    if not ss.current or not ss.current[0]:
        ss.current = pick_prompt(ss.used)

    _, mid, _ = st.columns([1,2,1])
    with mid:
        # 남은 시간
        remaining = 0
        if ss.started and ss.start_time:
            elapsed = int(time.time() - ss.start_time)
            remaining = max(0, ss.duration - elapsed)

        top1, top2, top3 = st.columns(3)
        top1.metric("점수", ss.score)
        top2.metric("최고 기록", ss.best)
        top3.metric("남은 시간", f"{remaining}s")

        # 틱 사운드
        play_tick_sound(ss.started and remaining > 0)

        # ===== 문제/입력/버튼(구분선 위쪽) =====
        prefix, answer = ss.current
        st.markdown(
            f"<div style='text-align:center; font-size:2.2rem; font-weight:800; margin-top:12px'>{prefix}</div>",
            unsafe_allow_html=True,
        )

        remain_hint = max(0, 2 - ss.hint_used_total)
        hint_disabled = (remain_hint == 0) or (ss.show_hint) or (not ss.started) or (remaining == 0)
        if st.button(f"💡 힌트(초성) 보기 (남은 {remain_hint}/2)", use_container_width=True, disabled=hint_disabled):
            ss.show_hint = True
            ss.hint_used_total += 1

        if ss.show_hint:
            st.info(f"힌트: **{chosung_hint(answer)}**")

        st.markdown("<div style='text-align:center; margin-top:6px'>정답을 입력해 보세요</div>", unsafe_allow_html=True)
        user_answer = st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed",
                                    placeholder="예) 밤말은 쥐가 듣는다", help="오타 조금은 괜찮아요!")

        colA, colB = st.columns([1,1])
        submit = colA.button("제출", use_container_width=True, disabled=(not ss.started or remaining==0))
        skip   = colB.button("스킵",  use_container_width=True, disabled=(not ss.started or remaining==0))

        # ===== 구분선 =====
        st.markdown("<hr>", unsafe_allow_html=True)

        # 제출 처리
        if submit and ss.started:
            sim = fuzzy_match(user_answer, answer)
            is_correct = sim >= ss.threshold
            flash_answer(f"정답: {answer}", success=is_correct)

            if is_correct:
                play_correct_sound()
                ss.score += 1; ss.best = max(ss.best, ss.score)
                ss.used.add(prefix)
                ss.current = pick_prompt(ss.used)
                ss[ANSWER_KEY] = ""     # 입력 초기화
                ss.show_hint = False    # 다음 문제로 넘어가면 힌트 자동 초기화
                safe_rerun()
            else:
                st.warning(f"아쉬워요 ❌ (유사도 {sim*100:.1f}%). 정답을 확인했어요!")

        # 스킵 처리(항상 활성화 조건 반영)
        if skip and ss.started and remaining > 0:
            ss.used.add(prefix)
            ss.current = pick_prompt(ss.used)
            ss[ANSWER_KEY] = ""
            ss.show_hint = False
            st.info("문제를 건너뛰었습니다.")
            safe_rerun()

        # 시간 종료
        if ss.started and remaining == 0:
            st.warning("⏰ 시간이 종료되었습니다! 첫 화면으로 돌아갑니다.")
            ss.started = False; ss.page = "home"

        if st.button("🏠 첫 화면으로", use_container_width=True):
            ss.page = "home"; safe_rerun()
