# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Streamlit 속담 이어말하기 게임 (카운트다운/즉시 다음 문제/중앙 배치/틱 소리)
- 1초 카운트다운: st.autorefresh 이용
- 정답이면 즉시 다음 문제
- 첫 화면 → 시작 → 중앙 게임 화면
- 틱 소리: WebAudio (사용자 클릭 이후 자동 재생)
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

# ---------------------- 유틸 ----------------------
def normalize(text: str) -> str:
    """한글 비교를 위한 정규화(공백/기호 제거, NFKC, 소문자)."""
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if ch.isalnum() or ord(ch) > 0x3130)
    return t.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def pick_prompt(used: set) -> Tuple[str, str]:
    remain = [k for k in PROVERBS.keys() if k not in used]
    if not remain:
        used.clear()
        remain = list(PROVERBS.keys())
    prefix = random.choice(remain)
    return prefix, PROVERBS[prefix]

def play_tick_sound(running: bool):
    """
    1초마다 짧은 '틱' 소리를 재생.
    - 첫 사용자 상호작용(클릭) 이후 자동재생 허용을 위해 AudioContext.resume 연결
    - 게임 종료 시 interval 해제
    """
    if running:
        html(
            """
            <script>
            (function(){
              if (window._tickInterval) return;  // 이미 실행 중이면 중복 방지
              const AC = window.AudioContext || window.webkitAudioContext;
              const ctx = new AC();
              const resume = ()=>{ ctx.resume(); document.removeEventListener('click', resume); };
              document.addEventListener('click', resume, {once:true});
              function tick(){
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.type = 'square';
                o.frequency.value = 1000;
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

# ---------------------- 페이지 설정 ----------------------
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")

# 세션 스테이트
ss = st.session_state
if "page" not in ss:
    ss.page = "home"  # "home" | "game"
if "started" not in ss:
    ss.started = False
if "score" not in ss:
    ss.score = 0
if "best" not in ss:
    ss.best = 0
if "used" not in ss:
    ss.used = set()
if "current" not in ss:
    ss.current = (None, None)
if "start_time" not in ss:
    ss.start_time = None
if "duration" not in ss:
    ss.duration = 60
if "threshold" not in ss:
    ss.threshold = 0.85

# ---------------------- HOME 화면 ----------------------
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
                safe_rerun()

    st.caption("Tip: 브라우저 보안정책에 따라 소리 자동재생이 막힐 수 있어요. "
               "시작 버튼을 누르면 활성화됩니다.")

# ---------------------- GAME 화면 ----------------------
if ss.page == "game":
    # 1초마다 자동 리프레시(카운트다운)
    if hasattr(st, "autorefresh"):  # Streamlit >= 1.28
        st.autorefresh(interval=1000, key="__ticker__")

    # 중앙 레이아웃
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h2 style='text-align:center'>게임 진행</h2>", unsafe_allow_html=True)

        # 카운트다운
        remaining = 0
        if ss.started and ss.start_time:
            elapsed = int(time.time() - ss.start_time)
            remaining = max(0, ss.duration - elapsed)

        info1, info2, info3 = st.columns(3)
        info1.metric("점수", ss.score)
        info2.metric("최고 기록", ss.best)
        info3.metric("남은 시간", f"{remaining}s")

        # 틱 사운드 (남은 시간 있을 때만)
        play_tick_sound(ss.started and remaining > 0)

        st.divider()

        # 문제 카드
        prefix, answer = ss.current
        with st.container(border=True):
            st.markdown(f"**앞부분:** {prefix if prefix else '-'}")

            user_answer = st.text_input("뒷부분을 입력하세요", key="__answer__", label_visibility="visible")

            colA, colB, colC = st.columns([1, 1, 1])
            submit = colA.button("제출", use_container_width=True, disabled=not ss.started)
            skip = colB.button("스킵", use_container_width=True, disabled=not ss.started)
            giveup = colC.button("정답 보기", use_container_width=True, disabled=not ss.started)

            # 정답 체크
            if submit and ss.started:
                sim = fuzzy_match(user_answer, answer)
                if sim >= ss.threshold:
                    st.success(f"정답! ✅ (유사도 {sim*100:.1f}%)")
                    ss.score += 1
                    ss.best = max(ss.best, ss.score)
                    ss.used.add(prefix)
                    ss.current = pick_prompt(ss.used)   # 즉시 다음 문제
                    safe_rerun()
                else:
                    st.warning(f"틀렸어요 ❌ (유사도 {sim*100:.1f}%). 다시 시도해 보세요!")

            if skip and ss.started:
                ss.used.add(prefix)
                ss.current = pick_prompt(ss.used)
                st.info("문제를 건너뛰었습니다.")
                safe_rerun()

            if giveup and ss.started:
                st.info(f"정답: **{answer}**")

        # 시간 종료 처리
        if ss.started and remaining == 0:
            st.warning("⏰ 시간이 종료되었습니다!")
            ss.started = False
            ss.page = "home"

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 첫 화면으로", use_container_width=True):
            ss.page = "home"
            safe_rerun()
