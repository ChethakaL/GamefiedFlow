# app.py
import os
import time
from typing import Optional

import streamlit as st

# --- .env support (put GEMINI_API_KEY in a .env next to app.py) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ================= Gemini config =================
GEMINI_DEFAULT_MODEL = "gemini-1.5-flash"   # you can switch to "gemini-1.5-flash-8b" if you like

# Free-tier friendly: only call Gemini when user presses "Get a hint"
# If you want auto coaching lines after answers, set this True
AI_COACH_ENABLED = False

# Cooldown so the free tier (RPM limit) doesn't 429
HINT_COOLDOWN_SEC = 30

# Built-in fallback hints (shown if Gemini throttles or isn't configured)
PREWRITTEN_HINTS = {
    1: "Think of apps that recommend or autocomplete.",
    2: "Add audience, tone, and output format.",
    3: "Pick one short task and try it.",
}

def configure_gemini():
    import google.generativeai as genai
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.session_state["gemini_ready"] = True
        except Exception as e:
            st.session_state["gemini_ready"] = False
            st.session_state["gemini_error"] = str(e)
    else:
        st.session_state["gemini_ready"] = False


def gemini_reply(prompt: str, temp: float = 0.6, cache_key: Optional[str] = None) -> str:
    """Call Gemini with a small per-session cache + cooldown + graceful 429 fallback."""
    if "gemini_cache" not in st.session_state:
        st.session_state.gemini_cache = {}

    key = cache_key or prompt
    if key in st.session_state.gemini_cache:
        return st.session_state.gemini_cache[key]

    if not st.session_state.get("gemini_ready"):
        return "(Hint unavailable: Gemini key not configured.)"

    # Cooldown
    now = time.time()
    next_ok = st.session_state.get("next_hint_ok_ts", 0)
    if now < next_ok:
        wait = int(next_ok - now)
        return f"(Cooling down {wait}s to respect free-tier limits…)"

    try:
        import google.generativeai as genai
        model_name = st.session_state.get("gemini_model", GEMINI_DEFAULT_MODEL)
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": temp, "max_output_tokens": 200}
        )
        text = (resp.text or "").strip() or "(No response from Gemini.)"
        st.session_state["next_hint_ok_ts"] = now + HINT_COOLDOWN_SEC
    except Exception as e:
        msg = str(e)
        if "429" in msg or "rate" in msg.lower():
            st.session_state["next_hint_ok_ts"] = now + HINT_COOLDOWN_SEC
            text = "(Free-tier limit hit; showing a built-in hint.)"
        else:
            text = f"(Gemini error: {e})"

    st.session_state.gemini_cache[key] = text
    return text

def current_hint_prompt() -> str:
    m = st.session_state.module
    if m in (0, 1):
        return "Give one short hint (<=20 words) to help a beginner name an everyday example of AI they use."
    if m == 2:
        return "Give one short hint (<=20 words) on improving a prompt with audience, tone, and output format."
    if m == 3:
        return "Give one short hint (<=20 words) for choosing a quick hands-on AI exercise and completing it."
    return "Give a concise study hint (<=20 words) for learning basic AI concepts."

def fallback_hint_for_current_module() -> str:
    m = max(1, min(3, st.session_state.module or 1))
    return PREWRITTEN_HINTS.get(m, "Keep it short and specific.")

# ================= Streamlit app =================
st.set_page_config(page_title="AI Starter Quest (Gemini Demo)", page_icon="🎓", layout="centered")

def init_state():
    st.session_state.setdefault("progress", 0)           # 0..100
    st.session_state.setdefault("badges", [])            # list[str]
    st.session_state.setdefault("module", 0)             # 0=welcome; 1..3 modules
    st.session_state.setdefault("messages", [])          # chat history
    st.session_state.setdefault("quiz_correct", 0)
    st.session_state.setdefault("email_captured", False)
    st.session_state.setdefault("gemini_ready", False)
    st.session_state.setdefault("gemini_model", GEMINI_DEFAULT_MODEL)

init_state()
configure_gemini()

# Sidebar (status only)
st.sidebar.header("Tutor (Gemini)")
if st.session_state.get("gemini_ready"):
    st.sidebar.success(f"Gemini ready ({st.session_state['gemini_model']})")
else:
    st.sidebar.info("Hints/coach optional. Add GEMINI_API_KEY in a .env to enable.")
if st.sidebar.button("Reset demo"):
    for k in ["progress","badges","module","messages","quiz_correct","email_captured","gemini_cache","next_hint_ok_ts"]:
        st.session_state.pop(k, None)
    st.rerun()

# Header
col1, col2 = st.columns([1,1])
with col1:
    st.title("🎓 AI Starter Quest")
    st.caption("Gamified learning + AI tutor (Gemini)")

