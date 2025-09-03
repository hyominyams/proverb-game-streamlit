# -*- coding: utf-8 -*-
import time, random, difflib, unicodedata
from typing import Dict, Tuple
import streamlit as st
from streamlit.components.v1 import html

# ====================== 데이터 ======================
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

# ====================== 유틸 ======================
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

def pick_prompt(used:set) -> Tuple[str,str]:
    remain = [k for k in PROVERBS if k not in used]
    if not remain:
        used.clear(); remain = list(PROVERBS.keys())
    p = random.choice(remain)
    return p, PROVERBS[p]

# ====================== 사운드/이펙트 ======================
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
        html("""<script> if(window._tickInterval){clearInterval(window._tickInterval);window._tickInterval=null;} </script>""", height=0)

def play_correct_sound_and_confetti():
    st.balloons()
    html("""
    <div id="confetti" style="
      position:fixed; left:50%; bottom:-20px; transform:translateX(-50%);
      font-size:40px; opacity:0; transition: all .6s ease-out; z-index:9999;">🎉🎊✨</div>
    <script>
      (function(){
        const AC = window.AudioContext || window.webkitAudioContext;
        const ctx = new AC(); const t = ctx.currentTime;
        function beep(f, d, du){
          const o=ctx.createOscillator(), g=ctx.createGain();
          o.type='triangle'; o.frequency.value=f;
          g.gain.setValueAtTime(0.0001, t+d);
          g.gain.exponentialRampToValueAtTime(0.35, t+d+0.03);
          g.gain.exponentialRampToValueAtTime(0.0001, t+d+du);
          o.connect(g); g.connect(ctx.destination);
          o.start(t+d); o.stop(t+d+du+0.03);
        }
        // 간단한 빵파레: 도-솔-높은 도
        beep(523.25,0.00,0.12); beep(783.99,0.12,0.12); beep(1046.5,0.24,0.18);
        const el = document.getElementById('confetti');
        setTimeout(()=>{ el.style.opacity=1; el.style.bottom='40%'; }, 10);
        setTimeout(()=>{ el.style.opacity=0; el.remove(); }, 900);
      })();
    </script>
    """, height=0)

def flash_answer_overlay(text:str, success:bool):
    color = "#10b981" if success else "#ef4444"
    html(f"""
    <style>
      @keyframes pop {{
        0%  {{ transform: scale(.9); opacity:.0; }}
        50% {{ transform: scale(1.03); opacity:1; }}
        100% {{ transform: scale(1.0); opacity:1; }}
      }}
    </style>
    <div id="ansflash" style="
      position:fixed; left:50%; top:12%; transform:translateX(-50%);
      background:{color}; color:white; padding:10px 18px; border-radius:12px;
      box-shadow:0 8px 24px rgba(0,0,0,.2); font-size:18px; font-weight:700;
      z-index:9999; animation: pop .25s ease-out;">{text}</div>
    <script>
      setTimeout(() => {{
        const el = document.getElementById('ansflash');
        if (el) el.remove();
      }}, 1200);
    </script>
    """, height=0)

def render_stats(score:int, end_ts:float, hints:int):
    # 큰 숫자(2.2rem) + 카드 UI
    now_rem = max(0, int(round(end_ts - time.time()))) if end_ts else 0
    html(f"""
    <div class="stats">
      <div class="card"><div class="label">점수</div><div class="value">{score}</div></div>
      <div class="card"><div class="label">남은 시간</div><div class="value"><span id="timer_div">{now_rem}</span>s</div></div>
      <div class="card"><div class="label">힌트 사용</div><div class="value">{hints}/2</div></div>
    </div>
    <style>
      .stats {{ display:flex; gap:12px; justify-content:center; margin:4px 0 6px; }}
      .card {{ padding:12px 16px; border:1px solid #e9ecef; border-radius:12px;
               min-width:160px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.04); }}
      .card .label {{ font-size:.95rem; color:#666; margin-bottom:6px; }}
      .card .value {{ font-size:2.2rem; font-weight:800; line-height:1.1; }}
      #timer_div {{ font-size:2.2rem; }}
    </style>
    <script>
      (function(){{
        const end = {int(end_ts*1000) if end_ts else 0};
        function update(){{
          if (!end) return;
          const now = Date.now();
          let rem = Math.max(0, Math.round((end - now)/1000));
          const el = document.getElementById('timer_div');
          if (el) el.textContent = rem.toString();
        }}
        update();
        if (!window.__timerInterval) {{
          window.__timerInterval = setInterval(update, 1000);
        }}
      }})();
    </script>
    """, height=110)

# ====================== 상태 ======================
st.set_page_config(page_title="속담 이어말하기", page_icon="🧩", layout="centered")
ss = st.session_state
ANSWER_KEY = "answer_box"

defaults = dict(
    page="home", started=False, score=0, best=0, used=set(), current=(None,None),
    duration=90, threshold=0.85, hint_used_total=0, show_hint=False,
    end_time=None, reveal_text="", reveal_success=False, just_correct=False
)
for k,v in defaults.items():
    if k not in ss: ss[k]=v

