# 🤖 Multi-Bot Telegram Support Manager

**Production-ready Multi-Bot Telegram Support Management System**

One Master Bot + unlimited connected bots · One centralized support group · Full two-way reply routing · MongoDB Atlas · Render Free Web Service

---

## ✨ Features

- **One Master Bot** – Premium admin panel with inline keyboards
- **Unlimited Child Bots** – Add any bot by token; they run simultaneously
- **Centralized Support Group** – All messages from all bots arrive in one group
- **Two-way Reply System** – Reply in the group → message delivered through the original bot
- **Independent Settings** – Welcome message, auto-reply, cooldown per bot
- **Admin Management** – Owner + multiple admins with permission checks
- **Statistics & Activity Logs**
- **Webhook Architecture** – Optimized for Render Free (no long-running polling)
- **Secure** – Tokens never shown in full, webhook secrets, owner-only actions

---

## 📁 Project Structure

```
MultiBot-Support-Manager/
├── main.py                 # FastAPI + lifespan entry point
├── requirements.txt
├── render.yaml
├── Procfile
├── .env.example
├── .gitignore
├── README.md
├── app/
│   ├── config.py           # Pydantic settings
├── database/
│   ├── connection.py       # Motor + indexes
│   ├── models.py
│   └── repositories.py     # All DB operations
├── handlers/
│   ├── master.py           # Full admin panel + group reply handler
│   └── child_bot.py        # Per-bot start/help/message forwarding
├── services/
│   ├── bot_manager.py      # Multi-bot lifecycle & webhooks
│   └── support_service.py  # Forwarding + reply routing
├── keyboards/
│   ├── master.py
│   └── support.py
├── middlewares/
│   ├── auth.py
│   └── logging.py
├── webhooks/
│   └── routes.py           # /webhook/master/... and /webhook/bot/...
├── utils/
│   └── helpers.py
└── tests/
```

---

## 🚀 Deployment Guide (Beginner + Mobile Friendly)

You can do everything from an Android browser (Chrome recommended).

### 1. Create MongoDB Atlas Database (Free)