with col2:
    st.write("**Progress**")
    p = st.session_state.progress
    st.progress(p/100 if p > 1 else p)
    st.write("**Badges**")
    st.write(" • ".join(st.session_state.badges) if st.session_state.badges else "_No badges yet_")

st.divider()

# Helpers
def say(role, text): st.chat_message(role).write(text)
def badge(name, emoji):
    label = f"{emoji} {name}"
    if label not in st.session_state.badges:
        st.session_state.badges.append(label)
def progress_to(p): st.session_state.progress = max(st.session_state.progress, p)

# Seed message
if not st.session_state.messages:
    st.session_state.messages = [
        {"role":"assistant","content":"Welcome! Type **begin** to start your AI journey. You'll complete 3 quick modules, earn badges, and preview your Report Card. Locked Level requires enrollment."}
    ]

# Render history
for m in st.session_state.messages:
    say(m["role"], m["content"])

# Hints: only after Module 1 begins
if st.session_state.module >= 1 and st.button("💡 Get a hint"):
    hint = gemini_reply(current_hint_prompt(), temp=0.7, cache_key=f"hint_m{st.session_state.module}")
    if hint.startswith("("):  # throttled / not configured / cooling down
        hint = fallback_hint_for_current_module() + " " + hint
    st.session_state.messages.append({"role":"assistant","content": f"**Hint:** {hint}"})
    st.rerun()

# ---------- Modules ----------
def render_module_1(user_text: str):
    txt = user_text.strip().lower()

    # Friendly greetings before start
    if txt in {"hi","hello","hey","yo","hola","help","start"}:
        return "Hi! 👋 Type **begin** to start Module 1."

    if txt == "begin":
        progress_to(20); badge("Concept Spark", "🏅")
        return ("### Module 1: What is AI?\n"
                "AI helps computers perform tasks like pattern recognition, prediction, and content generation.\n\n"
                "**Checkpoint:** Name one everyday example of AI you've used or seen.")
    elif any(k in txt for k in ["netflix","spotify","recommend","maps","autocorrect","autocomplete","youtube"]):
        progress_to(40)
        if AI_COACH_ENABLED and st.session_state.get("gemini_ready"):
            coach = gemini_reply(
                "Explain in one friendly sentence why recommendations (e.g., Netflix) are an example of AI, for a non-technical learner.",
                temp=0.4
            )
            st.session_state.messages.append({"role":"assistant","content": f"**Tutor:** {coach}"})
        return ("Nice! ✅ Recommendation engines (like Netflix/Spotify) are classic AI.\n\n"
                "**Mini-Quiz:** Which statement is MOST accurate?\n"
                "A) AI is one algorithm.\n"
                "B) AI is a field with many methods, such as machine learning.\n"
                "C) AI is magic.\n\n"
                "_Reply with A, B, or C._")
    elif txt.upper() in ["A","B","C"]:
        if txt.upper() == "B":
            st.session_state.quiz_correct += 1
            if AI_COACH_ENABLED and st.session_state.get("gemini_ready"):
                fb = gemini_reply(
                    "In one sentence, praise a learner for selecting option B (AI is a field) and add a tiny follow-up tip.",
                    temp=0.3
                )
                st.session_state.messages.append({"role":"assistant","content": f"**Tutor:** {fb}"})
            msg = "Correct! 🎉"
        else:
            if AI_COACH_ENABLED and st.session_state.get("gemini_ready"):
                tip = gemini_reply(
                    "In one sentence, gently correct a learner who picked A or C and say why B is best, in plain English.",
                    temp=0.3
                )
                st.session_state.messages.append({"role":"assistant","content": f"**Tutor:** {tip}"})
            msg = "Good try — the best answer is **B**."
        progress_to(50); st.session_state.module = 2
        return msg + "\n\n**Progress saved.** Moving to **Module 2: Prompting Basics**.\nType anything to continue."
    else:
        return "Type **begin** to start the course, or say something like `Netflix recommendations` for the checkpoint."

