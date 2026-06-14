# BEITI — מפרט טכני

## מה זה ביתי?
בוט WhatsApp לניהול הבית: רשימת קניות, חשבונות ותשלומים — הכל דרך הודעה אחת.

---

## ארכיטקטורה

```
WhatsApp (משתמש)
      │  POST
      ▼
heyy.io (ממסר)
      │  POST /webhook/
      ▼
Flask Backend (beiti)
      │
      ├─► Claude API  ──► הבנת כוונה (intent)
      │
      ├─► Supabase    ──► שמירה / שליפה
      │
      └─► heyy.io API ──► שליחת תשובה
```

---

## טבלאות Supabase

### `households`
| עמודה | סוג | תיאור |
|---|---|---|
| id | uuid (PK) | מזהה ייחודי |
| name | text | שם הבית (ברירת מחדל: "ביתי") |
| phone_numbers | text[] | כל מספרי הטלפון של בני הבית |
| created_at | timestamptz | |

### `shopping_items`
| עמודה | סוג | תיאור |
|---|---|---|
| id | uuid (PK) | |
| household_id | uuid (FK) | |
| name | text | שם הפריט ("חלב") |
| quantity | text | כמות ("2 ליטר") — טקסט חופשי |
| bought | bool | האם נקנה |
| added_by | text | שם המוסיף |
| created_at | timestamptz | |

### `bills`
| עמודה | סוג | תיאור |
|---|---|---|
| id | uuid (PK) | |
| household_id | uuid (FK) | |
| name | text | שם החשבון ("חשמל") |
| amount | numeric | סכום בשקלים |
| due_date | date | תאריך תשלום |
| paid | bool | שולם? |
| recurring | bool | חוזר חודשי? |
| notes | text | הערות |
| created_at | timestamptz | |

---

## Intents (כוונות משתמש)

| Intent | דוגמאות |
|---|---|
| `add_shopping` | "תוסיף חלב", "צריך לקנות לחם" |
| `remove_shopping` | "מחק חלב מהרשימה", "הסר ביצים" |
| `list_shopping` | "מה ברשימה?", "תראה לי מה צריך לקנות" |
| `add_bill` | "שמור חשמל 380 שקל", "יש חשבון מים ל-15 ליולי" |
| `mark_paid` | "שילמתי חשמל", "סמן ארנונה כשולם" |
| `list_bills` | "מה יש לשלם?", "אילו חשבונות פתוחים?" |
| `general` | כל דבר אחר |

---

## Webhook מ-heyy.io

**POST** `/webhook/`

```json
{
  "from": "972501234567",
  "message": { "text": "תוסיף חלב לרשימה" },
  "contact": { "name": "רון" }
}
```

---

## משתני סביבה נדרשים

ראה `backend/.env.example`

---

## שלבי פיתוח

- [ ] 1. הגדרת טבלאות ב-Supabase
- [ ] 2. רישום webhook ב-heyy.io
- [ ] 3. בדיקת Claude intent parsing עם הודעות לדוגמה
- [ ] 4. חיבור מלא: webhook → Claude → Supabase → תשובה
- [ ] 5. הוספת בני בית נוספים ל-household
- [ ] 6. תזכורות אוטומטיות לחשבונות (cron)
