create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create table private.agent_worker_secret (id boolean primary key default true check(id), token_hash text not null);
create table public.agent_worker_health (id boolean primary key default true check(id), last_seen timestamptz not null);
alter table public.agent_worker_health enable row level security;
revoke all on public.agent_worker_health from public, anon, authenticated;
grant select on public.agent_worker_health to authenticated;
create policy worker_health_read on public.agent_worker_health for select to authenticated using (true);
create table public.agent_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  application_id text not null references public.applications(id),
  status text not null default 'queued' check(status in ('queued','running','completed','failed','cancelled')),
  message text not null default 'Waiting for the server…',
  result jsonb, preview_image text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index agent_jobs_user_created on public.agent_jobs(user_id,created_at desc);
create index agent_jobs_pending on public.agent_jobs(created_at) where status in ('queued','running');
create unique index agent_jobs_one_active_per_user on public.agent_jobs(user_id) where status in ('queued','running');
alter table public.agent_jobs enable row level security;
revoke all on public.agent_jobs from public, anon, authenticated;
grant select on public.agent_jobs to authenticated;
create policy jobs_owner_read on public.agent_jobs for select to authenticated using ((select auth.uid())=user_id);
create table private.agent_job_inputs (
  job_id uuid primary key references public.agent_jobs(id) on delete cascade,
  profile jsonb not null, resume_url text, lease_id uuid
);
revoke all on all tables in schema private from public, anon, authenticated;

