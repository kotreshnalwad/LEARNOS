// ─── Enums ────────────────────────────────────────────────────────────────────

export type SkillLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type ResourceType = 'video' | 'course' | 'documentation' | 'book' | 'paper' | 'blog' | 'github' | 'podcast'
export type LessonStatus = 'locked' | 'in_progress' | 'completed'
export type RoadmapStatus = 'generating' | 'active' | 'completed' | 'archived'

// ─── User ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  clerk_id: string
  email: string
  name: string
  avatar_url?: string
  xp_points: number
  streak_days: number
  last_active_at?: string
  created_at: string
}

// ─── Topic ────────────────────────────────────────────────────────────────────

export interface Topic {
  id: string
  title: string
  slug: string
  description?: string
  category?: string
  tags?: string[]
  search_count: number
}

// ─── Resource ─────────────────────────────────────────────────────────────────

export interface Resource {
  id: string
  resource_type: ResourceType
  title: string
  url: string
  description?: string
  author?: string
  platform?: string
  duration_minutes?: number
  is_free: boolean
  is_primary: boolean
  composite_score: number
  thumbnail_url?: string
}

// ─── Project ──────────────────────────────────────────────────────────────────

export interface Project {
  id: string
  title: string
  description: string
  requirements?: string[]
  deliverables?: string[]
  hints?: string[]
  difficulty: SkillLevel
  xp_reward: number
}

// ─── Quiz ─────────────────────────────────────────────────────────────────────

export interface Question {
  id: string
  question: string
  question_type: string
  options?: string[]
  order: number
}

export interface Quiz {
  id: string
  passing_score: number
  time_limit_minutes?: number
  questions: Question[]
}

// ─── Lesson ───────────────────────────────────────────────────────────────────

export interface Lesson {
  id: string
  title: string
  summary?: string
  objectives?: string[]
  key_concepts?: string[]
  difficulty: SkillLevel
  estimated_minutes: number
  order: number
  xp_reward: number
  resources: Resource[]
  quiz?: Quiz
  project?: Project
  // progress overlay
  status?: LessonStatus
  mastery_score?: number
  time_spent_seconds?: number
}

// ─── Module ───────────────────────────────────────────────────────────────────

export interface Module {
  id: string
  title: string
  description?: string
  order: number
  is_unlocked: boolean
  estimated_hours?: number
  completion_percentage: number
  lessons: Lesson[]
}

// ─── Roadmap ──────────────────────────────────────────────────────────────────

export interface RoadmapSummary {
  id: string
  title: string
  level: SkillLevel
  status: RoadmapStatus
  completion_percentage: number
  estimated_hours?: number
  topic: Topic
  created_at: string
}

export interface Roadmap extends RoadmapSummary {
  description?: string
  modules: Module[]
  last_updated_at: string
}

// ─── Progress ─────────────────────────────────────────────────────────────────

export interface ProgressUpdate {
  lesson_id: string
  status: LessonStatus
  time_spent_seconds?: number
  notes?: string
}

export interface DashboardStats {
  total_lessons_completed: number
  total_hours_learned: number
  current_streak: number
  xp_points: number
  roadmaps_in_progress: number
  average_mastery_score: number
  badges_earned: number
}

// ─── Quiz Submission ──────────────────────────────────────────────────────────

export interface QuizSubmit {
  quiz_id: string
  answers: Record<string, string>
  time_taken_seconds?: number
}

export interface QuizResult {
  attempt_id: string
  score: number
  passed: boolean
  passing_score: number
  xp_earned: number
  feedback: Record<string, {
    correct: boolean
    your_answer: string
    correct_answer: string
    explanation?: string
  }>
}

// ─── Tutor ────────────────────────────────────────────────────────────────────

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface TutorChatRequest {
  lesson_id: string
  message: string
  conversation_history: TutorMessage[]
}

// ─── Generation ───────────────────────────────────────────────────────────────

export interface GenerationStatus {
  roadmap_id: string
  status: 'init' | 'created' | 'searching' | 'searched' | 'ranked' | 'generating' | 'curriculum' | 'saving' | 'complete' | 'error'
  progress: number
  current_step: string
  message: string
}

// ─── API Response Wrappers ────────────────────────────────────────────────────

export interface ApiError {
  detail: string
  status: number
}

// ─── UI State ─────────────────────────────────────────────────────────────────

export interface SearchState {
  query: string
  level: SkillLevel
  isGenerating: boolean
  generationStatus?: GenerationStatus
}