def render_module_2(user_text: str):
    if st.session_state.progress < 60:
        progress_to(60); badge("Prompt Explorer", "🔎")
        return ("### Module 2: Prompting Basics\n"
                "Good prompts are **clear**, **contextual**, and **goal-oriented**.\n\n"
                "**Task:** Rewrite this weak prompt to be specific.\n"
                "_Weak_: `Write marketing ideas.`\n"
                "Include audience, tone, and format.")
    else:
        attempt = user_text.strip()
        if attempt and attempt.upper() not in ["A","B"]:
            if AI_COACH_ENABLED and st.session_state.get("gemini_ready"):
                rubric = f"Rate this prompt for clarity, context, and format (1-5 each) and give one improvement tip in <=30 words:\n\n{attempt}"
                review = gemini_reply(rubric, temp=0.3)
                st.session_state.messages.append({"role":"assistant","content": f"**Tutor review:** {review}"})
            progress_to(80)
            return ("**Quick Check:** Which prompt yields structured output?\n"
                    "A) `Write about AI.`\n"
                    "B) `Create a 5-step checklist for starting with AI at a small bakery, numbered list.`\n\n"
                    "_Reply with A or B._")
        elif attempt.upper() in ["A","B"]:
            if attempt.upper() == "B":
                st.session_state.quiz_correct += 1
                st.session_state.messages.append({"role":"assistant","content":"**Tutor:** Great pick — numbered steps create structure."})
            else:
                st.session_state.messages.append({"role":"assistant","content":"**Tutor:** Close. Asking for numbered steps (B) yields a tidy result."})
            st.session_state.module = 3; progress_to(85)
            return "Moving to **Module 3: Hands-On**. Type anything to continue."
        else:
            return "Try adding audience, tone, and format (e.g., Instagram posts, friendly tone, bullet list)."

def render_module_3(user_text: str):
    if st.session_state.progress < 90:
        progress_to(90); badge("AI Tinkerer", "🛠️")
        return ("### Module 3: Hands-On Practice\n"
                "Pick a quick exercise (reply with 1, 2, or 3):\n"
                "1) Content — 5 product ideas using AI\n"
                "2) Customer Support — empathetic reply to a delay complaint\n"
                "3) Data — 3 ways AI can save time in spreadsheets")
    else:
        choice = user_text.strip()
        if choice in ["1","2","3"]:
            progress_to(95)
            prompts = {
                "1": "Generate 5 product ideas for eco-friendly kitchen tools.",
                "2": "Write a brief, empathetic apology for a delayed order; offer options to resolve.",
                "3": "List 3 spreadsheet automations (cleaning, categorizing, summarizing)."
            }
            hint = ""
            if st.session_state.get("gemini_ready") and AI_COACH_ENABLED:
                hint_text = gemini_reply(f"Give one 15-word tip to do this well: {prompts[choice]}", temp=0.6)
                hint = f"\n\n**Tutor tip:** {hint_text}"
            return f"Great choice! Try this: **{prompts[choice]}**{hint}\n\n_When you're done, type `done`._"
        elif choice.lower() == "done":
            progress_to(100)
            return (
                "👏 Nicely done. You've completed the free track!\n\n"
                "## 🔒 Locked Level: Applied AI Playbooks\n"
                "- 12 advanced prompt frameworks\n- Case studies + templates\n- Certificate + full Report Card\n\n"
                "👉 **Unlock via the AI Learning Academy:** [Enroll to unlock](https://example.com/enroll)\n\n"
                "### Report Card (Preview)\n"
                f"- Concepts: {'★'*min(5,3 + st.session_state.quiz_correct)}{'☆'*max(0,5-(3+st.session_state.quiz_correct))}\n"
                f"- Prompt Craft: {'★'*min(5,2 + st.session_state.quiz_correct)}{'☆'*max(0,5-(2+st.session_state.quiz_correct))}\n"
                "- Applied Practice: ★★★☆☆\n"
                "- Consistency: ★★☆☆☆\n\n"
                "_Enter your email to receive your badges + preview report & a limited-time coupon._"
            )
        else:
            return "Reply with `1`, `2`, or `3` to pick an exercise, then type `done` when finished."

def route(user_text: str):
    m = st.session_state.module
    if m == 0:
        st.session_state.module = 1
        return render_module_1(user_text)
    if m == 1:
        return render_module_1(user_text)
    if m == 2:
        return render_module_2(user_text)
    if m == 3:
        return render_module_3(user_text)
    return "Say **begin** to start."

# Chat input
user_input = st.chat_input("Your answer...")
if user_input:
    st.session_state.messages.append({"role":"user","content":user_input})
    reply = route(user_input)
    st.session_state.messages.append({"role":"assistant","content": reply})
    st.rerun()

# Email capture
st.divider()
with st.expander("Enrollment & Email (Demo)"):
    email = st.text_input("Enter email to receive badges + coupon (demo)")
    if st.button("Send me my goodies"):
        if email and "@" in email:
            st.session_state.email_captured = True
            st.success("✅ Demo: Email captured. In production, trigger Zapier/Make → CRM + LMS.")
        else:
            st.error("Please enter a valid email.")

st.caption("Demo shows: progress, badges, quizzes, (optional) AI hints via Gemini with cooldown, locked level, upsell CTA, report card preview.")
