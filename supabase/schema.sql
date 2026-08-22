-- Run this in the Supabase SQL Editor (Project: ai_career_coach).
-- Then set DATABASE_URL in backend/.env to the Session pooler URI
-- (Connect → Python → URI, sslmode=require) and restart the API.
-- FastAPI uses the database password, so it bypasses RLS. RLS is here
-- for when you later query as a limited role.

create extension if not exists vector;

create table if not exists users (
  id bigint generated always as identity primary key,
  email text unique not null,
  password_hash text not null,
  full_name text not null,
  role text default 'user',
  plan text default 'free',
  stripe_customer_id text default '',
  card_last4 text default '',
  card_brand text default '',
  password_reset_token_hash text default '',
  password_reset_expires timestamptz,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists profiles (
  id bigint generated always as identity primary key,
  user_id bigint unique references users(id) on delete cascade,
  country text default '',
  city text default '',
  professional_status text default 'student',
  headline text default '',
  summary text default '',
  education jsonb default '[]',
  experience jsonb default '[]',
  skills jsonb default '{}',
  projects jsonb default '[]',
  career_goals jsonb default '{}',
  linkedin_url text default '',
  github_username text default '',
  readiness_score float default 0,
  resume_health float default 0,
  interview_performance float default 0,
  updated_at timestamptz default now()
);

create table if not exists resumes (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  title text,
  version_type text,
  template text,
  source text,
  target_role text default '',
  content jsonb default '{}',
  change_log jsonb default '[]',
  last_ats jsonb,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists roadmaps (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  target_role text,
  duration_months int default 3,
  milestones jsonb default '[]',
  skill_gap jsonb default '[]',
  is_saved boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists interview_sessions (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  target_role text,
  interview_type text,
  mode text default 'text',
  job_description text default '',
  status text default 'in_progress',
  questions jsonb default '[]',
  current_index int default 0,
  overall_score float,
  report jsonb,
  created_at timestamptz default now(),
  completed_at timestamptz
);

create table if not exists career_memories (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  category text,
  key text,
  value text,
  enabled boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists conversations (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  title text,
  messages jsonb default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists usage_records (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  feature text,
  period text,
  count int default 0,
  tokens int default 0
);

create table if not exists knowledge_docs (
  id bigint generated always as identity primary key,
  title text,
  source text,
  category text,
  topic text,
  target_role text,
  experience_level text,
  content text,
  chunk_index int default 0,
  embedding jsonb
);

create table if not exists reminders (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  title text,
  body text default '',
  due_at timestamptz,
  source text default 'custom',
  source_ref text default '',
  done boolean default false,
  created_at timestamptz default now()
);

create table if not exists profile_imports (
  id bigint generated always as identity primary key,
  user_id bigint references users(id) on delete cascade,
  source text,
  handle text default '',
  raw jsonb default '{}',
  analysis jsonb default '{}',
  applied boolean default false,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
alter table resumes enable row level security;
alter table roadmaps enable row level security;
alter table interview_sessions enable row level security;
alter table career_memories enable row level security;
alter table conversations enable row level security;
alter table usage_records enable row level security;
alter table reminders enable row level security;
alter table profile_imports enable row level security;

alter table users add column if not exists card_last4 text default '';
alter table users add column if not exists card_brand text default '';
alter table users add column if not exists password_reset_token_hash text default '';
alter table users add column if not exists password_reset_expires timestamptz;
