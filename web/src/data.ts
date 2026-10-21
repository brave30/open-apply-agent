import { supabase } from './supabase'
import { emptyProfile, type CandidateProfile, type Draft, type Resume } from './types'

function client() { if (!supabase) throw new Error('Supabase is not configured.'); return supabase }
export async function getProfile(userId: string, email: string) {
  const { data, error } = await client().from('candidate_profiles').select('*').eq('user_id', userId).maybeSingle()
  if (error) throw error
  return data ? data as CandidateProfile : emptyProfile(userId, email)
}
export async function saveProfile(profile: CandidateProfile) {
  const { error } = await client().from('candidate_profiles').upsert(profile, { onConflict: 'user_id' })
  if (error) throw error
}
export async function uploadResume(userId: string, file: File): Promise<Resume> {
  const extension = file.name.split('.').at(-1)?.toLowerCase()
  if (!['pdf', 'docx', 'txt'].includes(extension || '')) throw new Error('Choose a PDF, DOCX, or TXT resume.')
  if (file.size > 5 * 1024 * 1024 || file.size === 0) throw new Error('Resume must be between 1 byte and 5 MB.')
  const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())), b => b.toString(16).padStart(2, '0')).join('')
  const path = `${userId}/${crypto.randomUUID()}.${extension}`
  const content_type = ({pdf:'application/pdf',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',txt:'text/plain'} as Record<string,string>)[extension!]
  const { error } = await client().storage.from('resumes').upload(path, file, { contentType: content_type, upsert: false })
  if (error) throw error
  return { path, name: file.name, sha256, size: file.size, content_type }
}
export async function getDrafts(userId: string): Promise<Draft[]> {
  const { data, error } = await client().from('application_drafts').select('*').eq('user_id', userId).order('updated_at', { ascending: false })
  if (error) throw error
  return data as Draft[]
}
export async function saveDraft(draft: Draft): Promise<Draft> {
  const { data, error } = await client().from('application_drafts').upsert(draft, { onConflict: 'user_id,application_id' }).select().single()
  if (error) throw error
  return data as Draft
}
export async function submitDraft(id: string, answers: Record<string, string>, resume: Resume | null) {
  const { error } = await client().rpc('submit_simulated_application', { draft_id: id, reviewed_answers: answers, reviewed_resume: resume })
  if (error) throw error
}
