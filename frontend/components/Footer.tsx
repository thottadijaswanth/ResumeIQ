import { Sparkles, Shield, Cpu, Github, ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white mt-auto py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold text-slate-900">
                Resume<span className="text-indigo-600">IQ</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Production-grade AI resume analysis and deterministic job matching platform. Built for modern software engineering workflows.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              Features
            </h4>
            <ul className="space-y-2 text-xs text-slate-600">
              <li>ATS Compatibility Audit</li>
              <li>Semantic Vector Chunking</li>
              <li>Skill Normalization Engine</li>
              <li>Tailored Resume Builder</li>
              <li>AI Cover Letter Generator</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              Architecture
            </h4>
            <ul className="space-y-2 text-xs text-slate-600">
              <li>FastAPI + Pydantic V2</li>
              <li>PostgreSQL + pgvector</li>
              <li>Next.js App Router</li>
              <li>PyMuPDF & python-docx</li>
              <li>Modular AI Abstraction</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              Engineering Ethics
            </h4>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-xs text-slate-600 space-y-1.5">
              <div className="flex items-center space-x-1.5 text-indigo-700 font-medium">
                <Shield className="w-3.5 h-3.5" />
                <span>Zero Hallucination Policy</span>
              </div>
              <p className="text-[11px] leading-normal text-slate-500">
                Our AI tailoring engine reorganizes existing experience without ever fabricating employment history, metrics, or credentials.
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
          <p>© {new Date().getFullYear()} ResumeIQ. Production Engineering Project.</p>
          <div className="flex items-center space-x-4 mt-4 sm:mt-0">
            <span className="inline-flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-600 font-medium">FastAPI Engine Operational</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}

