'use client'

import { motion } from 'framer-motion'
import { useUser } from '@clerk/nextjs'
import { Flame, Zap, Trophy, BookOpen, Clock, Target, Award, BarChart2 } from 'lucide-react'
import { useDashboardStats, useRoadmaps } from '@/hooks/useApi'
import { AppShell } from '@/components/layout/AppShell'
import { StatCard, LevelBadge, SkeletonCard, ProgressRing } from '@/components/shared'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

const BADGES = [
  { icon: '🚀', name: 'First Steps', desc: 'Completed your first lesson', earned: true },
  { icon: '🔥', name: 'On Fire', desc: '7-day learning streak', earned: true },
  { icon: '🧠', name: 'Deep Thinker', desc: 'Scored 90%+ on 5 quizzes', earned: false },
  { icon: '⚡', name: 'Speed Learner', desc: 'Completed 3 lessons in one day', earned: false },
  { icon: '🏆', name: 'Roadmap Master', desc: 'Completed an entire roadmap', earned: false },
  { icon: '💎', name: 'Expert', desc: 'Reached expert level in any topic', earned: false },
]

export default function ProfilePage() {
  const { user } = useUser()
  const { data: stats, isLoading } = useDashboardStats()
  const { data: roadmaps } = useRoadmaps()

  const skillData = roadmaps?.slice(0, 5).map(r => ({
    topic: r.topic.title.slice(0, 12),
    progress: Math.round(r.completion_percentage),
  })) || []

  const activityData = Array.from({ length: 7 }, (_, i) => ({
    day: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
    minutes: Math.floor(Math.random() * 90),
  }))

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8 animate-fade-in">

        {/* Profile header */}
        <div className="flex items-center gap-5">
          <div className="relative">
            {user?.imageUrl ? (
              <img src={user.imageUrl} alt={user.fullName || ''} className="w-20 h-20 rounded-2xl object-cover" />
            ) : (
              <div className="w-20 h-20 rounded-2xl bg-secondary flex items-center justify-center text-2xl font-serif">
                {user?.firstName?.[0] || '?'}
              </div>
            )}
            <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-gold flex items-center justify-center text-xs text-background font-bold">
              {stats ? Math.floor(stats.xp_points / 500) + 1 : 1}
            </div>
          </div>
          <div>
            <h1 className="font-serif text-2xl text-foreground">{user?.fullName || 'Learner'}</h1>
            <p className="text-muted-foreground text-sm font-light">{user?.primaryEmailAddress?.emailAddress}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs bg-gold-light text-gold-dark px-2.5 py-1 rounded-full font-medium">
                Level {stats ? Math.floor(stats.xp_points / 500) + 1 : 1} Learner
              </span>
              <span className="text-xs text-muted-foreground">
                {stats ? `${stats.xp_points % 500} / 500 XP to next level` : ''}
              </span>
            </div>
          </div>
        </div>

        {/* XP progress bar */}
        {stats && (
          <div>
            <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
              <span className="flex items-center gap-1"><Zap className="w-3 h-3 text-gold" /> {stats.xp_points.toLocaleString()} XP total</span>
              <span>Next level: {(Math.floor(stats.xp_points / 500) + 1) * 500} XP</span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-gold to-gold-light rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${(stats.xp_points % 500) / 500 * 100}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
            </div>
          </div>
        )}

        {/* Stats grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-24" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Flame} label="Day streak" value={stats?.current_streak ?? 0} color="orange" />
            <StatCard icon={Clock} label="Hours learned" value={`${stats?.total_hours_learned ?? 0}h`} color="blue" />
            <StatCard icon={BookOpen} label="Completed" value={stats?.total_lessons_completed ?? 0} color="green" />
            <StatCard icon={Target} label="Avg mastery" value={`${Math.round((stats?.average_mastery_score ?? 0) * 100)}%`} color="gold" />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Activity chart */}
          <div className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart2 className="w-4 h-4 text-muted-foreground" />
              <h2 className="font-medium text-foreground text-sm">Weekly Activity</h2>
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={activityData} barSize={20}>
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  formatter={(v: number) => [`${v} min`, 'Time spent']}
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="minutes" fill="#C8A96E" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Skill radar */}
          {skillData.length > 2 && (
            <div className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4 text-muted-foreground" />
                <h2 className="font-medium text-foreground text-sm">Skill Progress</h2>
              </div>
              <ResponsiveContainer width="100%" height={140}>
                <RadarChart data={skillData}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="topic" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <Radar dataKey="progress" fill="#C8A96E" fillOpacity={0.2} stroke="#C8A96E" strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Badges */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Award className="w-4 h-4 text-muted-foreground" />
            <h2 className="font-medium text-foreground">Badges</h2>
            <span className="text-xs text-muted-foreground ml-auto">
              {BADGES.filter(b => b.earned).length}/{BADGES.length} earned
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {BADGES.map((badge) => (
              <motion.div
                key={badge.name}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`border rounded-xl p-4 flex items-center gap-3 transition-all ${
                  badge.earned
                    ? 'border-gold/30 bg-gold-light/20'
                    : 'border-border opacity-40 grayscale'
                }`}
              >
                <span className="text-2xl">{badge.icon}</span>
                <div>
                  <div className="text-sm font-medium text-foreground">{badge.name}</div>
                  <div className="text-xs text-muted-foreground font-light">{badge.desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Roadmap progress list */}
        {roadmaps && roadmaps.length > 0 && (
          <div>
            <h2 className="font-medium text-foreground mb-4">Learning Paths</h2>
            <div className="space-y-3">
              {roadmaps.map((roadmap) => (
                <div key={roadmap.id} className="flex items-center gap-4 bg-card border border-border rounded-xl p-4">
                  <ProgressRing progress={roadmap.completion_percentage} size={48} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">{roadmap.title}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <LevelBadge level={roadmap.level} small />
                      <span className="text-xs text-muted-foreground">{roadmap.topic.title}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}