1. Open [https://www.mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) and sign up / log in.
2. Create a **Free (M0)** cluster (choose any region close to you).
3. Create a database user (username + password). **Save the password.**
4. Network Access → Add IP Address → **Allow Access from Anywhere** (`0.0.0.0/0`).
5. Database → Connect → Drivers → copy the connection string.
   - It looks like:  
     `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   - Replace `<password>` with your real password.
   - Add a database name, e.g.:  
     `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/support_manager?retryWrites=true&w=majority`

### 2. Create Master Bot

1. Open Telegram → search **@BotFather**.
2. Send `/newbot` → follow instructions → copy the **token**.
3. (Optional) Set a nice name and description.

### 3. Get Your Telegram User ID

1. Open Telegram → search **@userinfobot** → `/start`.
2. Copy the numeric **Id**.

### 4. Deploy on Render (Free Web Service)

1. Open [https://render.com](https://render.com) → Sign up with GitHub (or email).
2. Create a **New Web Service**.
3. Connect your GitHub repository (upload this project to a private/public repo first) **or** use “Deploy from GitHub” after pushing the code.
4. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables (exactly these names):

| Variable            | Value                                      |
|---------------------|--------------------------------------------|
| `MASTER_BOT_TOKEN`  | Token from @BotFather                      |
| `MONGODB_URI`       | Full MongoDB Atlas connection string       |
| `OWNER_ID`          | Your numeric Telegram user ID              |
| `WEBHOOK_BASE_URL`  | Will be set after first deploy (see below) |
| `WEBHOOK_SECRET`    | Any long random string (e.g. `mysecret123xyz`) |
| `MONGODB_DB_NAME`   | `support_manager` (optional)               |
| `LOG_LEVEL`         | `INFO`                                     |

6. Click **Create Web Service**. Wait until it shows **Live**.
7. Copy the public URL (example: `https://multi-bot-support-xxxx.onrender.com`).
8. Go back to Environment → set  
   `WEBHOOK_BASE_URL` = `https://multi-bot-support-xxxx.onrender.com`  
   (no trailing slash).
9. **Manual Deploy** again so the new variable is applied.

> **Note**: Render Free services spin down after ~15 min of inactivity. The first request after sleep takes 30–60 s. The system recovers automatically.

### 5. First Launch Checklist

1. Open Telegram → find your **Master Bot** → `/start`.
2. You should see the premium main menu.
3. **Set Support Group**:
   - Create a Telegram group (or use existing).
   - Add the **Master Bot** as administrator (with “Post Messages” permission).
   - Prefer also adding every child bot later as admin.
   - In Master Bot → Support Settings → Set / Change Group.
   - Forward any message from the group to the Master Bot, **or** send the group ID.
4. **Add your first child bot**:
   - Create another bot with @BotFather.
   - In Master Bot → Manage Bots → Add Bot → paste the token → Confirm.
5. Test:
   - Send a message to the child bot.
   - It should appear in the Support Group with buttons.
   - Reply to that message in the group → the reply reaches the user through the child bot.

---

## 📋 Environment Variables Reference

| Name               | Required | Description                                      |
|--------------------|----------|--------------------------------------------------|
| MASTER_BOT_TOKEN   | Yes      | Token of the central admin bot                   |
| MONGODB_URI        | Yes      | MongoDB Atlas connection string                  |
| OWNER_ID           | Yes      | Your Telegram numeric user ID                    |
| WEBHOOK_BASE_URL   | Yes      | Public HTTPS URL of the Render service           |
| WEBHOOK_SECRET     | Yes      | Random secret used in webhook paths              |
| MONGODB_DB_NAME    | No       | Default `support_manager`                        |
| LOG_LEVEL          | No       | `DEBUG` / `INFO` / `WARNING` / `ERROR`           |

---

## 🎮 Master Bot Commands

| Command     | Description                    |
|-------------|--------------------------------|
| /start      | Open Main Menu                 |
| /panel      | Open Admin Panel               |
| /help       | Help & instructions            |
| /addbot     | Add a new bot by token         |
| /bots       | List connected bots            |
| /removebot  | Remove a bot (via menu)        |
| /setgroup   | Configure support group        |
| /admins     | Manage administrators          |
| /stats      | Statistics dashboard           |
| /settings   | General settings               |
| /logs       | Recent activity logs           |
| /cancel     | Cancel current operation       |

### Child Bot Commands

| Command   | Description          |
|-----------|----------------------|
| /start    | Welcome message      |
| /help     | Help                 |
| /contact  | Contact support info |

---

## 🔐 Security Notes

- Bot tokens are stored in MongoDB and **never** displayed in full in messages or logs.
- Only the Owner can add/remove bots and admins.
- Webhook endpoints require the secret in the path (and optional header).
- Admin middleware blocks unauthorized users from the Master Bot.
- No secrets are hardcoded.

---

## 🛠 Local Development (optional)

```bash
python -m venv venv
source venv/bin/activate          # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env              # fill in values
# For local testing you need a public URL (ngrok, cloudflared, etc.)
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
```

---

## 📌 Important Render Free Limitations

- Service sleeps after inactivity → cold start 30–60 s.
- No persistent local disk – everything is in MongoDB.
- The system is designed to re-register webhooks and reload all bots on every restart.

---

## ✅ How Message Routing Works

1. User sends message → Child Bot receives it via its unique webhook.
2. System forwards a formatted copy to the Support Group and saves a mapping (`group_message_id` ↔ `bot_id` + `user_chat_id`).
3. Admin replies to that message in the group (native reply).
4. System looks up the mapping and delivers the reply **through the original child bot**.

Media (photos, videos, documents, voice, stickers, etc.) is supported via `file_id` (no re-upload needed).

---

## 📞 Support

If you encounter issues:

1. Check Render logs (Dashboard → Logs).
2. Verify all environment variables.
3. Confirm the Master Bot and child bots are admins in the support group.
4. Make sure `WEBHOOK_BASE_URL` has no trailing slash and matches the live URL exactly.

---

**Built for production use on Render Free + MongoDB Atlas Free tier.**
