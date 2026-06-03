'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { Sparkles, Loader2, MoreVertical, Trash2, ExternalLink, Clock, BookOpen } from 'lucide-react'
import Link from 'next/link'
import { streamSSE } from '@/lib/api'
import { useGenerationStore, useSearchStore } from '@/stores'
import type { RoadmapSummary, SkillLevel, ResourceType, GenerationStatus } from '@/types'

// ─── StatCard ──────────────────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: string | number
  color?: 'orange' | 'blue' | 'gold' | 'green'
}

const COLOR_CLASSES = {
  orange: 'bg-orange-50 text-orange-600 dark:bg-orange-950 dark:text-orange-400',
  blue: 'bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400',
  gold: 'bg-gold-light text-gold-dark dark:bg-gold/10 dark:text-gold',
  green: 'bg-green-50 text-green-600 dark:bg-green-950 dark:text-green-400',
}

export function StatCard({ icon: Icon, label, value, color = 'blue' }: StatCardProps) {
  return (
    <div className="bg-card border border-border rounded-2xl p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${COLOR_CLASSES[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <div className="font-serif text-2xl text-foreground leading-none">{value}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
      </div>
    </div>
  )
}

// ─── ProgressRing ─────────────────────────────────────────────────────────────

export function ProgressRing({ progress, size = 64 }: { progress: number; size?: number }) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--border))" strokeWidth={4} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#C8A96E" strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-medium text-foreground">{Math.round(progress)}%</span>
      </div>
    </div>
  )
}

// ─── LevelBadge ───────────────────────────────────────────────────────────────

const LEVEL_STYLES: Record<SkillLevel, string> = {
  beginner: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400',
  intermediate: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
  advanced: 'bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-400',
  expert: 'bg-gold-light text-gold-dark dark:bg-gold/10 dark:text-gold',
}

export function LevelBadge({ level, small = false }: { level: SkillLevel; small?: boolean }) {
  return (
    <span className={`inline-flex rounded-full font-medium capitalize ${LEVEL_STYLES[level]} ${
      small ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1'
    }`}>
      {level}
    </span>
  )
}

// ─── ResourceTypeBadge ────────────────────────────────────────────────────────

const TYPE_STYLES: Record<ResourceType, string> = {
  video: 'badge-video',
  course: 'badge-course',
  documentation: 'badge-docs',
  book: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
  paper: 'badge-paper',
  blog: 'badge-blog',
  github: 'badge-github',
  podcast: 'bg-pink-50 text-pink-700 dark:bg-pink-950 dark:text-pink-300',
}

export function ResourceTypeBadge({ type }: { type: ResourceType }) {
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full uppercase tracking-wide ${TYPE_STYLES[type]}`}>
      {type}
    </span>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

export function SkeletonCard({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-2xl ${className}`} />
}

// ─── SearchBar ────────────────────────────────────────────────────────────────

export function SearchBar({ placeholder }: { placeholder?: string }) {
  const router = useRouter()
  const { getToken } = useAuth()
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState<SkillLevel>('beginner')
  const { startGeneration, updateStatus, completeGeneration } = useGenerationStore()
  const { setQuery: storeSetQuery, setLevel: storeSetLevel } = useSearchStore()

  const handleSearch = async () => {
    if (!query.trim()) return
    storeSetQuery(query)
    storeSetLevel(level)
    startGeneration()
    router.push('/dashboard?generating=true')

    try {
      const token = await getToken()
      if (!token) return
      for await (const event of streamSSE<GenerationStatus>('/api/roadmaps/generate', { topic_query: query, level }, token)) {
        updateStatus(event)
        if (event.status === 'complete' && event.roadmap_id) {
          completeGeneration(event.roadmap_id)
          router.push(`/roadmap/${event.roadmap_id}`)
          return
        }
      }
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="flex items-center gap-2 bg-secondary/60 border border-border rounded-xl px-4 py-2.5 focus-within:border-gold/40 transition-colors">
      <Sparkles className="w-4 h-4 text-muted-foreground flex-shrink-0" />
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleSearch()}
        placeholder={placeholder || 'What do you want to learn?'}
        className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none font-light"
      />
      {query && (
        <button
          onClick={handleSearch}
          className="text-xs font-medium px-3 py-1.5 rounded-lg bg-foreground text-background hover:opacity-85 transition-opacity whitespace-nowrap"
        >
          Generate path
        </button>
      )}
    </div>
  )
}

