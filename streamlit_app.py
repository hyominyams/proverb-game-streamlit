# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Streamlit 속담 이어말하기 게임 (요청사항 반영)
- 문제/입력칸을 구분선 위쪽에 배치
- 힌트(초성) : 게임당 2회 제한, 숨기기 없음(다음 문제에서 자동 초기화)
- 제출 즉시 정답 공개(React 느낌의 애니메이션 오버레이)
- 정답 시: 축하 사운드 + 즉시 다음 문제(입력칸 자동 초기화)
- 스킵 버튼 활성화 문제 수정
- 1초 카운트다운 + 틱 사운드 유지
"""

import streamlit as st
import random, difflib, unicodedata, time
from typing import Dict, Tuple
from streamlit.components.v1 import html

# ---------------------- 호환 유틸 ----------------------
def safe_rerun():
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()

# ---------------------- 데이터 ----------------------
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

# ---------------------- 퍼지 매칭/초성 ----------------------
def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if ch.isalnum() or ord(ch) > 0x3130)
    return t.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

_CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
def chosung_hint(s: str) -> str:
    base = 0xAC00
    res = []
    for ch in s:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - base
            cho_idx = idx // 588
            res.append(_CHO[cho_idx])
        elif ch.isspace():
            res.append(" ")
        else:
            res.append(ch)
    return "".join(res).replace("  ", " ").replace(" ", " · ")

# ---------------------- 문제 선택 ----------------------
def pick_prompt(used: set) -> Tuple[str, str]:
    remain = [k for k in PROVERBS.keys() if k not in used]
    if not remain:
        used.clear()
        remain = list(PROVERBS.keys())
    prefix = random.choice(remain)
    return prefix, PROVERBS[prefix]

# ---------------------- 사운드/이펙트 ----------------------
def play_tick_sound(running: bool):
    if running:
        html(
            """
            <script>
            (function(){
              if (window._tickInterval) return;
              const AC = window.AudioContext || window.webkitAudioContext;
              const ctx = new AC();
              const resume = ()=>{ ctx.resume(); document.removeEventListener('click', resume); };
              document.addEventListener('click', resume, {once:true});
              function tick(){
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.type = 'square'; o.frequency.value = 1000;
                g.gain.setValueAtTime(0.0001, ctx.currentTime);
                g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.02);
                g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.08);
                o.connect(g); g.connect(ctx.destination);
                o.start(); o.stop(ctx.currentTime + 0.1);
              }
              window._tickInterval = setInterval(tick, 1000);
            })();
            </script>
            """,
            height=0,
        )
    else:
        html(
            """
            <script>
              if (window._tickInterval){
                clearInterval(window._tickInterval);
                window._tickInterval = null;
              }
            </script>
            """,
            height=0,
        )

def play_correct_sound():
    html(
        """
        <script>
        (function(){
          const AC = window.AudioContext || window.webkitAudioContext;
          const ctx = new AC();
          const now = ctx.currentTime;
          function beep(freq, t0, dur){
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.type = 'sine'; o.frequency.value = freq;
            g.gain.setValueAtTime(0.0001, now + t0);
            g.gain.exponentialRampToValueAtTime(0.35, now + t0 + 0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, now + t0 + dur);
            o.connect(g); g.connect(ctx.destination);
            o.start(now + t0); o.stop(now + t0 + dur + 0.03);
          }
          // 도-미-솔
          beep(523.25, 0.00, 0.12);
          beep(659.25, 0.12, 0.12);
          beep(783.99, 0.24, 0.18);
        })();
        </script>
        """,
        height=0,
    )

def flash_answer(text: str, success: bool):
    color = "#10b981" if success else "#ef4444"
    html(
        f"""
        <style>
          @keyframes pop {{
            0% {{ transform: scale(.9); opacity:.0; }}
            50% {{ transform: scale(1.03); opacity:1; }}
            100%{{ transform: scale(1.0); opacity:1; }}
          }}
        </style>
        <div id="ansflash" style="
            position:fixed; left:50%; top:12%;
            transform:translateX(-50%);
            background:{color}; color:white;
            padding:10px 18px; border-radius:12px;
            box-shadow:0 8px 24px rgba(0,0,0,.2);
            font-size:18px; font-weight:700;
            z-index:9999; animation: pop .25s ease-out;">
            {text}
        </div>
        <script>
          setTimeout(()=>{ const el = document.getElementById('ansflash'); if(el) el.remove(); }, 1200);
        </script>
        """,
        height=0,
    )

# ---------------------- 페이지/상태 ----------------------
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
ss = st.session_state
if "page" not in ss: ss.page = "home"          # "home" | "game"
if "started" not in ss: ss.started = False
if "score" not in ss: ss.score = 0
if "best" not in ss: ss.best = 0
if "used" not in ss: ss.used = set()
if "current" not in ss: ss.current = (None, None)
if "start_time" not in ss: ss.start_time = None
if "duration" not in ss: ss.duration = 90
if "threshold" not in ss: ss.threshold = 0.85
if "hint_used_total" not in ss: ss.hint_used_total = 0         # 전체 2회 제한
if "show_hint" not in ss: ss.show_hint = False                 # 현재 문제에 한해 표시
ANSWER_KEY = "answer_text"

# ---------------------- HOME ----------------------
if ss.page == "home":
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>제한 시간 안에 최대한 많이 맞혀보세요! 오타 조금은 괜찮아요.</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            st.subheader("게임 설정")
            ss.duration = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
            ss.threshold = st.slider("🎯 정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)

            if st.button("▶️ 게임 시작", use_container_width=True):
                ss.started = True
                ss.score = 0
                ss.hint_used_total = 0
                ss.used = set()
                ss.start_time = time.time()
                ss.current = pick_prompt(ss.used)
                ss.page = "game"
                ss.show_hint = False
                ss[ANSWER_KEY] = ""
                safe_rerun()

    st.caption("Tip: 첫 클릭 후 소리 활성화(브라우저 자동재생 정책).")

# ---------------------- GAME ----------------------
if ss.page == "game":
    # 1초 카운트다운 자동 갱신
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, key="__ticker__")

    # 중앙 레이아웃
    _, mid, _ = st.columns([1, 2, 1])
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

        # 틱