# 전역 스타일(입력칸 크게/넓게)
st.markdown("""
<style>
/* 메인 컨테이너 상단 여백 살짝 줄여 문제 박스 더 위로 */
.block-container { padding-top: 0.8rem; }
/* 텍스트 입력 인풋 넓게 + 큰 글자 + 패딩 */
.stTextInput input { font-size: 1.25rem; padding: 14px 12px; }
</style>
""", unsafe_allow_html=True)

# ====================== 콜백 ======================
def start_game():
    ss.started = True
    ss.score = 0
    ss.used = set()
    ss.hint_used_total = 0
    ss.current = pick_prompt(ss.used)
    ss.end_time = time.time() + ss.duration
    ss.page = "game"
    ss.show_hint = False
    ss[ANSWER_KEY] = ""

def use_hint():
    if ss.hint_used_total < 2 and not ss.show_hint and ss.started:
        ss.hint_used_total += 1
        ss.show_hint = True

def submit_answer():
    if not ss.started or not ss.current[0]:
        return
    prefix, answer = ss.current
    user = ss.get(ANSWER_KEY, "")
    sim = fuzzy_match(user, answer)
    is_correct = (sim >= ss.threshold)
    ss.reveal_text = f"정답: {answer}"
    ss.reveal_success = is_correct
    if is_correct:
        ss.score += 1
        ss.best = max(ss.best, ss.score)
        ss.used.add(prefix)
        ss.current = pick_prompt(ss.used)
        ss.show_hint = False
        ss[ANSWER_KEY] = ""
        ss.just_correct = True
    else:
        ss.just_correct = False

def skip_question():
    if not ss.started: return
    prefix, _ = ss.current
    ss.used.add(prefix)
    ss.current = pick_prompt(ss.used)
    ss.show_hint = False
    ss[ANSWER_KEY] = ""
    ss.reveal_text = ""  # 스킵 시 정답 미공개

def go_home():
    ss.page = "home"
    ss.started = False
    ss.reveal_text = ""
    play_tick_sound(False)

# ====================== HOME ======================
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

# ====================== GAME ======================
if ss.page == "game":
    # 서버 1초 주기 동기화
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, key="__ticker__")

    # 문제 보장
    if not ss.current or not ss.current[0]:
        ss.current = pick_prompt(ss.used)

    # 타임아웃 판정
    remaining_server = max(0, int(round(ss.end_time - time.time()))) if ss.end_time else 0
    if ss.started and remaining_server == 0:
        play_tick_sound(False)
        st.markdown("### ⏰ TIME OUT!")
        st.success(f"최종 점수: {ss.score}점 / 힌트 사용 {ss.hint_used_total}/2")
        col = st.columns([1,2,1])[1]
        with col:
            st.button("다시 시작", use_container_width=True, on_click=start_game)
            st.button("🏠 첫 화면", use_container_width=True, on_click=go_home)
    else:
        # 1) 상단 상태 카드
        render_stats(ss.score, ss.end_time or time.time(), ss.hint_used_total)

        # 틱 사운드
        play_tick_sound(ss.started and remaining_server > 0)

        # 2) 문제 박스 (상태 카드 바로 아래, 더 위쪽 / '문제' 라벨 제거)
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            prefix, answer = ss.current
            st.markdown(f"""
            <div style="border:1px solid #e9ecef; border-radius:14px; padding:14px 18px;
                        box-shadow:0 2px 8px rgba(0,0,0,.04); margin-top:2px;">
              <div style="text-align:center; font-size:2.3rem; font-weight:800;">{prefix}</div>
            """, unsafe_allow_html=True)
            # 힌트 버튼 + 힌트 표시
            st.button(f"💡 힌트(초성) 보기 (남은 {max(0,2-ss.hint_used_total)}/2)",
                      use_container_width=True,
                      disabled=(not ss.started) or (ss.hint_used_total>=2) or ss.show_hint or remaining_server==0,
                      on_click=use_hint)
            if ss.show_hint:
                st.info(f"힌트: **{chosung_hint(answer)}**")
            st.markdown("</div>", unsafe_allow_html=True)

        # 3) 정답 입력/버튼 박스 (더 하단)
        _, mid2, _ = st.columns([1, 2, 1])
        with mid2:
            st.markdown("""
            <div style="border:1px solid #e9ecef; border-radius:14px; padding:16px 18px;
                        box-shadow:0 2px 8px rgba(0,0,0,.04); margin-top:12px;">
              <div style="text-align:center; font-weight:700; margin-bottom:8px">정답을 입력한 뒤 Enter 키를 누르세요</div>
            """, unsafe_allow_html=True)

            # ✅ Enter로 제출: on_change=submit_answer
            st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed",
                          placeholder="예) 밤말은 쥐가 듣는다", help="오타 조금은 괜찮아요!",
                          on_change=submit_answer)

            colB, colC = st.columns([1,1])
            colB.button("스킵",  use_container_width=True, disabled=(not ss.started or remaining_server==0),
                        on_click=skip_question)
            colC.button("🏠 첫 화면", use_container_width=True, on_click=go_home)

            st.markdown("</div>", unsafe_allow_html=True)

        # 4) 제출 직후 정답 공개 / 축하이펙트
        if ss.reveal_text:
            flash_answer_overlay(ss.reveal_text, ss.reveal_success)
            ss.reveal_text = ""
        if ss.just_correct:
            play_correct_sound_and_confetti()
            ss.just_correct = False
