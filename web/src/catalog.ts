import type { Application, Field, Platform } from './types'

const groups: [Platform, string[], string[]][] = [
  ['Workday', ['Northstar Systems', 'Summit Health', 'Atlas Financial', 'Cedar Energy', 'Meridian Retail'], ['Software Engineer', 'Data Analyst', 'Product Manager', 'Cloud Engineer', 'UX Designer']],
  ['Greenhouse', ['Linear Grove', 'Orbit Labs', 'Moss Robotics', 'Forma Studio', 'Harbor AI'], ['Frontend Engineer', 'Machine Learning Engineer', 'Robotics Engineer', 'Product Designer', 'Customer Success Manager']],
  ['Lever', ['Juniper Cloud', 'Lumen Analytics', 'Pinecone Works', 'Tidal Software', 'Copper Labs'], ['Backend Engineer', 'Analytics Engineer', 'DevOps Engineer', 'Technical Writer', 'Security Engineer']],
  ['Other', ['Studio Fern', 'Bluebird Commerce', 'Helio Research', 'Fieldwork Co.', 'Beacon Education'], ['Creative Developer', 'Operations Analyst', 'Research Assistant', 'Project Coordinator', 'Learning Designer']],
]
export const applications: Application[] = groups.flatMap(([platform, companies, titles]) => companies.map((company, i) => ({
  id: `${platform.toLowerCase()}-${i + 1}`, platform, company, title: titles[i],
  location: ['New York, NY', 'Remote · US', 'Austin, TX', 'San Francisco, CA', 'Boston, MA'][i],
  salary: ['$110k – $150k', '$95k – $135k', '$120k – $165k', '$105k – $145k', '$90k – $130k'][i],
  department: ['Engineering', 'Data & Insights', 'Product', 'Infrastructure', 'Design & Experience'][i],
  description: `Join the ${company} team to build thoughtful products, collaborate across disciplines, and solve meaningful problems. This fictional opening is part of the Open Apply testing catalog.`, variant: i + 1,
})))

const baseFields: Field[] = [
  { id: 'full_name', label: 'Full name', required: true, section: 'Personal information' },
  { id: 'email', label: 'Email address', type: 'email', required: true, section: 'Personal information' },
  { id: 'phone', label: 'Phone number', type: 'tel', section: 'Personal information' },
  { id: 'city', label: 'City', section: 'Personal information' },
  { id: 'linkedin', label: 'LinkedIn', type: 'url', section: 'Personal information' },
  { id: 'school', label: 'School', section: 'Experience & education' },
  { id: 'degree', label: 'Degree', section: 'Experience & education' },
  { id: 'employer', label: 'Most recent employer', section: 'Experience & education' },
  { id: 'job_title', label: 'Most recent job title', section: 'Experience & education' },
  { id: 'skills', label: 'Skills', type: 'textarea', section: 'Experience & education' },
  { id: 'work_authorization', label: 'Are you authorized to work in the United States?', type: 'select', options: ['', 'Yes', 'No'], section: 'Additional questions' },
  { id: 'salary', label: 'Desired salary', section: 'Additional questions' },
  { id: 'motivation', label: 'Why do you want this job?', type: 'textarea', section: 'Additional questions' },
]
const extraQuestions = ['What is your available start date?', 'Are you willing to relocate?', 'Please share a portfolio URL.', 'How many years of relevant experience do you have?', 'What working arrangement do you prefer?']
export function fieldsFor(application: Application): Field[] {
  const fields = baseFields.map(f => ({ ...f }))
  if (application.platform === 'Lever') fields.splice(5, 2)
  if (application.platform === 'Other' && application.variant % 2 === 0) fields.splice(5, 4)
  fields.push({ id: 'custom_answer', label: extraQuestions[application.variant - 1], type: application.variant === 3 ? 'url' : 'text', section: 'Additional questions' })
  return fields
}
