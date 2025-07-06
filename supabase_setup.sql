-- sales_data テーブル作成
create table if not exists public.sales_data (
  id serial primary key,
  company_id uuid not null,
  date date not null,
  revenue numeric,
  employees integer,
  weather_data jsonb
);

-- RLS（行レベルセキュリティ）有効化
alter table public.sales_data enable row level security;

-- JWT 内の company_id と一致する行だけ選択可能
create policy "Select own company data" on public.sales_data
  for select using (
    company_id = (auth.jwt() ->> 'company_id')::uuid
  );