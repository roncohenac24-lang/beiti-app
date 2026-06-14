# ביתי 🏠

בוט WhatsApp לניהול הבית — רשימת קניות, חשבונות ותשלומים.

## סטאק
- **WhatsApp**: heyy.io (API v2.0)
- **Backend**: Python / Flask
- **AI**: Claude API (Anthropic)
- **DB**: Supabase (PostgreSQL)

## התקנה מהירה

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # ומלא את המשתנים
python app.py
```

## מבנה הפרויקט

```
beiti/
├── backend/
│   ├── app.py                      # Flask entry point
│   ├── routes/
│   │   ├── webhook.py              # קבלת הודעות מ-heyy.io
│   │   ├── shopping.py             # רשימת קניות CRUD
│   │   └── bills.py                # חשבונות CRUD
│   ├── services/
│   │   ├── claude_service.py       # הבנת שפה טבעית
│   │   ├── heyy_service.py         # שליחת הודעות WhatsApp
│   │   └── supabase_service.py     # גישה לבסיס הנתונים
│   ├── requirements.txt
│   └── .env.example
├── BEITI_SPEC.md                   # מפרט טכני מלא
└── README.md
```

## משתני סביבה

ראה `backend/.env.example` — נדרשים:
- `ANTHROPIC_API_KEY`
- `HEYY_API_KEY` + `HEYY_INSTANCE_ID`
- `SUPABASE_URL` + `SUPABASE_KEY`

## הגדרת Webhook ב-heyy.io

הגדר את כתובת ה-webhook שלך ב-heyy.io dashboard:
```
https://<your-domain>/webhook/
```

לפיתוח מקומי — השתמש ב-[ngrok](https://ngrok.com):
```bash
ngrok http 5000
```

## מסמכים נוספים

ראה [BEITI_SPEC.md](BEITI_SPEC.md) למפרט טכני מלא כולל טבלאות Supabase ורשימת intents.
