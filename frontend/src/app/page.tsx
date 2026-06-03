'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@clerk/nextjs'
import { Sparkles, ArrowRight, BookOpen, Zap, Target, RefreshCw, Brain, Star } from 'lucide-react'
import Link from 'next/link'
import { useSearchStore, useGenerationStore } from '@/stores'
import { streamSSE } from '@/lib/api'
import type { GenerationStatus, SkillLevel } from '@/types'

const TRENDING = ['Machine Learning', 'Python', 'React', 'Cybersecurity', 'Digital Marketing', 'RAG Systems', 'UI/UX Design', 'Blockchain', 'Finance', 'Data Science']

const LEVELS: { value: SkillLevel; label: string; desc: string }[] = [
  { value: 'beginner', label: 'Beginner', desc: 'No prior knowledge' },
  { value: 'intermediate', label: 'Intermediate', desc: 'Some experience' },
  { value: 'advanced', label: 'Advanced', desc: 'Strong foundation' },
  { value: 'expert', label: 'Expert', desc: 'Deep expertise' },
]

const FEATURES = [
  { icon: Zap, title: 'Instant Discovery', desc: 'AI scans courses, YouTube, papers, GitHub, and documentation in seconds.' },
  { icon: Target, title: 'Quality Ranked', desc: 'Every resource scored on authority, freshness, popularity, and completeness.' },
  { icon: BookOpen, title: 'Structured Curriculum', desc: 'Modules, lessons, milestones, and projects — all designed in order.' },
  { icon: Brain, title: 'AI Tutor', desc: 'Ask anything, anytime. Claude explains, quizzes you, and adapts to you.' },
  { icon: RefreshCw, title: 'Always Updated', desc: 'Roadmap refreshes automatically when better resources appear online.' },
  { icon: Star, title: 'Mastery Gating', desc: 'Advance only when you truly understand. Progress that actually means something.' },
]

