"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Briefcase,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  Loader2,
  Building,
  MapPin,
  Users,
  Clock,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import { Job, JobSummary } from "@/types";

function parseCsvList(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function JobsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedResumeId = searchParams.get("resumeId");

  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Structured Job Form state
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Hiring Organization");
  const [location, setLocation] = useState("Hyderabad, India");
  const [workMode, setWorkMode] = useState<"Remote" | "Hybrid" | "On-site">("Hybrid");
  const [minExperience, setMinExperience] = useState("4");
  const [requiredSkillsText, setRequiredSkillsText] = useState("");
  const [preferredSkillsText, setPreferredSkillsText] = useState("");
  const [employmentType, setEmploymentType] = useState("Full-time");
  const [noticePeriod, setNoticePeriod] = useState("");
  const [educationText, setEducationText] = useState("");
  const [responsibilitiesText, setResponsibilitiesText] = useState("");
  const [locationRequired, setLocationRequired] = useState(false);
  const [showOptional, setShowOptional] = useState(false);
  const [description, setDescription] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadData() {
      try {
        const jobsData = await apiRequest<JobSummary[]>("/jobs");
        setJobs(jobsData);
      } catch (err: any) {
        setError(err.message || "Failed to load jobs.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setCreating(true);

    try {
      const payload = {
        title,
        company: company.trim() || "Hiring Organization",
        location: workMode === "Remote" && !location.trim() ? "Anywhere" : location.trim(),
        work_mode: workMode,
        min_experience: minExperience !== "" ? parseFloat(minExperience) : null,
        max_experience: null,
        required_skills: parseCsvList(requiredSkillsText),
        preferred_skills: parseCsvList(preferredSkillsText),
        employment_type: employmentType || null,
        notice_period: noticePeriod.trim() || null,
        education_requirements: parseCsvList(educationText),
        responsibilities: responsibilitiesText
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        location_required: locationRequired,
        description,
      };

      const created = await apiRequest<Job>("/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setSuccess(`Job "${created.title}" created. Opening candidate screening workspace...`);
      setJobs([created, ...jobs]);
      setTitle("");
      setRequiredSkillsText("");
      setPreferredSkillsText("");
      setDescription("");

      router.push(`/jobs/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create job.");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteJob = async (id: string, jobTitle: string) => {
    if (!confirm(`Delete job requisition "${jobTitle}"?`)) return;
    try {
      await apiRequest(`/jobs/${id}`, { method: "DELETE" });
      setJobs(jobs.filter((j) => j.id !== id));
    } catch (err: any) {
      setError(err.message || "Failed to delete job.");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Job Requisitions & Candidate Screening
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Create one structured job posting and screen 1 to 1,000+ candidate resumes against it.
          </p>
        </div>
        {preselectedResumeId && (
          <span className="text-xs font-medium bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-xl border border-indigo-200">
            Select any job below to open screening
          </span>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start space-x-3 text-emerald-800 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-600" />
          <span>{success}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Structured Job Creation Form (2 cols) */}
        <div className="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center space-x-2 text-indigo-600">
            <Sparkles className="w-5 h-5" />
            <h2 className="text-base font-bold text-slate-900">Create Structured Job</h2>
          </div>

          <form onSubmit={handleCreateJob} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Role / Job Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Senior Java Backend Developer"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Work Mode *
                </label>
                <select
                  value={workMode}
                  onChange={(e) => {
                    const nextMode = e.target.value as "Remote" | "Hybrid" | "On-site";
                    setWorkMode(nextMode);
                    if (nextMode === "Remote" && !location) {
                      setLocation("Anywhere");
                    }
                  }}
                  className="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                >
                  <option value="Hybrid">Hybrid</option>
                  <option value="On-site">On-site</option>
                  <option value="Remote">Remote</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Location *
                </label>
                <input
                  type="text"
                  required
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Hyderabad, India"
                  className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Minimum Experience (yrs)
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                max="50"
                value={minExperience}
                onChange={(e) => setMinExperience(e.target.value)}
                placeholder="4"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Required Skills (comma-separated)
              </label>
              <input
                type="text"
                value={requiredSkillsText}
                onChange={(e) => setRequiredSkillsText(e.target.value)}
                placeholder="Java, Spring Boot, REST APIs, SQL"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Preferred Skills (comma-separated)
              </label>
              <input
                type="text"
                value={preferredSkillsText}
                onChange={(e) => setPreferredSkillsText(e.target.value)}
                placeholder="AWS, Docker, Kubernetes"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Job Description *
              </label>
              <textarea
                required
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Role summary, responsibilities, and technical expectations..."
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 leading-relaxed"
              />
            </div>

            {/* Optional Metadata Accordion */}
            <div className="border-t border-slate-100 pt-2">
              <button
                type="button"
                onClick={() => setShowOptional(!showOptional)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-600 hover:text-slate-900 py-1"
              >
                <span>Optional Details (Company, Employment Type, Education)</span>
                {showOptional ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showOptional && (
                <div className="space-y-3 pt-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Company / Team
                      </label>
                      <input
                        type="text"
                        value={company}
                        onChange={(e) => setCompany(e.target.value)}
                        className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Employment Type
                      </label>
                      <select
                        value={employmentType}
                        onChange={(e) => setEmploymentType(e.target.value)}
                        className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white"
                      >
                        <option value="Full-time">Full-time</option>
                        <option value="Contract">Contract</option>
                        <option value="Part-time">Part-time</option>
                        <option value="Internship">Internship</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Education Requirements
                      </label>
                      <input
                        type="text"
                        value={educationText}
                        onChange={(e) => setEducationText(e.target.value)}
                        placeholder="Bachelor's in CS, B.Tech"
                        className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                        Notice Period
                      </label>
                      <input
                        type="text"
                        value={noticePeriod}
                        onChange={(e) => setNoticePeriod(e.target.value)}
                        placeholder="Immediate / 30 days"
                        className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                      Responsibilities (one per line)
                    </label>
                    <textarea
                      rows={3}
                      value={responsibilitiesText}
                      onChange={(e) => setResponsibilitiesText(e.target.value)}
                      placeholder="Design microservice APIs&#10;Own production database schema performance"
                      className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300"
                    />
                  </div>
                  <label className="flex items-center space-x-2 text-xs text-slate-700">
                    <input
                      type="checkbox"
                      checked={locationRequired}
                      onChange={(e) => setLocationRequired(e.target.checked)}
                      className="rounded border-slate-300 text-indigo-600"
                    />
                    <span>Enforce location as a hard requirement</span>
                  </label>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={creating}
              className="w-full flex items-center justify-center py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <span className="flex items-center space-x-1.5">
                  <Plus className="w-4 h-4" />
                  <span>Create Job & Open Screening</span>
                </span>
              )}
            </button>
          </form>
        </div>

        {/* Saved Jobs Directory (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              Active Job Requisitions ({jobs.length})
            </h2>
          </div>

          {loading ? (
            <div className="p-8 text-center bg-white rounded-2xl border border-slate-200">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">Loading job requisitions...</p>
            </div>
          ) : jobs.length === 0 ? (
            <div className="bg-white p-10 rounded-2xl border border-dashed border-slate-300 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                <Briefcase className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">No Job Requisitions Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Create a structured job posting on the left, then upload and rank hundreds of resumes against it.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-indigo-200 transition-all flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
                >
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center space-x-2 flex-wrap">
                      <h3 className="text-base font-bold text-slate-900">{job.title}</h3>
                      {job.work_mode && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/70">
                          {job.work_mode}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      <span className="flex items-center space-x-1 font-medium text-slate-700">
                        <Building className="w-3.5 h-3.5 text-slate-400" />
                        <span>{job.company}</span>
                      </span>
                      {job.location && (
                        <span className="flex items-center space-x-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          <span>{job.location}</span>
                        </span>
                      )}
                      {(job.min_experience !== undefined && job.min_experience !== null) && (
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>
                            {job.min_experience}
                            {job.max_experience ? `–${job.max_experience}` : "+"} yrs
                          </span>
                        </span>
                      )}
                    </div>
                    {job.required_skills && job.required_skills.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {job.required_skills.slice(0, 6).map((skill, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 self-end sm:self-center flex-shrink-0">
                    <Link
                      href={`/jobs/${job.id}`}
                      className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors shadow-sm"
                    >
                      <Users className="w-3.5 h-3.5" />
                      <span>Screen Candidates</span>
                    </Link>
                    <button
                      onClick={() => handleDeleteJob(job.id, job.title)}
                      className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                      title="Delete Job"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading job requisitions...</p>
        </div>
      }
    >
      <JobsContent />
    </Suspense>
  );
}
