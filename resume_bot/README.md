# Telegram Resume ATS Bot

Send resumes (PDF / DOCX / TXT) to the bot on Telegram → get an ATS score, improvement tips and 3 certification suggestions. Multiple resumes at once are supported.

## Setup (5 steps)

1. **Get a bot token**: open Telegram → search `@BotFather` → send `/newbot` → follow steps → copy the token.
2. **Install Python 3.10+**, then in this folder:
   ```
   pip install -r requirements.txt
   ```
3. **Set the token**
   - Windows (PowerShell): `$env:TELEGRAM_BOT_TOKEN="your_token_here"`
   - Linux/Mac: `export TELEGRAM_BOT_TOKEN="your_token_here"`
4. **Run**: `python bot.py`
5. **Use on mobile**: open Telegram on your phone → search your bot's username → press Start → send resumes.

The bot works on mobile automatically because Telegram itself is the mobile app. Your laptop only needs to stay on while the bot runs. To keep it running 24/7, deploy to a free host like Render, Railway or PythonAnywhere.

## Commands
- `/jd <text>` – match against a job description
- `/ranking` – rank all resumes sent
- `/clear` – reset

## ATS score (100 points)
Contact info 10 · Sections 25 · Skills/keywords 25 · Action verbs 10 · Measurable results 10 · Length 10 · LinkedIn/GitHub 10