// ─── GenerationProgress ───────────────────────────────────────────────────────

export function GenerationProgress({ status }: { status: GenerationStatus | null }) {
  if (!status) return null
  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="bg-card border border-border rounded-2xl p-5"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl bg-foreground flex items-center justify-center flex-shrink-0">
          <Loader2 className="w-4 h-4 text-background animate-spin" />
        </div>
        <div>
          <div className="text-sm font-medium text-foreground">Building your roadmap</div>
          <div className="text-xs text-muted-foreground font-light">{status.message}</div>
        </div>
        <div className="ml-auto text-sm font-medium text-gold">{status.progress}%</div>
      </div>
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-gold rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${status.progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
      <div className="flex items-center gap-6 mt-3 text-xs text-muted-foreground">
        {[
          { step: 'searching', label: 'Searching web' },
          { step: 'ranked', label: 'Ranking resources' },
          { step: 'curriculum', label: 'Building curriculum' },
          { step: 'saving', label: 'Saving roadmap' },
        ].map(({ step, label }) => {
          const steps = ['init', 'created', 'searching', 'searched', 'ranked', 'generating', 'curriculum', 'saving', 'complete']
          const currentIdx = steps.indexOf(status.status)
          const stepIdx = steps.indexOf(step)
          const done = currentIdx > stepIdx
          const active = currentIdx === stepIdx

          return (
            <div key={step} className={`flex items-center gap-1 transition-colors ${done ? 'text-success' : active ? 'text-foreground' : ''}`}>
              {done ? '✓' : active ? <Loader2 className="w-3 h-3 animate-spin" /> : '○'} {label}
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

// ─── RoadmapCard ─────────────────────────────────────────────────────────────

interface RoadmapCardProps {
  roadmap: RoadmapSummary
  onDelete: () => void
}

export function RoadmapCard({ roadmap, onDelete }: RoadmapCardProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="group bg-card border border-border rounded-2xl p-5 hover:border-gold/30 hover:shadow-sm transition-all duration-200"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <LevelBadge level={roadmap.level} small />
          <span className="text-xs text-muted-foreground">{roadmap.topic.title}</span>
        </div>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1 rounded-lg hover:bg-secondary transition-colors opacity-0 group-hover:opacity-100"
          >
            <MoreVertical className="w-4 h-4 text-muted-foreground" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-36 bg-card border border-border rounded-xl shadow-lg py-1 z-10">
              <button
                onClick={() => { onDelete(); setMenuOpen(false) }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-secondary/50 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete
              </button>
            </div>
          )}
        </div>
      </div>

      <h3 className="font-serif text-base text-foreground leading-tight mb-3 line-clamp-2">
        {roadmap.title}
      </h3>

      {/* Progress */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>Progress</span>
          <span>{Math.round(roadmap.completion_percentage)}%</span>
        </div>
        <div className="h-1 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-gold rounded-full transition-all duration-500"
            style={{ width: `${roadmap.completion_percentage}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {roadmap.estimated_hours && (
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {roadmap.estimated_hours}h</span>
          )}
        </div>
        <Link href={`/roadmap/${roadmap.id}`}>
          <button className="text-xs font-medium text-foreground hover:text-gold transition-colors flex items-center gap-1">
            Continue <ExternalLink className="w-3 h-3" />
          </button>
        </Link>
      </div>
    </motion.div>
  )
}