export default function LandingPage() {
  const router = useRouter()
  const { isSignedIn, getToken } = useAuth()
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState<SkillLevel>('beginner')
  const [showLevels, setShowLevels] = useState(false)
  const { updateStatus, startGeneration, completeGeneration } = useGenerationStore()
  const { setQuery: storeSetQuery, setLevel: storeSetLevel } = useSearchStore()
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) { inputRef.current?.focus(); return }
    if (!isSignedIn) { router.push('/sign-in'); return }

    storeSetQuery(searchQuery)
    storeSetLevel(level)
    startGeneration()
    router.push('/dashboard?generating=true')

    try {
      const token = await getToken()
      if (!token) return

      for await (const event of streamSSE<GenerationStatus>(
        '/api/roadmaps/generate',
        { topic_query: searchQuery, level },
        token
      )) {
        updateStatus(event)
        if (event.status === 'complete' && event.roadmap_id) {
          completeGeneration(event.roadmap_id)
          router.push(`/roadmap/${event.roadmap_id}`)
          return
        }
      }
    } catch (err) {
      console.error('Generation failed', err)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b border-border/60 bg-background/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-[60px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-foreground flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-background" />
            </div>
            <span className="font-serif text-lg font-medium">LearnOS</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="#features" className="hover:text-foreground transition-colors">Features</Link>
            <Link href="#how" className="hover:text-foreground transition-colors">How it works</Link>
          </div>
          <div className="flex items-center gap-3">
            {isSignedIn ? (
              <Link href="/dashboard">
                <button className="text-sm font-medium px-4 py-2 rounded-full bg-foreground text-background hover:opacity-85 transition-opacity">
                  Dashboard
                </button>
              </Link>
            ) : (
              <>
                <Link href="/sign-in" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Sign in</Link>
                <Link href="/sign-up">
                  <button className="text-sm font-medium px-4 py-2 rounded-full bg-foreground text-background hover:opacity-85 transition-opacity">
                    Get started
                  </button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 text-xs font-medium tracking-widest uppercase text-gold mb-6 border border-gold/30 rounded-full px-4 py-1.5 bg-gold-light/30">
            <Sparkles className="w-3 h-3" />
            AI Learning Operating System
          </div>

          <h1 className="font-serif text-5xl md:text-7xl text-foreground mb-6 leading-[1.05] tracking-tight">
            What do you want
            <br />
            to <em className="text-gold">master</em>?
          </h1>

          <p className="text-lg text-muted-foreground max-w-xl mx-auto mb-10 font-light leading-relaxed">
            Type any topic. AI researches the internet, curates the best resources,
            and builds your personalized curriculum — in minutes.
          </p>

          {/* Search */}
          <div className="relative max-w-2xl mx-auto">
            <div className="flex items-center gap-3 bg-card border border-border rounded-2xl p-2 pl-5 shadow-sm focus-within:border-gold/60 focus-within:shadow-gold/10 focus-within:shadow-lg transition-all duration-300">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder='Try "Machine Learning" or "Python"…'
                className="flex-1 bg-transparent text-base font-light text-foreground placeholder:text-muted-foreground outline-none"
              />
              {/* Level selector */}
              <div className="relative">
                <button
                  onClick={() => setShowLevels(!showLevels)}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground hover:bg-muted transition-colors whitespace-nowrap"
                >
                  {LEVELS.find(l => l.value === level)?.label} ▾
                </button>
                <AnimatePresence>
                  {showLevels && (
                    <motion.div
                      initial={{ opacity: 0, y: 4, scale: 0.97 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.97 }}
                      className="absolute right-0 top-full mt-2 w-48 bg-card border border-border rounded-xl shadow-lg p-1 z-50"
                    >
                      {LEVELS.map(l => (
                        <button
                          key={l.value}
                          onClick={() => { setLevel(l.value); setShowLevels(false) }}
                          className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${level === l.value ? 'bg-secondary font-medium' : 'hover:bg-secondary/50'}`}
                        >
                          <div className="font-medium">{l.label}</div>
                          <div className="text-xs text-muted-foreground">{l.desc}</div>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <button
                onClick={() => handleSearch()}
                className="flex items-center gap-2 bg-foreground text-background text-sm font-medium px-5 py-2.5 rounded-xl hover:opacity-85 transition-opacity whitespace-nowrap"
              >
                <Sparkles className="w-4 h-4" />
                Generate path
              </button>
            </div>
          </div>

          {/* Trending chips */}
          <div className="flex flex-wrap gap-2 justify-center mt-6">
            {TRENDING.map((topic) => (
              <button
                key={topic}
                onClick={() => { setQuery(topic); handleSearch(topic) }}
                className="text-sm text-muted-foreground bg-secondary hover:bg-gold-light hover:text-gold-dark hover:border-gold/40 border border-transparent px-3.5 py-1.5 rounded-full transition-all duration-200"
              >
                {topic}
              </button>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Stats bar */}
      <div className="border-y border-border/60 bg-secondary/40 py-5">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-center gap-12 text-sm text-muted-foreground">
          {[
            { label: 'Topics covered', value: '500+' },
            { label: 'Resources indexed', value: '2M+' },
            { label: 'Avg completion rate', value: '94%' },
            { label: 'Learners', value: '50K+' },
          ].map(stat => (
            <div key={stat.label} className="text-center hidden sm:block">
              <div className="font-serif text-2xl text-foreground">{stat.value}</div>
              <div className="text-xs mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <div className="text-xs font-medium tracking-widest uppercase text-gold mb-3">How it works</div>
          <h2 className="font-serif text-4xl text-foreground tracking-tight">
            Your personal <em>learning architect</em>
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              viewport={{ once: true }}
              className="bg-card border border-border rounded-2xl p-6 hover:border-gold/30 hover:shadow-sm transition-all duration-300"
            >
              <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center mb-4">
                <f.icon className="w-5 h-5 text-foreground/70" />
              </div>
              <h3 className="font-medium text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed font-light">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-foreground text-background py-20 text-center">
        <div className="max-w-2xl mx-auto px-6">
          <h2 className="font-serif text-4xl md:text-5xl mb-4 leading-tight">
            Start learning <em>anything</em><br />in 60 seconds.
          </h2>
          <p className="text-background/70 mb-8 font-light">
            Enter a topic. AI does the rest.
          </p>
          <Link href={isSignedIn ? '/dashboard' : '/sign-up'}>
            <button className="inline-flex items-center gap-2 bg-gold text-gold-dark font-medium px-8 py-4 rounded-full text-base hover:opacity-90 transition-opacity">
              Get started free <ArrowRight className="w-4 h-4" />
            </button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 text-center text-sm text-muted-foreground">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Sparkles className="w-4 h-4" />
          <span className="font-serif">LearnOS AI</span>
        </div>
        <p>Master Anything. AI Builds The Path.</p>
      </footer>
    </div>
  )
}
