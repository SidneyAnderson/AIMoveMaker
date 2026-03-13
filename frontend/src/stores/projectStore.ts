import { create } from 'zustand'

interface ProjectState {
  currentProjectId: string | null
  selectedKeyframeId: string | null
  selectedClipId: string | null
  panelPrefs: {
    leftWidth: number
    rightWidth: number
    previewHeight: number
  }
  setCurrentProject: (id: string | null) => void
  setSelectedKeyframe: (id: string | null) => void
  setSelectedClip: (id: string | null) => void
  setPanelPrefs: (prefs: Partial<ProjectState['panelPrefs']>) => void
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
  selectedKeyframeId: null,
  selectedClipId: null,
  panelPrefs: loadPanelPrefs(),
  setCurrentProject: (id) => set({ currentProjectId: id }),
  setSelectedKeyframe: (id) => set({ selectedKeyframeId: id }),
  setSelectedClip: (id) => set({ selectedClipId: id }),
  setPanelPrefs: (prefs) =>
    set((state) => {
      const updated = { ...state.panelPrefs, ...prefs }
      localStorage.setItem('aimm_panel_prefs', JSON.stringify(updated))
      return { panelPrefs: updated }
    }),
}))
