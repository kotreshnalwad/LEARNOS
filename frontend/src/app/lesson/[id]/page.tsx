'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ExternalLink, Play, BookOpen, FileText, Code2,
  CheckCircle, Clock, Zap, ChevronLeft, MessageSquare,
  Headphones, Newspaper, GraduationCap, Github
} from 'lucide-react'
import Link from 'next/link'
import { useRoadmap, useUpdateProgress } from '@/hooks/useApi'
import { useTutorStore } from '@/stores'
import { AppShell } from '@/components/layout/AppShell'
import { QuizPanel } from '@/components/quiz/QuizPanel'
import { TutorPanel } from '@/components/tutor/TutorPanel'
import { LevelBadge } from '@/components/shared/LevelBadge'
import { ResourceTypeBadge } from '@/components/shared/ResourceTypeBadge'
import type { Lesson, Module, Resource, ResourceType } from '@/types'

const RESOURCE_ICONS: Record<ResourceType, any> = {
  video: Play,
  course: GraduationCap,
  documentation: FileText,
  book: BookOpen,
  paper: Newspaper,
  blog: Newspaper,
  github: Github,
  podcast: Headphones,
}

type Tab = 'resources' | 'quiz' | 'project' | 'notes'

export default function LessonPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const lessonId = params.id as string
  const roadmapId = searchParams.get('roadmap') || ''

  const { data: roadmap } = useRoadmap(roadmapId)
  const { mutate: updateProgress } = useUpdateProgress()
  const { openTutor, isOpen: tutorOpen } = useTutorStore()

  const [activeTab, setActiveTab] = useState<Tab>('resources')
  const [notes, setNotes] = useState('')
  const [timeStart] = useState(Date.now())
  const [completed, setCompleted] = useState(false)

  // Find the lesson from roadmap data
  const { lesson, module } = findLesson(roadmap?.modules || [], lessonId)

  // Mark as in_progress on mount
  useEffect(() => {
    if (lesson) {
      updateProgress({ lesson_id: lesson.id, status: 'in_progress' })
    }
    return () => {
      const timeSpent = Math.floor((Date.now() - timeStart) / 1000)
      if (lesson && timeSpent > 10) {
        updateProgress({
          lesson_id: lesson.id,
          status: completed ? 'completed' : 'in_progress',
          time_spent_seconds: timeSpent,
          notes: notes || undefined,
        })
      }
    }
  }, [lesson?.id])

  const handleMarkComplete = () => {
    if (!lesson) return
    const timeSpent = Math.floor((Date.now() - timeStart) / 1000)
    updateProgress({
      lesson_id: lesson.id,
      status: 'completed',
      time_spent_seconds: timeSpent,
      notes: notes || undefined,
    })
    setCompleted(true)
  }

  if (!lesson) {
    return (
      <AppShell>
        <div className="p-8 text-muted-foreground text-sm">
          Loading lesson… {roadmapId && <Link href={`/roadmap/${roadmapId}`} className="underline">Back to roadmap</Link>}
        </div>
      </AppShell>
    )
  }

  const tabs: { id: Tab; label: string; show: boolean }[] = [
    { id: 'resources', label: `Resources (${lesson.resources.length})`, show: true },
    { id: 'quiz', label: 'Quiz', show: !!lesson.quiz },
    { id: 'project', label: 'Project', show: !!lesson.project },
    { id: 'notes', label: 'Notes', show: true },
  ]

  return (
    <AppShell>
      <div className={`flex h-[calc(100vh-60px)] overflow-hidden transition-all ${tutorOpen ? 'mr-[380px]' : ''}`}>
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-6 py-8 animate-fade-in">

            {/* Back */}
            {roadmapId && (
              <Link href={`/roadmap/${roadmapId}`} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
                <ChevronLeft className="w-4 h-4" /> {module?.title || 'Back to roadmap'}
              </Link>
            )}

            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-2">
                <LevelBadge level={lesson.difficulty} small />
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="w-3.5 h-3.5" /> {lesson.estimated_minutes} min
                </span>
                <span className="flex items-center gap-1 text-xs text-gold">
                  <Zap className="w-3.5 h-3.5" /> {lesson.xp_reward} XP
                </span>
              </div>
              <h1 className="font-serif text-2xl md:text-3xl text-foreground leading-tight mb-3">
                {lesson.title}
              </h1>
              {lesson.summary && (
                <p className="text-muted-foreground font-light leading-relaxed">
                  {lesson.summary}
                </p>
              )}
            </div>

            {/* Objectives */}
            {lesson.objectives && lesson.objectives.length > 0 && (
              <div className="bg-secondary/50 rounded-xl p-4 mb-6">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  Learning objectives
                </div>
                <ul className="space-y-1.5">
                  {lesson.objectives.map((obj, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                      <CheckCircle className="w-3.5 h-3.5 text-gold mt-0.5 flex-shrink-0" />
                      {obj}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tabs */}
            <div className="flex gap-0 border-b border-border mb-6">
              {tabs.filter(t => t.show).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                    activeTab === tab.id
                      ? 'border-foreground text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
              >
                {activeTab === 'resources' && (
                  <ResourcesTab resources={lesson.resources} />
                )}
                {activeTab === 'quiz' && lesson.quiz && (
                  <QuizPanel quiz={lesson.quiz} lessonId={lesson.id} />
                )}
                {activeTab === 'project' && lesson.project && (
                  <ProjectTab project={lesson.project} />
                )}
                {activeTab === 'notes' && (
                  <NotesTab notes={notes} onChange={setNotes} />
                )}
              </motion.div>
            </AnimatePresence>

            {/* Actions */}
            <div className="flex gap-3 mt-8 pt-6 border-t border-border">
              <button
                onClick={() => openTutor(lesson.id)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-secondary transition-colors"
              >
                <MessageSquare className="w-4 h-4" /> Ask AI Tutor
              </button>
              {!completed ? (
                <button
                  onClick={handleMarkComplete}
                  className="flex-1 flex items-center justify-center gap-2 bg-foreground text-background text-sm font-medium py-2.5 rounded-xl hover:opacity-85 transition-opacity"
                >
                  <CheckCircle className="w-4 h-4" /> Mark as complete
                </button>
              ) : (
                <div className="flex-1 flex items-center justify-center gap-2 bg-success/10 text-success text-sm font-medium py-2.5 rounded-xl border border-success/20">
                  <CheckCircle className="w-4 h-4" /> Completed! +{lesson.xp_reward} XP
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tutor panel */}
      {tutorOpen && lesson && (
        <TutorPanel lesson={lesson} roadmapTitle={roadmap?.title} />
      )}
    </AppShell>
  )
}

function ResourcesTab({ resources }: { resources: Resource[] }) {
  const primary = resources.filter(r => r.is_primary)
  const supplementary = resources.filter(r => !r.is_primary)

  return (
    <div className="space-y-6">
      {primary.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Primary resources</div>
          <div className="space-y-2">
            {primary.map(r => <ResourceItem key={r.id} resource={r} />)}
          </div>
        </div>
      )}
      {supplementary.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Additional resources</div>
          <div className="space-y-2">
            {supplementary.map(r => <ResourceItem key={r.id} resource={r} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function ResourceItem({ resource }: { resource: Resource }) {
  const Icon = RESOURCE_ICONS[resource.resource_type] || FileText
  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3.5 p-4 rounded-xl border border-border hover:border-gold/30 hover:bg-secondary/30 transition-all group"
    >
      <div className="w-9 h-9 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-foreground/70" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground truncate">{resource.title}</div>
        <div className="flex items-center gap-2 mt-0.5">
          {resource.platform && <span className="text-xs text-muted-foreground">{resource.platform}</span>}
          {resource.duration_minutes && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" /> {resource.duration_minutes}m
            </span>
          )}
          <ResourceTypeBadge type={resource.resource_type} />
        </div>
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors flex-shrink-0" />
    </a>
  )
}

function ProjectTab({ project }: { project: NonNullable<Lesson['project']> }) {
  return (
    <div className="space-y-5">
      <div>
        <h3 className="font-medium text-foreground mb-1">{project.title}</h3>
        <p className="text-sm text-muted-foreground font-light leading-relaxed">{project.description}</p>
      </div>
      {project.requirements && (
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Requirements</div>
          <ul className="space-y-1.5">
            {project.requirements.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="text-gold mt-0.5">•</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}
      {project.deliverables && (
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">Deliverables</div>
          <ul className="space-y-1.5">
            {project.deliverables.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <CheckCircle className="w-3.5 h-3.5 text-gold mt-0.5 flex-shrink-0" /> {d}
              </li>
            ))}
          </ul>
        </div>
      )}
      {project.hints && (
        <div className="bg-gold-light/30 border border-gold/20 rounded-xl p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-gold-dark mb-2">💡 Hints</div>
          <ul className="space-y-1.5">
            {project.hints.map((h, i) => (
              <li key={i} className="text-sm text-foreground/80">{h}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex items-center gap-2 text-sm text-gold font-medium">
        <Zap className="w-4 h-4" /> {project.xp_reward} XP reward for completion
      </div>
    </div>
  )
}

function NotesTab({ notes, onChange }: { notes: string; onChange: (v: string) => void }) {
  return (
    <div>
      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
        Your notes (auto-saved)
      </div>
      <textarea
        value={notes}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Write your notes here… key insights, questions, code snippets."
        className="w-full h-64 bg-secondary/40 border border-border rounded-xl p-4 text-sm font-light text-foreground placeholder:text-muted-foreground/60 outline-none focus:border-gold/40 resize-none transition-colors font-mono"
      />
      <div className="text-xs text-muted-foreground mt-2">{notes.length} characters</div>
    </div>
  )
}

function findLesson(modules: Module[], lessonId: string): { lesson: Lesson | null; module: Module | null } {
  for (const module of modules) {
    const lesson = module.lessons.find(l => l.id === lessonId)
    if (lesson) return { lesson, module }
  }
  return { lesson: null, module: null }
}