-- These narrowly scoped API wrappers require either an authenticated owner or
-- a separate 256-bit worker credential. No browser receives worker privileges.
create function private.check_agent_worker(worker_token text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if worker_token is null or length(worker_token)<40 or not exists (
   select 1 from private.agent_worker_secret where token_hash=encode(sha256(convert_to(worker_token,'UTF8')),'hex')
 ) then raise exception 'Invalid worker credential' using errcode='42501'; end if;
end $$;
revoke all on function private.check_agent_worker(text) from public, anon, authenticated;

create function public.start_agent_job(application text, signed_resume_url text default null) returns uuid
language plpgsql security definer set search_path='' as $$
declare p public.candidate_profiles; job uuid; uid uuid:=auth.uid();
begin
 if uid is null then raise exception 'Sign in required'; end if;
 perform pg_advisory_xact_lock(hashtextextended(uid::text,0));
 if not exists(select 1 from public.agent_worker_health where last_seen>now()-interval '60 seconds') then
   raise exception 'The agent server is offline. Please try again shortly.'; end if;
 select * into p from public.candidate_profiles where user_id=uid;
 if not found or length(trim(coalesce(p.personal->>'full_name','')))=0 or length(trim(coalesce(p.personal->>'email','')))=0 then
   raise exception 'Save your name and email in My profile first.'; end if;
 if p.resume is null or split_part(p.resume->>'path','/',1)<>uid::text or signed_resume_url is null then
   raise exception 'Upload a resume in My profile first.'; end if;
 if length(signed_resume_url)>8192 then raise exception 'Invalid resume URL'; end if;
 if exists(select 1 from public.agent_jobs where user_id=uid and status in ('queued','running')) then
   raise exception 'You already have an active agent run.'; end if;
 if (select count(*) from public.agent_jobs where user_id=uid and created_at>now()-interval '1 hour')>=5 then
   raise exception 'Limit reached: five agent runs per hour. Please try again later.'; end if;
 if (select count(*) from public.agent_jobs where status in ('queued','running'))>=10 then
   raise exception 'The agent queue is full. Please try again later.'; end if;
 insert into public.agent_jobs(user_id,application_id) values(uid,application) returning id into job;
 insert into private.agent_job_inputs(job_id,profile,resume_url) values(job,to_jsonb(p),signed_resume_url);
 return job;
end $$;
revoke all on function public.start_agent_job(text,text) from public,anon;
grant execute on function public.start_agent_job(text,text) to authenticated;

create function public.cancel_agent_job(job_id uuid) returns void
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Sign in required'; end if;
 update public.agent_jobs set status='cancelled',message='Cancelled.',updated_at=now()
 where id=job_id and user_id=auth.uid() and status in ('queued','running');
 delete from private.agent_job_inputs where agent_job_inputs.job_id=cancel_agent_job.job_id
 and exists(select 1 from public.agent_jobs where id=cancel_agent_job.job_id and user_id=auth.uid() and status='cancelled');
end $$;
revoke all on function public.cancel_agent_job(uuid) from public,anon;
grant execute on function public.cancel_agent_job(uuid) to authenticated;

create function public.agent_worker_claim(worker_token text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare j public.agent_jobs; lease uuid:=gen_random_uuid(); payload jsonb;
begin
 perform private.check_agent_worker(worker_token);
 insert into public.agent_worker_health(id,last_seen) values(true,now()) on conflict(id) do update set last_seen=excluded.last_seen;
 update public.agent_jobs set status='failed',message='The run expired. Please start again.',updated_at=now()
 where (status='queued' and created_at<now()-interval '25 minutes')
 or (status='running' and (updated_at<now()-interval '2 minutes' or created_at<now()-interval '65 minutes'));
 delete from private.agent_job_inputs where job_id in(select id from public.agent_jobs where status in ('failed','cancelled','completed'));
 -- A single GPU worker; never lease another job while one is active.
 perform pg_advisory_xact_lock(510223001);
 if exists(select 1 from public.agent_jobs where status='running') then return null; end if;
 select * into j from public.agent_jobs where status='queued' order by created_at for update skip locked limit 1;
 if not found then return null; end if;
 update public.agent_jobs set status='running',message='Starting OpenWebRL on GPU 0…',updated_at=now() where id=j.id;
 update private.agent_job_inputs set lease_id=lease where job_id=j.id
 returning jsonb_build_object('profile',profile,'resume_url',resume_url) into payload;
 return payload || jsonb_build_object('id',j.id,'user_id',j.user_id,'application_id',j.application_id,'lease_id',lease);
end $$;
revoke all on function public.agent_worker_claim(text) from public,anon,authenticated;
grant execute on function public.agent_worker_claim(text) to anon;

create function public.agent_worker_report(worker_token text,job_id uuid,lease_id uuid,new_status text,message text,job_result jsonb,preview text) returns text
language plpgsql security definer set search_path='' as $$
declare current_status text;
begin
 perform private.check_agent_worker(worker_token);
 insert into public.agent_worker_health(id,last_seen) values(true,now()) on conflict(id) do update set last_seen=excluded.last_seen;
 select status into current_status from public.agent_jobs where id=job_id for update;
 if current_status is distinct from 'running' then return coalesce(current_status,'missing'); end if;
 if not exists(select 1 from private.agent_job_inputs i where i.job_id=agent_worker_report.job_id and i.lease_id=agent_worker_report.lease_id) then
   raise exception 'Lease mismatch'; end if;
 if new_status not in ('queued','running','completed','failed') then raise exception 'Invalid status'; end if;
 if length(coalesce(preview,''))>400000 or octet_length(coalesce(job_result,'{}'::jsonb)::text)>500000 then raise exception 'Result too large'; end if;
 update public.agent_jobs set status=new_status,message=left(agent_worker_report.message,300),result=job_result,
 preview_image=coalesce(preview,preview_image),updated_at=now() where id=job_id;
 if new_status in ('completed','failed') then delete from private.agent_job_inputs where agent_job_inputs.job_id=agent_worker_report.job_id; end if;
 return new_status;
end $$;
revoke all on function public.agent_worker_report(text,uuid,uuid,text,text,jsonb,text) from public,anon,authenticated;
grant execute on function public.agent_worker_report(text,uuid,uuid,text,text,jsonb,text) to anon;
