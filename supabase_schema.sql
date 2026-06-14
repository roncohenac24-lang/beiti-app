-- ============================================================
-- BEITI — Supabase Schema
-- הרץ את הקובץ הזה ב: Supabase Dashboard > SQL Editor > New Query
-- סדר הרצה חשוב — אל תשנה את הסדר
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 0. Extensions
-- ────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";


-- ────────────────────────────────────────────────────────────
-- 1. households — בתים / משפחות
-- ────────────────────────────────────────────────────────────
create table if not exists households (
    id          uuid primary key default uuid_generate_v4(),
    name        text not null default 'ביתי',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

comment on table households is 'יחידת הבסיס — כל בית מחזיק משתמשים, קניות, חשבונות ומשימות';


-- ────────────────────────────────────────────────────────────
-- 2. users — משתמשים (בני הבית)
-- ────────────────────────────────────────────────────────────
create table if not exists users (
    id              uuid primary key default uuid_generate_v4(),
    household_id    uuid not null references households(id) on delete cascade,
    name            text not null,
    phone           text not null unique,   -- 972501234567 (ללא + ורווחים)
    role            text not null default 'member'
                        check (role in ('admin', 'member')),
    is_active       boolean not null default true,
    joined_at       timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

comment on table users    is 'בני הבית — כל אחד מזוהה לפי מספר טלפון';
comment on column users.phone is 'פורמט בינלאומי ללא + — 972501234567';

create index if not exists idx_users_household on users(household_id);
create index if not exists idx_users_phone     on users(phone);


-- ────────────────────────────────────────────────────────────
-- 3. shopping_list — רשימת קניות
-- ────────────────────────────────────────────────────────────
create table if not exists shopping_list (
    id              uuid primary key default uuid_generate_v4(),
    household_id    uuid not null references households(id) on delete cascade,
    added_by        uuid references users(id) on delete set null,
    name            text not null,
    quantity        text not null default '',       -- טקסט חופשי: "2 ליטר", "חצי ק"ג"
    category        text not null default 'כללי',  -- פירות, ירקות, מוצרי חלב וכו'
    is_bought       boolean not null default false,
    bought_by       uuid references users(id) on delete set null,
    bought_at       timestamptz,
    priority        smallint not null default 0,    -- 0=רגיל, 1=דחוף
    notes           text not null default '',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

comment on table shopping_list is 'רשימת הקניות הפעילה של הבית';

create index if not exists idx_shopping_household  on shopping_list(household_id);
create index if not exists idx_shopping_not_bought on shopping_list(household_id, is_bought)
    where is_bought = false;


-- ────────────────────────────────────────────────────────────
-- 4. bills — חשבונות ותשלומים
-- ────────────────────────────────────────────────────────────
create table if not exists bills (
    id              uuid primary key default uuid_generate_v4(),
    household_id    uuid not null references households(id) on delete cascade,
    created_by      uuid references users(id) on delete set null,
    name            text not null,                 -- "חשמל", "ארנונה", "ועד בית"
    category        text not null default 'אחר'
                        check (category in ('חשמל', 'מים', 'גז', 'ארנונה', 'ועד בית',
                                            'אינטרנט', 'ביטוח', 'שכירות', 'אחר')),
    amount          numeric(10, 2) not null default 0,
    currency        char(3) not null default 'ILS',
    due_date        date,
    is_paid         boolean not null default false,
    paid_at         timestamptz,
    paid_by         uuid references users(id) on delete set null,
    recurring       boolean not null default false,
    recurrence      text                            -- 'monthly', 'bimonthly', 'yearly'
                        check (recurrence in ('monthly', 'bimonthly', 'yearly') or recurrence is null),
    notes           text not null default '',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

comment on table bills is 'חשבונות חד-פעמיים וחוזרים של הבית';

create index if not exists idx_bills_household   on bills(household_id);
create index if not exists idx_bills_unpaid      on bills(household_id, is_paid, due_date)
    where is_paid = false;
create index if not exists idx_bills_due_date    on bills(due_date)
    where is_paid = false;


-- ────────────────────────────────────────────────────────────
-- 5. tasks — משימות בית
-- ────────────────────────────────────────────────────────────
create table if not exists tasks (
    id              uuid primary key default uuid_generate_v4(),
    household_id    uuid not null references households(id) on delete cascade,
    created_by      uuid references users(id) on delete set null,
    assigned_to     uuid references users(id) on delete set null,
    title           text not null,
    description     text not null default '',
    status          text not null default 'open'
                        check (status in ('open', 'in_progress', 'done', 'cancelled')),
    priority        smallint not null default 0
                        check (priority between 0 and 2),   -- 0=רגיל, 1=גבוה, 2=דחוף
    due_date        date,
    completed_at    timestamptz,
    recurring       boolean not null default false,
    recurrence      text
                        check (recurrence in ('daily', 'weekly', 'monthly') or recurrence is null),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

comment on table tasks is 'משימות בית — ניקיון, תיקונים, תזכורות';

create index if not exists idx_tasks_household on tasks(household_id);
create index if not exists idx_tasks_assigned  on tasks(assigned_to)
    where status not in ('done', 'cancelled');
create index if not exists idx_tasks_open      on tasks(household_id, status)
    where status = 'open';


-- ────────────────────────────────────────────────────────────
-- 6. purchase_history — היסטוריית קניות (ללמידת הרגלים)
-- ────────────────────────────────────────────────────────────
create table if not exists purchase_history (
    id              uuid primary key default uuid_generate_v4(),
    household_id    uuid not null references households(id) on delete cascade,
    bought_by       uuid references users(id) on delete set null,
    item_name       text not null,
    normalized_name text not null,              -- שם מנורמל ללא כמות ("חלב" ולא "2 חלב")
    category        text not null default 'כללי',
    quantity        text not null default '',
    times_bought    integer not null default 1, -- כמה פעמים נקנה הפריט הזה בסך הכל
    last_bought_at  timestamptz not null default now(),
    source_item_id  uuid references shopping_list(id) on delete set null,
    created_at      timestamptz not null default now()
);

comment on table purchase_history is
    'כל פריט שנסמן כנקנה נרשם כאן — משמש את Claude ללמידת הרגלי הבית והצעת פריטים';

create index if not exists idx_history_household     on purchase_history(household_id);
create index if not exists idx_history_normalized    on purchase_history(household_id, normalized_name);
create index if not exists idx_history_last_bought   on purchase_history(household_id, last_bought_at desc);


-- ────────────────────────────────────────────────────────────
-- 7. updated_at trigger (אוטומטי לכל הטבלאות)
-- ────────────────────────────────────────────────────────────
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger trg_households_updated_at
    before update on households
    for each row execute function set_updated_at();

create trigger trg_users_updated_at
    before update on users
    for each row execute function set_updated_at();

create trigger trg_shopping_updated_at
    before update on shopping_list
    for each row execute function set_updated_at();

create trigger trg_bills_updated_at
    before update on bills
    for each row execute function set_updated_at();

create trigger trg_tasks_updated_at
    before update on tasks
    for each row execute function set_updated_at();


-- ────────────────────────────────────────────────────────────
-- 8. trigger — כשפריט נסמן כנקנה → כתוב ל-purchase_history
-- ────────────────────────────────────────────────────────────
create or replace function record_purchase()
returns trigger language plpgsql as $$
begin
    -- מופעל רק כשהפריט עובר מ-is_bought=false ל-is_bought=true
    if (old.is_bought = false and new.is_bought = true) then
        insert into purchase_history (
            household_id,
            bought_by,
            item_name,
            normalized_name,
            category,
            quantity,
            source_item_id,
            last_bought_at
        )
        values (
            new.household_id,
            new.bought_by,
            new.name,
            lower(trim(regexp_replace(new.name, '\d+\s*', '', 'g'))),  -- נרמול בסיסי
            new.category,
            new.quantity,
            new.id,
            now()
        )
        on conflict do nothing;  -- TODO: להוסיף upsert על normalized_name + household_id
    end if;
    return new;
end;
$$;

create trigger trg_record_purchase
    after update on shopping_list
    for each row execute function record_purchase();


-- ────────────────────────────────────────────────────────────
-- 9. Row Level Security (RLS)
-- ────────────────────────────────────────────────────────────
-- מפעיל RLS על כל הטבלאות — בשלב זה: service_role עוקף הכל
-- בעתיד: להוסיף policies לפי auth.uid() כשמחברים Supabase Auth

alter table households       enable row level security;
alter table users            enable row level security;
alter table shopping_list    enable row level security;
alter table bills            enable row level security;
alter table tasks            enable row level security;
alter table purchase_history enable row level security;

-- policy זמנית: גישה מלאה דרך service_role key (Backend בלבד)
-- הבוט משתמש ב-SUPABASE_KEY=service_role — אין חשיפה לקליינט
create policy "service role full access" on households
    for all using (true);
create policy "service role full access" on users
    for all using (true);
create policy "service role full access" on shopping_list
    for all using (true);
create policy "service role full access" on bills
    for all using (true);
create policy "service role full access" on tasks
    for all using (true);
create policy "service role full access" on purchase_history
    for all using (true);


-- ────────────────────────────────────────────────────────────
-- 10. נתוני דמו (אופציונלי — מחק אם אינך רוצה)
-- ────────────────────────────────────────────────────────────
-- הסר את הסימון -- מהשורות הבאות כדי להוסיף נתוני בדיקה:

/*
insert into households (name) values ('בית כהן') returning id;
-- העתק את ה-id שחזר והכנס אותו בשורות הבאות

insert into users (household_id, name, phone, role)
values
    ('<household_id>', 'רון', '972501234567', 'admin'),
    ('<household_id>', 'ליאור', '972509876543', 'member');

insert into shopping_list (household_id, name, category, quantity)
values
    ('<household_id>', 'חלב', 'מוצרי חלב', '2 ליטר'),
    ('<household_id>', 'לחם', 'מאפים', ''),
    ('<household_id>', 'ביצים', 'מוצרי חלב', '12');

insert into bills (household_id, name, category, amount, due_date, recurring, recurrence)
values
    ('<household_id>', 'חשמל', 'חשמל', 380.00, '2026-07-01', true, 'monthly'),
    ('<household_id>', 'ארנונה', 'ארנונה', 1200.00, '2026-07-15', true, 'bimonthly');
*/
