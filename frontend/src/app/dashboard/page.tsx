'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { useUser } from '@clerk/nextjs'
import { Flame, Clock, Trophy, Zap, BookOpen, Target, Plus, ArrowRight, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useRoadmaps, useDashboardStats, useDeleteRoadmap } from '@/hooks/useApi'
import { useGenerationStore } from '@/stores'
import { AppShell } from '@/components/layout/AppShell'
import { GenerationProgress } from '@/components/shared/GenerationProgress'
import { RoadmapCard } from '@/components/shared/RoadmapCard'
import { StatCard } from '@/components/shared/StatCard'
import { SkeletonCard } from '@/components/shared/Skeleton'
import { SearchBar } from '@/components/shared/SearchBar'

export default function DashboardPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user } = useUser()
  const isGenerating = searchParams.get('generating') === 'true'

  const { data: roadmaps, isLoading: roadmapsLoading } = useRoadmaps()
  const { data: stats, isLoading: statsLoading } = useDashboardStats()
  const { mutate: deleteRoadmap } = useDeleteRoadmap()
  const { status, roadmapId } = useGenerationStore()

  // Redirect to roadmap when generation completes
  useEffect(() => {
    if (roadmapId && !isGenerating) {
      router.push(`/roadmap/${roadmapId}`)
    }
  }, [roadmapId, isGenerating, router])

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8 animate-fade-in">

        {/* Generation overlay */}
        <AnimatePresence>
          {isGenerating && (
            <GenerationProgress status={status} />
          )}
        </AnimatePresence>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-serif text-3xl text-foreground">
              {greeting()}, <em>{user?.firstName || 'Learner'}</em>
            </h1>
            <p className="text-muted-foreground mt-1 font-light">
              {stats?.current_streak ? `🔥 ${stats.current_streak} day streak — keep it going!` : 'Start your learning journey today.'}
            </p>
          </div>
        </div>

        {/* Search bar */}
        <SearchBar placeholder="What do you want to learn today?" />

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statsLoading ? (
            Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-24" />)
          ) : (
            <>
              <StatCard icon={Flame} label="Day streak" value={stats?.current_streak ?? 0} color="orange" />
              <StatCard icon={Clock} label="Hours learned" value={`${stats?.total_hours_learned ?? 0}h`} color="blue" />
              <StatCard icon={Trophy} label="XP earned" value={(stats?.xp_points ?? 0).toLocaleString()} color="gold" />
              <StatCard icon={BookOpen} label="Lessons done" value={stats?.total_lessons_completed ?? 0} color="green" />
            </>
          )}
        </div>

        {/* Roadmaps section */}
        <div>
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-serif text-xl text-foreground">Your Learning Paths</h2>
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors">
              <Plus className="w-4 h-4" /> New roadmap
            </Link>
          </div>

          {roadmapsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} className="h-44" />)}
            </div>
          ) : roadmaps?.length === 0 ? (
            <EmptyRoadmaps />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {roadmaps?.map((roadmap) => (
                <RoadmapCard
                  key={roadmap.id}
                  roadmap={roadmap}
                  onDelete={() => deleteRoadmap(roadmap.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

function EmptyRoadmaps() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-dashed border-border rounded-2xl p-12 text-center"
    >
      <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
        <Target className="w-7 h-7 text-muted-foreground" />
      </div>
      <h3 className="font-serif text-xl text-foreground mb-2">No learning paths yet</h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-xs mx-auto font-light">
        Search any topic and AI will build your personalized curriculum in minutes.
      </p>
      <Link href="/">
        <button className="inline-flex items-center gap-2 bg-foreground text-background text-sm font-medium px-5 py-2.5 rounded-full hover:opacity-85 transition-opacity">
          Create your first roadmap <ArrowRight className="w-4 h-4" />
        </button>
      </Link>
    </motion.div>
  )
}
