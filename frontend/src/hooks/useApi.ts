import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@clerk/nextjs'
import { createAuthClient } from '@/lib/api'
import type {
  Roadmap, RoadmapSummary, DashboardStats,
  ProgressUpdate, QuizSubmit, QuizResult,
  TutorChatRequest, User
} from '@/types'

function useApi() {
  const { getToken } = useAuth()
  return createAuthClient(getToken)
}

// ─── Keys ─────────────────────────────────────────────────────────────────────

export const keys = {
  roadmaps: ['roadmaps'] as const,
  roadmap: (id: string) => ['roadmaps', id] as const,
  dashboardStats: ['dashboard', 'stats'] as const,
  lesson: (id: string) => ['lessons', id] as const,
  quiz: (id: string) => ['quizzes', id] as const,
  user: ['user'] as const,
}

// ─── Roadmaps ─────────────────────────────────────────────────────────────────

export function useRoadmaps() {
  const api = useApi()
  return useQuery<RoadmapSummary[]>({
    queryKey: keys.roadmaps,
    queryFn: async () => {
      const res = await api.get('/api/roadmaps')
      return res.data
    },
  })
}

export function useRoadmap(id: string) {
  const api = useApi()
  return useQuery<Roadmap>({
    queryKey: keys.roadmap(id),
    queryFn: async () => {
      const res = await api.get(`/api/roadmaps/${id}`)
      return res.data
    },
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useDashboardStats() {
  const api = useApi()
  return useQuery<DashboardStats>({
    queryKey: keys.dashboardStats,
    queryFn: async () => {
      const res = await api.get('/api/roadmaps/dashboard/stats')
      return res.data
    },
  })
}

export function useDeleteRoadmap() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/roadmaps/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.roadmaps }),
  })
}

// ─── Progress ─────────────────────────────────────────────────────────────────

export function useUpdateProgress() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProgressUpdate) => api.post('/api/progress', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.roadmaps })
      qc.invalidateQueries({ queryKey: keys.dashboardStats })
    },
  })
}

// ─── Quiz ─────────────────────────────────────────────────────────────────────

export function useQuiz(quizId: string) {
  const api = useApi()
  return useQuery({
    queryKey: keys.quiz(quizId),
    queryFn: async () => {
      const res = await api.get(`/api/quizzes/${quizId}`)
      return res.data
    },
    enabled: !!quizId,
  })
}

export function useSubmitQuiz() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation<QuizResult, Error, QuizSubmit>({
    mutationFn: async (data) => {
      const res = await api.post('/api/quizzes/submit', data)
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.roadmaps })
      qc.invalidateQueries({ queryKey: keys.dashboardStats })
    },
  })
}

// ─── Tutor suggestions ────────────────────────────────────────────────────────

export function useGetSuggestions() {
  const api = useApi()
  return useMutation<{ suggestions: string[] }, Error, TutorChatRequest>({
    mutationFn: async (data) => {
      const res = await api.post('/api/tutor/suggestions', data)
      return res.data
    },
  })
}
