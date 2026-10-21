-- Run with `supabase test db` against a local test project after migrations.
begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select plan(8);
insert into auth.users(id,email) values
('11111111-1111-4111-8111-111111111111','tenant-a@example.test'),
('22222222-2222-4222-8222-222222222222','tenant-b@example.test');
insert into public.candidate_profiles(user_id,personal) values
('11111111-1111-4111-8111-111111111111','{"full_name":"Tenant A","email":"tenant-a@example.test"}'),
('22222222-2222-4222-8222-222222222222','{"full_name":"Tenant B","email":"tenant-b@example.test"}');
insert into public.application_drafts(user_id,application_id) values
('11111111-1111-4111-8111-111111111111','workday-1'),
('22222222-2222-4222-8222-222222222222','workday-1');
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"11111111-1111-4111-8111-111111111111","role":"authenticated"}',true);
select is((select count(*)::int from public.candidate_profiles),1,'A can only read A profile');
select is((select count(*)::int from public.application_drafts),1,'A can only read A draft');
select throws_ok($$insert into public.candidate_profiles(user_id) values('22222222-2222-4222-8222-222222222222') on conflict(user_id) do update set skills='["stolen"]'$$,'42501',null,'A cannot overwrite B profile');
select throws_ok($$insert into public.application_drafts(user_id,application_id,status) values('11111111-1111-4111-8111-111111111111','lever-1','submitted')$$,'42501',null,'Direct submitted-state insert is denied');
select throws_ok($$update public.candidate_profiles set resume='{"path":"22222222-2222-4222-8222-222222222222/resume.pdf"}' where user_id='11111111-1111-4111-8111-111111111111'$$,'42501',null,'A cannot attach B resume');
select throws_ok($$insert into public.application_submissions(draft_id,user_id,application_id,answers,resume) values(gen_random_uuid(),'11111111-1111-4111-8111-111111111111','workday-1','{}','{}')$$,'42501',null,'Direct submission insert is denied');
reset role;
set local role anon;
select throws_ok($$select * from public.candidate_profiles$$,'42501',null,'Anonymous profile read is denied');
select is((select count(*)::int from public.applications),20,'Anonymous visitors can read all twenty simulated roles');
reset role;
select * from finish();
rollback;
