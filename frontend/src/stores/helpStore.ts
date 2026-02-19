import { create } from 'zustand';

interface HelpState {
  onboardingCompleted: boolean;
  showOnboarding: boolean;
  currentStep: number;
  tooltipsEnabled: boolean;
  hiddenTooltips: Set<string>;
  completeOnboarding: () => void;
  startOnboarding: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  stopOnboarding: () => void;
  hideTooltip: (id: string) => void;
  toggleTooltips: () => void;
}

const getUserKey = () => {
  const userId = localStorage.getItem('user_id') || 'default';
  return `onboarding_completed_${userId}`;
};

export const useHelpStore = create<HelpState>((set, get) => ({
  onboardingCompleted: localStorage.getItem(getUserKey()) === 'true',
  showOnboarding: false,
  currentStep: 0,
  tooltipsEnabled: true,
  hiddenTooltips: new Set<string>(),

  completeOnboarding: () => {
    localStorage.setItem(getUserKey(), 'true');
    set({ onboardingCompleted: true, showOnboarding: false, currentStep: 0 });
  },

  startOnboarding: () => {
    set({ showOnboarding: true, currentStep: 0 });
  },

  nextStep: () => {
    set((s) => ({ currentStep: s.currentStep + 1 }));
  },

  prevStep: () => {
    set((s) => ({ currentStep: Math.max(0, s.currentStep - 1) }));
  },

  goToStep: (step: number) => {
    set({ currentStep: step });
  },

  stopOnboarding: () => {
      localStorage.setItem(getUserKey(), 'true');
    set({ onboardingCompleted: true, showOnboarding: false, currentStep: 0 });
  },

  hideTooltip: (id: string) => {
    const next = new Set(get().hiddenTooltips);
    next.add(id);
    set({ hiddenTooltips: next });
  },

  toggleTooltips: () => {
    set((s) => ({ tooltipsEnabled: !s.tooltipsEnabled }));
  },
}));
