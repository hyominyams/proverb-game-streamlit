# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Streamlit 속담 이어말하기 게임
- 1초 카운트다운 (st.autorefresh)
- 정답 시: 시각 효과 + 축하 사운드, 즉시 다음 문제, 입력란 자동 초기화
- '정답 보기' 대신 '힌트(초성)' 버튼
- 앞부분을 페이지 중앙에 크게 표기, 정답 입력은 작게
"""

import streamlit as st
import random
import difflib
import unicodedata
import time
from typing import Dict, Tuple
from streamlit.components.v1 import html

# ---------------------- 호환 유틸 ----------------------
def safe_rerun():
    """Streamlit 버전별 rerun 호환"""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

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

# 한글 초성 뽑기
_CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
_JUNG = ["ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"]
_JONG = [""] + ["ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]

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
            # 한글이 아니면 그대로(숫자/영문/기호 등)
            res.append(ch)
    # 단어 간 시각적 구분을 위해 공백을 ' · '로 살짝 표시
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
    # 1초마다 '틱' 소리
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
                g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.004);
                g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.06);
                o.connect(g); g.connect(ctx.destination);
                o.start(); o.stop(ctx.currentTime + 0.07);
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
    # 정답 시 한 번만 재생되는 짧은 축하음(간단한 3음)
    html(
        """
        <script>
        (function(){
          const AC = window.AudioContext || window.webkitAudioContext;
          const ctx = new AC();
          const now = ctx.currentTime;
          function beepAt(freq, t0, dur){
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.type = 'sine'; o.frequency.value = freq;
            g.gain.setValueAtTime(0.0001, now + t0);
            g.gain.exponentialRampToValueAtTime(0.3, now + t0 + 0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, now + t0 + dur);
            o.connect(g); g.connect(ctx.destination);
            o.start(now + t0); o.stop(now + t0 + dur + 0.02);
          }
          // 도-미-솔 간단한 아르페지오
          beepAt(523.25, 0.00, 0.12);
          beepAt(659.25, 0.12, 0.12);
          beepAt(783.99, 0.24, 0.18);
        })();
        </script>
        """,
        height=0,
    )

def confetti_effect():
    # 간단한 이모지 '폭죽' 이펙트 (CDN 없이 가벼운 표현)
    html(
        """
        <div id="confetti" style="position:fixed;inset:0;pointer-events:none;display:flex;justify-content:center;align-items:center;font-size:42px;opacity:0;transition:opacity .15s">🎉✨🎊</div>
        <script>
          const el = document.getElementById('confetti');
          el.style.opacity = 1;
          setTimeout(()=>{ el.style.opacity = 0; el.remove(); }, 700);
        </script>
        """,
        height=0,
    )

# ---------------------- 페이지 설정/상태 ----------------------
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")

ss = st.session_state
if "page" not in ss: ss.page = "home"      # "home" | "game"
if "started" not in ss: ss.started = False
if "score" not in ss: ss.score = 0
if "best" not in ss: ss.best = 0
if "used" not in ss: ss.used = set()
if "current" not in ss: ss.current = (None, None)
if "start_time" not in ss: ss.start_time = None
if "duration" not in ss: ss.duration = 60
if "threshold" not in ss: ss.threshold = 0.85
if "show_hint" not in ss: ss.show_hint = False
ANSWER_KEY = "answer_text"  # 입력란 세션 키

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
                ss.used = set()
                ss.start_time = time.time()
                ss.current = pick_prompt(ss.used)
                ss.page = "game"
                ss.show_hint = False
                ss[ANSWER_KEY] = ""
                safe_rerun()

    st.caption("Tip: 브라우저 자동재생 차단 시, 시작 버튼 클릭 후 소리가 활성화됩니다.")

# ---------------------- GAME ----------------------
if ss.page == "game":
    # 1초마다 새로고침(카운트다운)
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, key="__ticker__")

    # 중앙 좁은 영역 구성
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # 남은 시간 계산
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

        st.markdown("<hr>", unsafe_allow_html=True)

        # 문제(앞부분) 크게 중앙 표시
        prefix, answer = ss.current
        st.markdown(
            f"""
            <div style="text-align:center; font-size: 2rem; font-weight: 700; padding: 12px 8px;">
              {prefix if prefix else '-'}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 힌트 토글 & 버튼
        hint_col, _ = st.columns([1, 1])
        if hint_col.button("💡 힌트(초성) 보기/숨기기", use_container_width=True):
            ss.show_hint = not ss.show_hint
        if ss.show_hint:
            st.info(f"힌트: **{chosung_hint(answer)}**")

        # 입력 영역 (상대적으로 작게)
        st.write("")  # 간격
        st.markdown("<div style='text-align:center;'>정답을 입력해 보세요</div>", unsafe_allow_html=True)
        user_answer = st.text_input(
            "정답",
            key=ANSWER_KEY,
            label_visibility="collapsed",
            placeholder="예) 밤말은 쥐가 듣는다",
            help="오타 조금은 괜찮아요!",
        )

        colA, colB = st.columns([1, 1])
        submit = colA.button("제출", use_container_width=True, disabled=not ss.started)
        skip = colB.button("스킵", use_container_width=True, disabled=not ss.started)

        if submit and ss.started:
            sim = fuzzy_match(user_answer, answer)
            if sim >= ss.threshold:
                st.success(f"정답! ✅ (유사도 {sim*100:.1f}%)")
                st.balloons()
                confetti_effect()
                play_correct_sound()
                ss.score += 1
                ss.best = max(ss.best, ss.score)
                ss.used.add(prefix)
                ss.current = pick_prompt(ss.used)
                # 입력란 자동 초기화
                ss[ANSWER_KEY] = ""
                ss.show_hint = False
                safe_rerun()
            else:
                st.warning(f"아쉽네요 ❌ (유사도 {sim*100:.1f}%). 다시 시도해 보세요!")

        if skip and ss.started:
            ss.used.add(prefix)
            ss.current = pick_prompt(ss.used)
            ss[ANSWER_KEY] = ""
            ss.show_hint = False
            st.info("문제를 건너뛰었습니다.")
            safe_rerun()

        # 시간 종료
        if ss.started and remaining == 0:
            st.warning("⏰ 시간이 종료되었습니다!")
            ss.started = False
            ss.page = "home"

        st.write("")
        if st.button("🏠 첫 화면으로", use_container_width=True):
            ss.page = "home"
            safe_rerun()
