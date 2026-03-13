import { create } from 'zustand'

interface JobProgress {
  jobId: string
  progressPct: number
  currentStep: number
  totalSteps: number
  etaSeconds: number | null
  status: string
}

interface JobStoreState {
  activeJobs: Record<string, JobProgress>
  updateJobProgress: (jobId: string, data: Partial<JobProgress>) => void
  removeJob: (jobId: string) => void
}

export const useJobStore = create<JobStoreState>()((set) => ({
  activeJobs: {},
  updateJobProgress: (jobId, data) =>
    set((state) => ({
      activeJobs: {
        ...state.activeJobs,
        [jobId]: { ...state.activeJobs[jobId], jobId, ...data } as JobProgress,
      },
    })),
  removeJob: (jobId) =>
    set((state) => {
      const { [jobId]: _, ...rest } = state.activeJobs
      return { activeJobs: rest }
    }),
}))
