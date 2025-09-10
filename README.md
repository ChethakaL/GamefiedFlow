# 🎓 AI Starter Quest — Gamified Learning Chatbot (Streamlit + Gemini)

An interactive **gamified chatbot demo** that teaches light AI basics, quizzes the learner, awards badges, and nudges them toward a locked “paid” module.  

This was built as a prototype for an **AI Learning Academy** — combining:
- **Gamification** (progress bar, badges, locked levels, report card preview)
- **AI tutoring** (hints & feedback powered by Google Gemini API)
- **Upsell mechanics** (free track ends with a locked module + call to action)

---

## ✨ Features
- **3 learning modules**:
  1. *AI Basics* — what AI is + everyday examples
  2. *Prompting Basics* — rewrite a weak prompt, quiz on structured output
  3. *Hands-On* — pick a short exercise (content, support, data)
- **Gamification**:
  - Progress bar updates with each step
  - Unlockable **badges** 🏅🔎🛠️
  - End-of-track **Report Card** preview
- **Upsell**:
  - Final module is locked
  - CTA to “Enroll to unlock advanced modules”
- **AI integration** (Google Gemini):
  - **💡 Get Hint** button (on-demand, context-aware hints)
  - **Optional AI Coaching** (auto feedback after key answers — can be toggled in code)
  - Built-in fallback hints if free-tier limits are hit
- **Lead capture**: demo email form, ready to connect to Zapier/Make → LMS or CRM.

---

## 🚀 Quickstart (local)

1. **Clone the repo**
   ```bash
   https://github.com/ChethakaL/GamefiedFlow.git
   cd GamefiedFlow
