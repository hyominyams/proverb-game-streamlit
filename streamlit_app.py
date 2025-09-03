# -*- coding: utf-8 -*-
import time, random, difflib, unicodedata
from typing import Dict, Tuple
import streamlit as st
from streamlit.components.v1 import html

# ---------------------- 호환 rerun ----------------------
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

# ---------------------- 유틸 ----------------------
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

# ---------------------- 효과음/이펙트 ----------------------
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
    # 짧은 빵파레 + 아래에서 올라오는 이펙트 + 풍선
    st.balloons()
    html("""
    <div id="confetti" style="
      position:fixed; left:50%; bottom:-20px; transform:translateX(-50%);
      font-size:40px; opacity:0; transition: all .6s ease-out; z-index:9999;">🎉🎊✨</div>
    <script>
      (function(){
        const AC = window.AudioContext || window.webkitAudioContext;
        const ctx = new AC();
        const t = ctx.currentTime;
        function beep(f, d, du){
          const o=ctx.createOscillator(), g=ctx.createGain();
          o.type='triangle'; o.frequency.value=f;
          g.gain.setValueAtTime(0.0001, t+d);
          g.gain.exponentialRampToValueAtTime(0.35, t+d+0.03);
          g.gain.exponentialRampToValueAtTime(0.0001, t+d+du);
          o.connect(g); g.connect(ctx.destination);
          o.start(t+d); o.stop(t+d+du+0.03);
        }
        // 간단한 파레드: 도-솔-도'
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

def render_timer(end_ts: float):
    # 브라우저에서 1초마다 표시 갱신(서버 지연 체감 최소화)
    now_rem = max(0, int(round(end_ts - time.time())))
    html(f"""
    <div style="text-align:center; font-weight:700" id="timer_div">{now_rem}s</div>
    <script>
      (function(){{
        const end = {int(end_ts*1000)};
        function update(){{
          const now = Date.now();
          let rem = Math.max(0, Math.round((end - now)/1000));
          const el = document.getElementById('timer_div');
          if (el) el.textContent = rem + 's';
        }}
        update();
        if (!window.__timerInterval) {{
          window.__timerInterval = setInterval(update, 1000);
        }}
      }})();
    </script>
    """, height=30)

# ---------------------- 상태 ----------------------
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

# ---------------------- 콜백 ----------------------
def start_game():
    ss.started = True
    ss.score = 0
    ss.used = set()
    ss.hint_used_total = 0
    ss.current = pick_prompt(ss.used)
    ss.end_time = time.time() + ss.duration
    ss.page = "game"
    ss.show_hint = False
    ss[ANSWER_KEY] = ""  # 콜백이므로 안전
    safe_rerun()

def use_hint():
    if ss.hint_used_total < 2 and not ss.show_hint and ss.started:
        ss.hint_used_total += 1
        ss.show_hint = True
        safe_rerun()

def submit_answer():
    # 현재 문제와 유저 입력 획득
    prefix, answer = ss.current
    user = ss.get(ANSWER_KEY, "")
    sim = fuzzy_match(user, answer)
    is_correct = (sim >= ss.threshold)

    # 정답 공개(오버레이)
    ss.reveal_text = f"정답: {answer}"
    ss.reveal_success = is_correct

    if is_correct:
        ss.score += 1
        ss.best = max(ss.best, ss.score)
        ss.used.add(prefix)
        ss.current = pick_prompt(ss.used)
        ss.show_hint = False
        ss[ANSWER_KEY] = ""      # 콜백 내에서 안전
        ss.just_correct = True   # 다음 렌더에서 이펙트+사운드
    else:
        ss.just_correct = False

    safe_rerun()

def skip_question():
    if not ss.started: return
    prefix, _ = ss.current
    ss.used.add(prefix)
    ss.current = pick_prompt(ss.used)
    ss.show_hint = False
    ss[ANSWER_KEY] = ""          # 콜백 내에서 안전
    ss.reveal_text = ""          # 스킵 시 정답 공개 X (원하면 켜기)
    safe_rerun()

def go_home():
    ss.page = "home"
    ss.started = False
    safe_rerun()

# ---------------------- HOME ----------------------
if ss.page == "home":
    st.markdown("<h1 style='text-align:center'>🧩 속담 이어말하기 게임</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>제한 시간 안에 많이 맞혀보세요! (오타 일부 허용)</p>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1,2,1])
    with mid:
        st.subheader("게임 설정")
        ss.duration  = st.slider("⏱️ 제한 시간(초)", 30, 300, 90, step=10)
        ss.threshold = st.slider("🎯 정답 인정 임계값", 0.6, 0.95, 0.85, step=0.01)
        st.button("▶️ 게임 시작", use_container_width=True, on_click=start_game)
    st.caption("※ 브라우저 자동재생 정책상 소리는 첫 클릭 이후 활성화됩니다.")

# ---------------------- GAME ----------------------
if ss.page == "game":
    # 1초마다 서버도 재실행(종료 판정용). 너무 튀면 1000→1500으로 조절
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, key="__ticker__")

    # 문제 보장
    if not ss.current or not ss.current[0]:
        ss.current = pick_prompt(ss.used)

    # 중앙 상단 블록
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        # 상단 메트릭 + 타이머
        left, center, right = st.columns([1,1,1])
        with left:  st.metric("점수", ss.score)
        with center:
            st.markdown("<div style='text-align:center'>남은 시간</div>", unsafe_allow_html=True)
            if ss.end_time is None: ss.end_time = time.time() + ss.duration
            render_timer(ss.end_time)
        with right: st.metric("힌트 사용", f"{ss.hint_used_total}/2")

        # 틱 사운드 (클라이언트 자율)
        remaining_server = max(0, int(round(ss.end_time - time.time())))
        play_tick_sound(ss.started and remaining_server > 0)

        # 힌트 버튼(정중앙에 가깝게)
        st.button(f"💡 힌트(초성) 보기 (남은 {max(0,2-ss.hint_used_total)}/2)",
                  use_container_width=True,
                  disabled=(not ss.started) or (ss.hint_used_total>=2) or ss.show_hint or remaining_server==0,
                  on_click=use_hint)

        # ====== 문제/입력칸 (정중앙 상단) ======
        prefix, answer = ss.current
        st.markdown(
            f"<div style='text-align:center; font-size:2.2rem; font-weight:800; margin-top:8px'>{prefix}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='text-align:center; margin-top:6px'>정답을 입력해 보세요</div>", unsafe_allow_html=True)
        st.text_input("정답", key=ANSWER_KEY, label_visibility="collapsed",
                      placeholder="예) 밤말은 쥐가 듣는다", help="오타 조금은 괜찮아요!")

        colA, colB, colC = st.columns([1,1,1])
        colA.button("제출", use_container_width=True, disabled=(not ss.started or remaining_server==0),
                    on_click=submit_answer)
        colB.button("스킵",  use_container_width=True, disabled=(not ss.started or remaining_server==0),
                    on_click=skip_question)
        colC.button("🏠 첫 화면", use_container_width=True, on_click=go_home)

        # ====== 구분선 (문제영역 아래) ======
        st.markdown("<hr>", unsafe_allow_html=True)

        # 정답 공개 오버레이(다음 렌더에서 표시하도록 플래그 기반)
        if ss.reveal_text:
            flash_answer_overlay(ss.reveal_text, ss.reveal_success)
            # 한 번만 표시
            ss.reveal_text = ""

        # 정답 맞춘 직후 이펙트/사운드
        if ss.just_correct:
            play_correct_sound_and_confetti()
            ss.just_correct = False

        # 서버 측 시간 종료 → 자동 종료
        if ss.started and remaining_server == 0:
            st.warning("⏰ 시간이 종료되었습니다! 첫 화면으로 돌아갑니다.")
            ss.started = False
            ss.page = "home"

