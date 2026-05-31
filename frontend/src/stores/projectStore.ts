import { create } from 'zustand'

interface ProjectState {
  currentProjectId: string | null
  currentProjectState: string | null
  currentUserProjectRole: string | null   // 'creative' | 'engineer' | 'viewer' | 'admin'
  selectedKeyframeId: string | null
  selectedClipId: string | null
  panelPrefs: {
    leftWidth: number
    rightWidth: number
    previewHeight: number
  }
  setCurrentProject: (id: string | null) => void
  setProjectContext: (state: string | null, role: string | null) => void
  setSelectedKeyframe: (id: string | null) => void
  setSelectedClip: (id: string | null) => void
  setPanelPrefs: (prefs: Partial<ProjectState['panelPrefs']>) => void
  clearProjectContext: () => void
}

const loadPanelPrefs = () => {
  try {
    const saved = localStorage.getItem('aimm_panel_prefs')
    if (saved) return JSON.parse(saved)
  } catch {}
  return { leftWidth: 220, rightWidth: 320, previewHeight: 35 }
}

export const useProjectStore = create<ProjectState>()((set) => ({
  currentProjectId: null,
  currentProjectState: null,
  currentUserProjectRole: null,
  selectedKeyframeId: null,
  selectedClipId: null,
  panelPrefs: loadPanelPrefs(),
  setCurrentProject: (id) => set({ currentProjectId: id }),
  setProjectContext: (state, role) => set({ currentProjectState: state, currentUserProjectRole: role }),
  setSelectedKeyframe: (id) => set({ selectedKeyframeId: id }),
  setSelectedClip: (id) => set({ selectedClipId: id }),
  setPanelPrefs: (prefs) =>
    set((state) => {
      const updated = { ...state.panelPrefs, ...prefs }
      localStorage.setItem('aimm_panel_prefs', JSON.stringify(updated))
      return { panelPrefs: updated }
    }),
  clearProjectContext: () =>
    set({
      currentProjectState: null,
      currentUserProjectRole: null,
      selectedKeyframeId: null,
      selectedClipId: null,
    }),
}))
