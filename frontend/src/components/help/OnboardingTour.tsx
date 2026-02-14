import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ChevronRight, ChevronLeft, X, Sparkles } from 'lucide-react';
import { useHelpStore } from '../../stores/helpStore';
import { onboardingSteps } from '../../data/helpContent';
import { useLocale } from '../../i18n';

const stepRoutes = ['/', '/', '/workflows', '/executions', '/credentials', '/'];

export default function OnboardingTour() {
  const { showOnboarding, currentStep, nextStep, prevStep, completeOnboarding, stopOnboarding } = useHelpStore();
  const navigate = useNavigate();
  const location = useLocation();
  const { locale } = useLocale();

  useEffect(() => {
    if (!showOnboarding) return;
    const route = stepRoutes[currentStep];
    if (route && location.pathname !== route) {
      navigate(route);
    }
  }, [showOnboarding, currentStep]);

  if (!showOnboarding) return null;

  const step = onboardingSteps[currentStep];
  if (!step) return null;

  const isLast = currentStep === onboardingSteps.length - 1;
  const isFirst = currentStep === 0;
  const lang = locale as 'en' | 'bg';

  return (
    <div className="fixed inset-0 z-[9998]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Tour card */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md">
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={20} className="text-white" />
              <span className="text-white font-semibold text-lg">
                {lang === 'bg' ? 'Добре дошли!' : 'Welcome!'}
              </span>
            </div>
            <button
              onClick={stopOnboarding}
              className="text-white/70 hover:text-white p-1 rounded-lg hover:bg-white/10"
              aria-label="Close tour"
            >
              <X size={18} />
            </button>
          </div>

          {/* Progress */}
          <div className="px-6 pt-4">
            <div className="flex gap-1.5">
              {onboardingSteps.map((_, i) => (
                <div
                  key={i}
                  className={`h-1.5 flex-1 rounded-full transition-colors ${
                    i <= currentStep ? 'bg-indigo-500' : 'bg-slate-200 dark:bg-slate-600'
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {lang === 'bg' ? `Стъпка ${currentStep + 1} от ${onboardingSteps.length}` : `Step ${currentStep + 1} of ${onboardingSteps.length}`}
            </p>
          </div>

          {/* Content */}
          <div className="px-6 py-5">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
              {step.title[lang]}
            </h3>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              {step.content[lang]}
            </p>
          </div>

          {/* Actions */}
          <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <button
              onClick={stopOnboarding}
              className="text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              {lang === 'bg' ? 'Пропусни' : 'Skip tour'}
            </button>

            <div className="flex gap-2">
              {!isFirst && (
                <button
                  onClick={prevStep}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm"
                >
                  <ChevronLeft size={16} />
                  {lang === 'bg' ? 'Назад' : 'Back'}
                </button>
              )}
              <button
                onClick={isLast ? completeOnboarding : nextStep}
                className="flex items-center gap-1 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium"
              >
                {isLast
                  ? (lang === 'bg' ? 'Готово!' : 'Done!')
                  : (lang === 'bg' ? 'Напред' : 'Next')}
                {!isLast && <ChevronRight size={16} />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
