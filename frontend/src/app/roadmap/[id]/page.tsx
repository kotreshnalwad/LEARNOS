'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Lock, CheckCircle, Play, ChevronDown, ChevronRight, Clock, Zap, Target, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { useRoadmap, useUpdateProgress } from '@/hooks/useApi'
import { AppShell } from '@/components/layout/AppShell'
import { ProgressRing } from '@/components/shared/ProgressRing'
import { LevelBadge } from '@/components/shared/LevelBadge'
import { SkeletonCard } from '@/components/shared/Skeleton'
import type { Module, Lesson, LessonStatus } from '@/types'

export default function RoadmapPage() {
  const params = useParams()
  const router = useRouter()
  const roadmapId = params.id as string
  const { data: roadmap, isLoading, error } = useRoadmap(roadmapId)
  const { mutate: updateProgress } = useUpdateProgress()
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set())

  if (isLoading) return <AppShell><RoadmapSkeleton /></AppShell>
  if (error || !roadmap) return <AppShell><div className="p-8 text-muted-foreground">Roadmap not found.</div></AppShell>

  const toggleModule = (id: string) => {
    setExpandedModules(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleStartLesson = (lesson: Lesson, module: Module) => {
    if (!module.is_unlocked) return
    updateProgress({ lesson_id: lesson.id, status: 'in_progress' })
    router.push(`/lesson/${lesson.id}?roadmap=${roadmapId}`)
  }

  const getLessonIcon = (status: LessonStatus | undefined, isUnlocked: boolean) => {
    if (!isUnlocked) return <Lock className="w-4 h-4 text-muted-foreground/50" />
    if (status === 'completed') return <CheckCircle className="w-4 h-4 text-success" />
    if (status === 'in_progress') return <Play className="w-4 h-4 text-gold fill-gold" />
    return <div className="w-4 h-4 rounded-full border-2 border-border" />
  }

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-6 py-8 animate-fade-in">
        {/* Back */}
        <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </Link>

        {/* Header */}
        <div className="flex items-start gap-5 mb-8">
          <ProgressRing progress={roadmap.completion_percentage} size={72} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <LevelBadge level={roadmap.level} />
              <span className="text-xs text-muted-foreground">{roadmap.topic.title}</span>
            </div>
            <h1 className="font-serif text-2xl text-foreground leading-tight mb-1">{roadmap.title}</h1>
            {roadmap.description && (
              <p className="text-sm text-muted-foreground font-light leading-relaxed">{roadmap.description}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              {roadmap.estimated_hours && (
                <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {roadmap.estimated_hours}h total</span>
              )}
              <span className="flex items-center gap-1"><Target className="w-3.5 h-3.5" /> {roadmap.modules.length} modules</span>
              <span className="flex items-center gap-1"><Zap className="w-3.5 h-3.5" />
                {roadmap.modules.reduce((acc, m) => acc + m.lessons.length, 0)} lessons
              </span>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
            <span>Overall progress</span>
            <span>{Math.round(roadmap.completion_percentage)}%</span>
          </div>
          <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gold rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${roadmap.completion_percentage}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Module tree */}
        <div className="space-y-3">
          {roadmap.modules.map((module, idx) => {
            const isExpanded = expandedModules.has(module.id)
            const completedLessons = module.lessons.filter(l => l.status === 'completed').length

            return (
              <motion.div
                key={module.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.06 }}
                className={`border rounded-2xl overflow-hidden transition-all duration-200 ${
                  !module.is_unlocked
                    ? 'border-border/50 opacity-60'
                    : isExpanded
                    ? 'border-gold/40 shadow-sm'
                    : 'border-border hover:border-border/80'
                }`}
              >
                {/* Module header */}
                <button
                  onClick={() => module.is_unlocked && toggleModule(module.id)}
                  className="w-full flex items-center gap-4 p-5 text-left bg-card"
                  disabled={!module.is_unlocked}
                >
                  {/* Order badge */}
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
                    module.is_unlocked ? 'bg-foreground text-background' : 'bg-secondary text-muted-foreground'
                  }`}>
                    {module.is_unlocked ? idx + 1 : <Lock className="w-4 h-4" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-foreground text-sm">{module.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {completedLessons}/{module.lessons.length} lessons
                      {module.estimated_hours && ` · ${module.estimated_hours}h`}
                    </div>
                    {/* Module progress bar */}
                    {module.is_unlocked && (
                      <div className="mt-2 h-1 bg-secondary rounded-full overflow-hidden w-32">
                        <div
                          className="h-full bg-gold rounded-full transition-all duration-500"
                          style={{ width: `${module.completion_percentage}%` }}
                        />
                      </div>
                    )}
                  </div>

                  {module.is_unlocked && (
                    <div className="text-muted-foreground flex-shrink-0">
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </div>
                  )}
                </button>

                {/* Lessons list */}
                <AnimatePresence>
                  {isExpanded && module.is_unlocked && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: 'easeInOut' }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-border divide-y divide-border/60">
                        {module.lessons.map((lesson) => (
                          <button
                            key={lesson.id}
                            onClick={() => handleStartLesson(lesson, module)}
                            className={`w-full flex items-center gap-4 px-5 py-3.5 text-left bg-card hover:bg-secondary/30 transition-colors ${
                              lesson.status === 'completed' ? 'opacity-70' : ''
                            }`}
                          >
                            <div className="flex-shrink-0 ml-1">
                              {getLessonIcon(lesson.status, module.is_unlocked)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-foreground truncate">{lesson.title}</div>
                              <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" /> {lesson.estimated_minutes}m
                                </span>
                                <span className="flex items-center gap-1">
                                  <Zap className="w-3 h-3" /> {lesson.xp_reward} XP
                                </span>
                                {lesson.resources.length > 0 && (
                                  <span>{lesson.resources.length} resources</span>
                                )}
                              </div>
                            </div>
                            {lesson.mastery_score && lesson.mastery_score > 0 && (
                              <div className="text-xs font-medium text-success">
                                {Math.round(lesson.mastery_score * 100)}%
                              </div>
                            )}
                            <ChevronRight className="w-4 h-4 text-muted-foreground/50 flex-shrink-0" />
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </div>
      </div>
    </AppShell>
  )
}

function RoadmapSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-4">
      <SkeletonCard className="h-24" />
      <SkeletonCard className="h-2" />
      {Array.from({ length: 4 }).map((_, i) => (
        <SkeletonCard key={i} className="h-16" />
      ))}
    </div>
  )
}
