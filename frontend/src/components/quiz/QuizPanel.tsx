'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, Clock, Zap, Trophy, RotateCcw, ArrowRight } from 'lucide-react'
import { useSubmitQuiz } from '@/hooks/useApi'
import type { Quiz, QuizResult as QuizResultType } from '@/types'

interface QuizPanelProps {
  quiz: Quiz
  lessonId: string
}

type QuizState = 'idle' | 'active' | 'submitted'

export function QuizPanel({ quiz, lessonId }: QuizPanelProps) {
  const [state, setState] = useState<QuizState>('idle')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [currentIdx, setCurrentIdx] = useState(0)
  const [timeLeft, setTimeLeft] = useState(quiz.time_limit_minutes ? quiz.time_limit_minutes * 60 : null)
  const [timeStart, setTimeStart] = useState(0)
  const [result, setResult] = useState<QuizResultType | null>(null)
  const { mutate: submitQuiz, isPending } = useSubmitQuiz()

  const questions = quiz.questions.sort((a, b) => a.order - b.order)
  const currentQ = questions[currentIdx]
  const isLast = currentIdx === questions.length - 1
  const answered = !!answers[currentQ?.id]

  // Timer
  useEffect(() => {
    if (state !== 'active' || !timeLeft) return
    const timer = setInterval(() => {
      setTimeLeft(t => {
        if (t === null || t <= 1) { handleSubmit(); return 0 }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [state, timeLeft])

  const startQuiz = () => {
    setState('active')
    setTimeStart(Date.now())
    setCurrentIdx(0)
    setAnswers({})
  }

  const selectAnswer = (questionId: string, answer: string) => {
    if (state !== 'active') return
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
  }

  const handleSubmit = useCallback(() => {
    const timeTaken = Math.floor((Date.now() - timeStart) / 1000)
    submitQuiz(
      { quiz_id: quiz.id, answers, time_taken_seconds: timeTaken },
      {
        onSuccess: (data) => {
          setResult(data)
          setState('submitted')
        },
        onError: () => {
          setState('submitted')
        },
      }
    )
  }, [answers, quiz.id, timeStart, submitQuiz])

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  if (state === 'idle') {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
          <Trophy className="w-8 h-8 text-gold" />
        </div>
        <h3 className="font-serif text-xl mb-2">Lesson Quiz</h3>
        <p className="text-sm text-muted-foreground mb-2 font-light">
          {questions.length} questions · Pass at {quiz.passing_score}%
        </p>
        {quiz.time_limit_minutes && (
          <p className="text-sm text-muted-foreground mb-6 flex items-center justify-center gap-1">
            <Clock className="w-4 h-4" /> {quiz.time_limit_minutes} minute time limit
          </p>
        )}
        <button
          onClick={startQuiz}
          className="bg-foreground text-background text-sm font-medium px-8 py-3 rounded-full hover:opacity-85 transition-opacity"
        >
          Start quiz
        </button>
      </div>
    )
  }

  if (state === 'submitted' && result) {
    return <QuizResultView result={result} quiz={quiz} onRetry={() => { setState('idle'); setResult(null) }} />
  }

  return (
    <div className="space-y-6">
      {/* Progress header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Question {currentIdx + 1} of {questions.length}
        </div>
        {timeLeft !== null && (
          <div className={`flex items-center gap-1.5 text-sm font-medium ${timeLeft < 60 ? 'text-destructive' : 'text-muted-foreground'}`}>
            <Clock className="w-4 h-4" /> {formatTime(timeLeft)}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-secondary rounded-full">
        <div
          className="h-full bg-gold rounded-full transition-all duration-300"
          style={{ width: `${((currentIdx) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQ.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <h3 className="font-medium text-foreground text-base leading-relaxed mb-5">
            {currentQ.question}
          </h3>

          {/* Options */}
          <div className="space-y-2.5">
            {currentQ.options?.map((option) => {
              const selected = answers[currentQ.id] === option
              return (
                <button
                  key={option}
                  onClick={() => selectAnswer(currentQ.id, option)}
                  className={`w-full text-left px-4 py-3.5 rounded-xl border text-sm transition-all duration-150 ${
                    selected
                      ? 'border-gold bg-gold-light/30 text-foreground font-medium'
                      : 'border-border hover:border-muted-foreground/40 hover:bg-secondary/30 text-foreground/80'
                  }`}
                >
                  {option}
                </button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => setCurrentIdx(i => Math.max(0, i - 1))}
          disabled={currentIdx === 0}
          className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        {isLast ? (
          <button
            onClick={handleSubmit}
            disabled={isPending || Object.keys(answers).length === 0}
            className="flex items-center gap-2 bg-foreground text-background text-sm font-medium px-6 py-2.5 rounded-full hover:opacity-85 transition-opacity disabled:opacity-40"
          >
            {isPending ? 'Grading…' : 'Submit quiz'} <Zap className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={() => setCurrentIdx(i => Math.min(questions.length - 1, i + 1))}
            disabled={!answered}
            className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-foreground/70 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Answer dots */}
      <div className="flex justify-center gap-1.5 pt-2">
        {questions.map((q, i) => (
          <button
            key={q.id}
            onClick={() => setCurrentIdx(i)}
            className={`w-2 h-2 rounded-full transition-all ${
              i === currentIdx ? 'bg-foreground scale-125' :
              answers[q.id] ? 'bg-gold' : 'bg-border'
            }`}
          />
        ))}
      </div>
    </div>
  )
}

function QuizResultView({ result, quiz, onRetry }: { result: QuizResultType; quiz: Quiz; onRetry: () => void }) {
  const passed = result.passed
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center py-6 space-y-6"
    >
      <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto ${
        passed ? 'bg-success/10' : 'bg-destructive/10'
      }`}>
        {passed
          ? <Trophy className="w-9 h-9 text-success" />
          : <XCircle className="w-9 h-9 text-destructive" />
        }
      </div>

      <div>
        <div className="font-serif text-4xl text-foreground mb-1">{Math.round(result.score)}%</div>
        <div className={`text-sm font-medium ${passed ? 'text-success' : 'text-destructive'}`}>
          {passed ? '🎉 Passed!' : 'Not quite there yet'}
        </div>
        <div className="text-xs text-muted-foreground mt-1">Pass score: {quiz.passing_score}%</div>
      </div>

      {passed && (
        <div className="flex items-center justify-center gap-2 text-sm text-gold font-medium">
          <Zap className="w-4 h-4" /> +{result.xp_earned} XP earned
        </div>
      )}

      {/* Per-question feedback */}
      <div className="text-left space-y-2 max-h-48 overflow-y-auto">
        {Object.entries(result.feedback).map(([qId, fb]) => (
          <div key={qId} className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
            fb.correct ? 'bg-success/5 border border-success/20' : 'bg-destructive/5 border border-destructive/20'
          }`}>
            {fb.correct
              ? <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
              : <XCircle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
            }
            <div>
              {!fb.correct && (
                <div className="text-xs text-muted-foreground">Correct: {fb.correct_answer}</div>
              )}
              {fb.explanation && (
                <div className="text-xs text-muted-foreground mt-0.5">{fb.explanation}</div>
              )}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onRetry}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <RotateCcw className="w-4 h-4" /> Retry quiz
      </button>
    </motion.div>
  )
}
