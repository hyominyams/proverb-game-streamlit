# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Streamlit 속담 이어말하기 게임
- GPT가 속담 앞부분을 제시하면 사용자가 뒷부분을 입력
- 약간의 오타를 허용하는 퍼지 채점
"""

import streamlit as st
import random
import difflib
import unicodedata
import time

# ---------------------- 속담 데이터 ----------------------
PROVERBS = {
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
}

# ---------------------- 유틸 함수 ----------------------
def normalize(text: str) -> str:
    """한글 비교를 위한 정규화"""
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if ch.isalnum() or ord(ch) > 0x3130)
    return t.strip().lower()

def fuzzy_match(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()

# ---------------------- Streamlit UI ----------------------
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
st.title("🧩 속담 이어말하기 게임")

# 세션 스테이트 초기화
if "started" not in st.session_state:
    st.session_state.started = False
if "score" not in st.session_state:
    st.session_state.score = 0
if "current" not in st.session_state:
    st.session_state.current = None
if "used" not in st.session_state:
    st.session_state.used = set()
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    game_seconds = st.slider("제한 시간(초)", 30, 180, 60, step=10)
    threshold = st.slider("정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)

# 게임 시작 버튼
if st.button("▶️ 게임 시작"):
    st.session_state.started = True
    st.session_state.score = 0
    st.session_state.used = set()
    st.session_state.start_time = time.time()
    st.session_state.current = random.choice(list(PROVERBS.items()))

# 진행 중일 때
if st.session_state.started and st.session_state.current:
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, game_seconds - int(elapsed))

    st.metric("점수", st.session_state.score)
    st.metric("남은 시간", f"{remaining}초")

    prefix, answer = st.session_state.current
    st.write(f"👉 **앞부분:** {prefix}")

    user_answer = st.text_input("뒷부분을 입력하세요")

    if st.button("제출"):
        sim = fuzzy_match(user_answer, answer)
        if sim >= threshold:
            st.success(f"정답! ✅ (유사도 {sim*100:.1f}%)")
            st.session_state.score += 1
            st.balloons()
            # 다음 문제
            unused = [k for k in PROVERBS.items() if k not in st.session_state.used]
            if unused:
                st.session_state.current = random.choice(unused)
            else:
                st.session_state.current = random.choice(list(PROVERBS.items()))
        else:
            st.warning(f"틀렸습니다 ❌ (유사도 {sim*100:.1f}%)")

    if remaining == 0:
        st.warning("⏰ 시간이 종료되었습니다!")
        st.session_state.started = False
