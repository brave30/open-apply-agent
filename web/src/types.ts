export type Platform = 'Workday' | 'Greenhouse' | 'Lever' | 'Other'
export type Education = { school: string; degree: string; field: string; graduation_year: number }
export type Experience = { employer: string; title: string; start_date: string; end_date: string | null; description: string }
export type VerifiedAnswer = { question: string; value: string; verified: boolean; verified_at: string | null; source: string }
export type Resume = { path: string; name: string; sha256: string; size: number; content_type: string }
export type CandidateProfile = {
  user_id: string
  personal: { full_name: string; email: string; phone: string; city: string; linkedin: string }
  education: Education[]
  work_experience: Experience[]
  skills: string[]
  verified_answers: VerifiedAnswer[]
  resume: Resume | null
  updated_at?: string
}
export type Application = { id: string; platform: Platform; company: string; title: string; location: string; salary: string; department: string; description: string; variant: number }
export type Field = { id: string; label: string; type?: string; required?: boolean; options?: string[]; section: string }
export type Draft = { id?: string; user_id: string; application_id: string; answers: Record<string, string>; resume: Resume | null; status: 'draft' | 'submitted'; updated_at?: string }
export function emptyProfile(user_id = '', email = ''): CandidateProfile {
  return { user_id, personal: { full_name: '', email, phone: '', city: '', linkedin: '' }, education: [], work_experience: [], skills: [], verified_answers: [], resume: null }
}
