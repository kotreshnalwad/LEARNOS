'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Send, Sparkles, RotateCcw, Lightbulb } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTutorStore } from '@/stores'
import { streamSSE } from '@/lib/api'
import { useGetSuggestions } from '@/hooks/useApi'
import type { Lesson } from '@/types'

interface TutorPanelProps {
  lesson: Lesson
  roadmapTitle?: string
}

export function TutorPanel({ lesson, roadmapTitle }: TutorPanelProps) {
  const { getToken } = useAuth()
  const {
    isOpen, closeTutor, messages, isStreaming, streamingContent,
    addMessage, startStream, appendStream, finalizeStream, clearHistory
  } = useTutorStore()

  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([
    'Explain this concept simply',
    'Give me a practical example',
    'What are common mistakes to avoid?',
  ])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { mutate: getSuggestions } = useGetSuggestions()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const sendMessage = async (text = input) => {
    const msg = text.trim()
    if (!msg || isStreaming) return

    setInput('')
    addMessage({ role: 'user', content: msg, timestamp: new Date().toISOString() })
    startStream()

    try {
      const token = await getToken()
      if (!token) return

      for await (const event of streamSSE<{ chunk: string }>(
        '/api/tutor/chat',
        {
          lesson_id: lesson.id,
          message: msg,
          conversation_history: messages.slice(-8),
        },
        token
      )) {
        if (event.chunk) appendStream(event.chunk)
      }
    } catch (err) {
      appendStream('\n\n*Connection error. Please try again.*')
    } finally {
      finalizeStream()

      // Get new suggestions after assistant responds
      getSuggestions(
        { lesson_id: lesson.id, message: msg, conversation_history: messages },
        { onSuccess: (data) => setSuggestions(data.suggestions) }
      )
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <motion.div
      initial={{ x: 380, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 380, opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 300 }}
      className="fixed right-0 top-[60px] bottom-0 w-[380px] bg-foreground text-background flex flex-col border-l border-background/10 z-40"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-background/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gold flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-background" />
          </div>
          <div>
            <div className="text-sm font-medium">AI Tutor</div>
            <div className="text-xs text-background/50 truncate max-w-[200px]">{lesson.title}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearHistory}
            className="p-1.5 rounded-lg hover:bg-background/10 transition-colors text-background/60 hover:text-background"
            title="Clear history"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={closeTutor}
            className="p-1.5 rounded-lg hover:bg-background/10 transition-colors text-background/60 hover:text-background"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.length === 0 && (
          <div className="text-center pt-6">
            <div className="w-12 h-12 rounded-2xl bg-background/10 flex items-center justify-center mx-auto mb-4">
              <Lightbulb className="w-6 h-6 text-gold" />
            </div>
            <p className="text-sm text-background/60 font-light">
              I'm here to help you master <strong className="text-background/80 font-medium">{lesson.title}</strong>.
              Ask me anything about the lesson.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-gold text-background/90 rounded-br-sm font-light'
                : 'bg-background/10 text-background/90 rounded-bl-sm'
            }`}>
              {msg.role === 'assistant' ? (
                <div className="prose-lesson prose-sm prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
          </motion.div>
        ))}

        {/* Streaming message */}
        {isStreaming && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="max-w-[88%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm bg-background/10 text-background/90">
              {streamingContent ? (
                <div className="prose-lesson prose-sm prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-gold animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gold animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-gold animate-bounce [animation-delay:300ms]" />
                </div>
              )}
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {!isStreaming && suggestions.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => sendMessage(s)}
              className="text-xs px-3 py-1.5 rounded-full bg-background/10 text-background/70 hover:bg-background/20 hover:text-background transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-background/10">
        <div className="flex items-end gap-2 bg-background/10 rounded-xl px-4 py-2.5">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about this lesson…"
            rows={1}
            className="flex-1 bg-transparent text-sm text-background placeholder:text-background/40 outline-none resize-none font-light"
            style={{ maxHeight: 120 }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isStreaming}
            className="w-8 h-8 rounded-lg bg-gold flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-85 transition-opacity flex-shrink-0"
          >
            <Send className="w-3.5 h-3.5 text-background" />
          </button>
        </div>
        <p className="text-xs text-background/30 text-center mt-2">Enter to send · Shift+Enter for new line</p>
      </div>
    </motion.div>
  )
}
