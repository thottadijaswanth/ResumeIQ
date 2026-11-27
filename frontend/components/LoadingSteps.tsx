"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

interface LoadingStepsProps {
  steps?: string[];
  durationMs?: number;
}

const DEFAULT_STEPS = [
  "Parsing and validating resume document format...",
  "Extracting candidate structured experience & skills...",
  "Analyzing job requirements and normalizing skill taxonomy...",
  "Computing semantic embeddings and section alignment...",
  "Executing deterministic weighted matching engine...",
  "Synthesizing ATS audit and actionable recommendations...",
];

export default function LoadingSteps({
  steps = DEFAULT_STEPS,
  durationMs = 15000,
}: LoadingStepsProps) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const stepInterval = durationMs / steps.length;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, stepInterval);

    return () => clearInterval(interval);
  }, [steps.length, durationMs]);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm max-w-lg mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 mb-3 animate-pulse">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
        <h3 className="text-lg font-bold text-slate-900">AI Engine at Work</h3>
        <p className="text-xs text-slate-500 mt-1">
          Processing document extraction and deep requirements comparison (local AI may take 15–60s)
        </p>
      </div>

      <div className="space-y-4">
        {steps.map((step, idx) => {
          const isDone = idx < activeStep;
          const isCurrent = idx === activeStep;

          return (
            <div key={idx} className="flex items-center space-x-3.5">
              <div className="flex-shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                ) : (
                  <Circle className="w-5 h-5 text-slate-300" />
                )}
              </div>
              <span
                className={`text-sm ${
                  isDone
                    ? "text-slate-800 font-medium"
                    : isCurrent
                    ? "text-indigo-600 font-semibold"
                    : "text-slate-400"
                }`}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

