import { useState, useEffect, useRef } from 'react';

interface UseOnboardingReturn {
  showOnboarding: boolean;
  onboardingStep: number;
  onboardingRef: React.RefObject<HTMLDivElement | null>;
  nextStep: () => void;
  skip: () => void;
}

export function useOnboarding(hasDevices: boolean | null): UseOnboardingReturn {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState(1);
  const onboardingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (hasDevices === false && !localStorage.getItem("cardea_onboarding_done")) {
      setShowOnboarding(true);
      setTimeout(() => {
        onboardingRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }, [hasDevices]);

  const skip = () => {
    setShowOnboarding(false);
    localStorage.setItem("cardea_onboarding_done", "true");
  };

  const nextStep = () => {
    if (onboardingStep >= 3) {
      skip();
    } else {
      setOnboardingStep(s => s + 1);
    }
  };

  return {
    showOnboarding,
    onboardingStep,
    onboardingRef,
    nextStep,
    skip
  };
}
