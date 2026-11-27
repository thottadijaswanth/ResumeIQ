"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckSquare,
  Plus,
  Clock,
  Calendar,
  Building,
  FileText,
  Trash2,
  Edit2,
  Check,
  AlertCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { apiRequest, getToken } from "@/lib/api";
import { Application, JobSummary, ResumeSummary } from "@/types";

const STATUSES: Array<"Saved" | "Applied" | "Interview" | "Offer" | "Rejected"> = [
  "Saved",
  "Applied",
  "Interview",
  "Offer",
  "Rejected",
];

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New application modal/form state
  const [showModal, setShowModal] = useState(false);
  const [newJobId, setNewJobId] = useState("");
  const [newResumeId, setNewResumeId] = useState("");
  const [newStatus, setNewStatus] = useState<"Saved" | "Applied" | "Interview" | "Offer" | "Rejected">("Saved");
  const [newNotes, setNewNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadData() {
      try {
        const [appsData, jobsData, resumesData] = await Promise.all([
          apiRequest<Application[]>("/applications"),
          apiRequest<JobSummary[]>("/jobs"),
          apiRequest<ResumeSummary[]>("/resumes"),
        ]);
        setApplications(appsData);
        setJobs(jobsData);
        setResumes(resumesData);
        if (jobsData.length > 0) setNewJobId(jobsData[0].id);
        if (resumesData.length > 0) setNewResumeId(resumesData[0].id);
      } catch (err: any) {
        setError(err.message || "Failed to load application data.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  const handleStatusChange = async (appId: string, status: string) => {
    try {
      const updated = await apiRequest<Application>(`/applications/${appId}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setApplications(applications.map((a) => (a.id === appId ? updated : a)));
    } catch (err: any) {
      alert("Failed to update application status: " + err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to remove this application?")) return;
    try {
      await apiRequest(`/applications/${id}`, { method: "DELETE" });
      setApplications(applications.filter((a) => a.id !== id));
    } catch (err: any) {
      alert("Failed to delete application: " + err.message);
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobId) return;

    setSubmitting(true);
    try {
      const created = await apiRequest<Application>("/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: newJobId,
          resume_id: newResumeId || undefined,
          status: newStatus,
          notes: newNotes || undefined,
        }),
      });

      setApplications([created, ...applications]);
      setShowModal(false);
      setNewNotes("");
    } catch (err: any) {
      alert("Failed to save application: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading application pipeline...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Job Application Tracker
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Kanban workflow to track applications from initial bookmark to interviews and offers.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          disabled={jobs.length === 0}
          className="inline-flex items-center space-x-2 px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Track New Job</span>
        </button>
      </div>

      {jobs.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-center justify-between">
          <span>You need to add at least one job posting before tracking applications.</span>
          <Link href="/jobs" className="font-semibold underline ml-2">
            Add Job
          </Link>
        </div>
      )}

      {/* Kanban Board Columns */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {STATUSES.map((status) => {
          const colApps = applications.filter((a) => a.status === status);
          let colBorder = "border-slate-200";
          let badgeColor = "bg-slate-100 text-slate-700";

          if (status === "Applied") {
            colBorder = "border-blue-200";
            badgeColor = "bg-blue-100 text-blue-700";
          } else if (status === "Interview") {
            colBorder = "border-amber-200";
            badgeColor = "bg-amber-100 text-amber-800";
          } else if (status === "Offer") {
            colBorder = "border-emerald-200";
            badgeColor = "bg-emerald-100 text-emerald-800";
          } else if (status === "Rejected") {
            colBorder = "border-rose-200";
            badgeColor = "bg-rose-100 text-rose-700";
          }

          return (
            <div
              key={status}
              className="bg-slate-100/60 rounded-2xl p-3.5 border border-slate-200/80 flex flex-col min-h-[500px]"
            >
              {/* Column Header */}
              <div className="flex items-center justify-between mb-3 px-1">
                <span className="text-xs font-bold text-slate-900 tracking-wide uppercase">
                  {status}
                </span>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
                  {colApps.length}
                </span>
              </div>

              {/* Cards List */}
              <div className="space-y-3 flex-1 overflow-y-auto">
                {colApps.map((app) => {
                  const jobData = jobs.find((j) => j.id === app.job_id);
                  const resumeData = resumes.find((r) => r.id === app.resume_id);

                  return (
                    <div
                      key={app.id}
                      className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-2.5"
                    >
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 pr-2">
                          <h4 className="text-xs font-bold text-slate-900 truncate">
                            {jobData?.title || "Position Title"}
                          </h4>
                          <p className="text-[11px] font-medium text-slate-500 truncate flex items-center space-x-1 mt-0.5">
                            <Building className="w-3 h-3 text-slate-400" />
                            <span>{jobData?.company || "Company"}</span>
                          </p>
                        </div>
                        <button
                          onClick={() => handleDelete(app.id)}
                          className="text-slate-300 hover:text-rose-600 transition-colors"
                          title="Delete card"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Resume used */}
                      {resumeData && (
                        <p className="text-[10px] text-slate-400 truncate">
                          📄 {resumeData.name}
                        </p>
                      )}

                      {/* Notes snippet */}
                      {app.notes && (
                        <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100 italic">
                          "{app.notes}"
                        </p>
                      )}

                      {/* Move status dropdown */}
                      <div className="pt-1 border-t border-slate-100 flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">Move to:</span>
                        <select
                          value={app.status}
                          onChange={(e) => handleStatusChange(app.id, e.target.value)}
                          className="text-[11px] font-semibold text-indigo-700 bg-transparent focus:outline-none cursor-pointer"
                        >
                          {STATUSES.map((st) => (
                            <option key={st} value={st}>
                              {st}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  );
                })}

                {colApps.length === 0 && (
                  <div className="h-28 border border-dashed border-slate-300/80 rounded-xl flex items-center justify-center text-[11px] text-slate-400">
                    No applications
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Application Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900">Track New Application</h3>

            <form onSubmit={handleCreateApplication} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Target Job
                </label>
                <select
                  required
                  value={newJobId}
                  onChange={(e) => setNewJobId(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                >
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} — {j.company}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Resume Used
                </label>
                <select
                  value={newResumeId}
                  onChange={(e) => setNewResumeId(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                >
                  <option value="">(None / General)</option>
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Initial Pipeline Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value as any)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                >
                  {STATUSES.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Notes / Next Steps
                </label>
                <textarea
                  rows={3}
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="e.g. Applied via referral, follow up on Monday"
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl"
                >
                  {submitting ? "Saving..." : "Save Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

