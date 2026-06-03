import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import type { GenerationStatus, TutorMessage, SkillLevel } from '@/types'

// ─── Roadmap Generation Store ─────────────────────────────────────────────────

interface GenerationStore {
  isGenerating: boolean
  status: GenerationStatus | null
  roadmapId: string | null
  startGeneration: () => void
  updateStatus: (status: GenerationStatus) => void
  completeGeneration: (roadmapId: string) => void
  resetGeneration: () => void
}

export const useGenerationStore = create<GenerationStore>()(
  immer((set) => ({
    isGenerating: false,
    status: null,
    roadmapId: null,
    startGeneration: () =>
      set((s) => {
        s.isGenerating = true
        s.status = null
        s.roadmapId = null
      }),
    updateStatus: (status) =>
      set((s) => {
        s.status = status
        if (status.roadmap_id) s.roadmapId = status.roadmap_id
      }),
    completeGeneration: (roadmapId) =>
      set((s) => {
        s.isGenerating = false
        s.roadmapId = roadmapId
      }),
    resetGeneration: () =>
      set((s) => {
        s.isGenerating = false
        s.status = null
        s.roadmapId = null
      }),
  }))
)

// ─── Tutor Store ──────────────────────────────────────────────────────────────

interface TutorStore {
  isOpen: boolean
  lessonId: string | null
  messages: TutorMessage[]
  isStreaming: boolean
  streamingContent: string
  openTutor: (lessonId: string) => void
  closeTutor: () => void
  addMessage: (msg: TutorMessage) => void
  startStream: () => void
  appendStream: (chunk: string) => void
  finalizeStream: () => void
  clearHistory: () => void
}

export const useTutorStore = create<TutorStore>()(
  immer((set) => ({
    isOpen: false,
    lessonId: null,
    messages: [],
    isStreaming: false,
    streamingContent: '',
    openTutor: (lessonId) =>
      set((s) => {
        s.isOpen = true
        if (s.lessonId !== lessonId) {
          s.lessonId = lessonId
          s.messages = []
        }
      }),
    closeTutor: () => set((s) => { s.isOpen = false }),
    addMessage: (msg) => set((s) => { s.messages.push(msg) }),
    startStream: () =>
      set((s) => {
        s.isStreaming = true
        s.streamingContent = ''
      }),
    appendStream: (chunk) => set((s) => { s.streamingContent += chunk }),
    finalizeStream: () =>
      set((s) => {
        if (s.streamingContent) {
          s.messages.push({
            role: 'assistant',
            content: s.streamingContent,
            timestamp: new Date().toISOString(),
          })
        }
        s.isStreaming = false
        s.streamingContent = ''
      }),
    clearHistory: () => set((s) => { s.messages = [] }),
  }))
)

// ─── Search Store ─────────────────────────────────────────────────────────────

interface SearchStore {
  query: string
  level: SkillLevel
  setQuery: (q: string) => void
  setLevel: (l: SkillLevel) => void
}

export const useSearchStore = create<SearchStore>()(
  immer((set) => ({
    query: '',
    level: 'beginner',
    setQuery: (q) => set((s) => { s.query = q }),
    setLevel: (l) => set((s) => { s.level = l }),
  }))
)

// ─── UI Store ─────────────────────────────────────────────────────────────────

interface UIStore {
  sidebarOpen: boolean
  activeTab: string
  toggleSidebar: () => void
  setActiveTab: (tab: string) => void
}

export const useUIStore = create<UIStore>()(
  immer((set) => ({
    sidebarOpen: true,
    activeTab: 'resources',
    toggleSidebar: () => set((s) => { s.sidebarOpen = !s.sidebarOpen }),
    setActiveTab: (tab) => set((s) => { s.activeTab = tab }),
  }))
)
