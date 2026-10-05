-- Run this once in Supabase's SQL editor (Project -> SQL Editor -> New query)
-- before the app's stats-saving features will work.

create table users (
    id serial primary key,
    nickname text not null,
    created_at timestamptz not null default now()
);

-- Case-insensitive uniqueness without needing the citext extension:
-- ensure_user() in db.py always looks up/compares by lower(nickname).
create unique index users_nickname_lower_idx on users (lower(nickname));

create table games (
    id serial primary key,
    user_id integer not null references users(id) on delete cascade,
    secret text not null,
    won boolean not null,
    num_guesses integer not null,
    played_at timestamptz not null default now()
);

create table turn_analysis (
    id serial primary key,
    game_id integer not null references games(id) on delete cascade,
    turn integer not null,
    guess text not null,
    n_after integer not null,
    percentile double precision not null,
    median_remaining double precision not null
);
