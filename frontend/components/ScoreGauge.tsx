"use client";

import { getScoreColor } from "@/lib/utils";

interface ScoreGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

export default function ScoreGauge({
  score,
  size = 180,
  strokeWidth = 14,
  label = "Overall Match",
  sublabel,
}: ScoreGaugeProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, score));
  const offset = circumference - (clampedScore / 100) * circumference;

  let strokeColor = "#10b981"; // Emerald
  if (score < 60) strokeColor = "#f43f5e"; // Rose
  else if (score < 80) strokeColor = "#f59e0b"; // Amber

  const colorStyles = getScoreColor(score);

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#e2e8f0"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-extrabold tracking-tight ${colorStyles.text}`}>
            {Math.round(clampedScore)}%
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 mt-1">
            {label}
          </span>
        </div>
      </div>
      {sublabel && (
        <p className="text-xs text-slate-500 text-center mt-3 max-w-[200px]">
          {sublabel}
        </p>
      )}
    </div>
  );
}

