-- Multi-tenant candidate workspace. Apply to a dedicated Supabase project.
create table public.candidate_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  personal jsonb not null default '{}'::jsonb check (jsonb_typeof(personal) = 'object'),
  education jsonb not null default '[]'::jsonb check (jsonb_typeof(education) = 'array'),
  work_experience jsonb not null default '[]'::jsonb check (jsonb_typeof(work_experience) = 'array'),
  skills jsonb not null default '[]'::jsonb check (jsonb_typeof(skills) = 'array'),
  verified_answers jsonb not null default '[]'::jsonb check (jsonb_typeof(verified_answers) = 'array'),
  resume jsonb check (resume is null or jsonb_typeof(resume) = 'object'),
  updated_at timestamptz not null default now()
);
create table public.applications (
  id text primary key,
  platform text not null check (platform in ('Workday','Greenhouse','Lever','Other')),
  company text not null,
  title text not null,
  location text not null,
  salary text not null,
  department text not null,
  description text not null,
  variant int not null check (variant between 1 and 5),
  simulated boolean not null default true check (simulated)
);
create table public.application_drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  application_id text not null references public.applications(id),
  answers jsonb not null default '{}'::jsonb check (jsonb_typeof(answers) = 'object'),
  resume jsonb check (resume is null or jsonb_typeof(resume) = 'object'),
  status text not null default 'draft' check (status in ('draft','submitted')),
  updated_at timestamptz not null default now(),
  submitted_at timestamptz,
  unique(user_id, application_id)
);
create table public.application_submissions (
  id uuid primary key default gen_random_uuid(),
  draft_id uuid not null unique references public.application_drafts(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  application_id text not null references public.applications(id),
  answers jsonb not null,
  resume jsonb not null,
  submitted_at timestamptz not null default now()
);
create index application_drafts_user_updated_idx on public.application_drafts(user_id, updated_at desc);
create index application_submissions_user_idx on public.application_submissions(user_id);

create function public.set_updated_at() returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end;
$$;
create trigger candidate_profiles_updated before update on public.candidate_profiles for each row execute function public.set_updated_at();
create trigger application_drafts_updated before update on public.application_drafts for each row execute function public.set_updated_at();

alter table public.candidate_profiles enable row level security;
alter table public.applications enable row level security;
alter table public.application_drafts enable row level security;
alter table public.application_submissions enable row level security;
revoke all on public.candidate_profiles, public.applications, public.application_drafts, public.application_submissions from anon, authenticated;
grant select, insert, update, delete on public.candidate_profiles to authenticated;
grant select on public.applications to anon, authenticated;
grant select, insert, update, delete on public.application_drafts to authenticated;
grant select on public.application_submissions to authenticated;

create policy profiles_owner_select on public.candidate_profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy profiles_owner_insert on public.candidate_profiles for insert to authenticated with check ((select auth.uid()) = user_id and (resume is null or split_part(resume->>'path','/',1) = (select auth.uid())::text));
create policy profiles_owner_update on public.candidate_profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id and (resume is null or split_part(resume->>'path','/',1) = (select auth.uid())::text));
create policy profiles_owner_delete on public.candidate_profiles for delete to authenticated using ((select auth.uid()) = user_id);
create policy catalog_public_read on public.applications for select to anon, authenticated using (true);
create policy drafts_owner_select on public.application_drafts for select to authenticated using ((select auth.uid()) = user_id);
create policy drafts_owner_insert on public.application_drafts for insert to authenticated with check ((select auth.uid()) = user_id and status = 'draft' and submitted_at is null and (resume is null or split_part(resume->>'path','/',1) = (select auth.uid())::text));
create policy drafts_owner_update on public.application_drafts for update to authenticated using ((select auth.uid()) = user_id and status = 'draft') with check ((select auth.uid()) = user_id and status = 'draft' and submitted_at is null and (resume is null or split_part(resume->>'path','/',1) = (select auth.uid())::text));
create policy drafts_owner_delete on public.application_drafts for delete to authenticated using ((select auth.uid()) = user_id and status = 'draft');
create policy submissions_owner_read on public.application_submissions for select to authenticated using ((select auth.uid()) = user_id);

-- Submissions can only be created through this atomic review operation.
create function public.submit_simulated_application(draft_id uuid, reviewed_answers jsonb, reviewed_resume jsonb)
returns uuid language plpgsql security definer set search_path = '' as $$
declare d public.application_drafts; submission_id uuid;
begin
  if auth.uid() is null then raise exception 'Sign in required'; end if;
  select * into d from public.application_drafts where id = draft_id and user_id = auth.uid() for update;
  if not found then raise exception 'Draft not found'; end if;
  if d.status <> 'draft' then raise exception 'Application already submitted'; end if;
  if d.answers is distinct from reviewed_answers or d.resume is distinct from reviewed_resume then raise exception 'Application changed since review'; end if;
  if length(trim(coalesce(d.answers->>'full_name',''))) = 0 or length(trim(coalesce(d.answers->>'email',''))) = 0 then raise exception 'Name and email are required'; end if;
  if d.resume is null or split_part(d.resume->>'path','/',1) is distinct from auth.uid()::text then raise exception 'Your own resume is required'; end if;
  if not exists(select 1 from storage.objects where bucket_id = 'resumes' and name = d.resume->>'path') then raise exception 'Resume file not found'; end if;
  insert into public.application_submissions(draft_id,user_id,application_id,answers,resume) values(d.id,d.user_id,d.application_id,d.answers,d.resume) returning id into submission_id;
  update public.application_drafts set status='submitted', submitted_at=now() where id=d.id;
  return submission_id;
end;
$$;
revoke all on function public.submit_simulated_application(uuid,jsonb,jsonb) from public, anon;
grant execute on function public.submit_simulated_application(uuid,jsonb,jsonb) to authenticated;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('resumes','resumes',false,5242880,array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain'])
on conflict(id) do nothing;
create policy resumes_owner_read on storage.objects for select to authenticated using (bucket_id='resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy resumes_owner_upload on storage.objects for insert to authenticated with check (bucket_id='resumes' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy resumes_owner_delete on storage.objects for delete to authenticated using (bucket_id='resumes' and (storage.foldername(name))[1] = (select auth.uid())::text and not exists(select 1 from public.application_submissions where resume->>'path'=name));
