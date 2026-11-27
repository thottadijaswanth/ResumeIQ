"use client";

import { useRef, useState } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  RefreshCw,
} from "lucide-react";
import { apiRequest } from "@/lib/api";
import {
  BulkResumeFailureItem,
  BulkResumeUploadItem,
  BulkResumeUploadResponse,
} from "@/types";

interface BulkResumeUploaderProps {
  endpoint: string; // e.g. "/resumes/batch" or `/jobs/${jobId}/resumes`
  actionLabel?: string;
  batchSize?: number;
  onComplete?: (uploadedIds: string[], summary: { processed: number; cached: number; failed: number }) => void;
}

export default function BulkResumeUploader({
  endpoint,
  actionLabel = "Upload Resumes",
  batchSize = 50,
  onComplete,
}: BulkResumeUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [progress, setProgress] = useState({
    uploadedFiles: 0,
    totalFiles: 0,
    currentBatch: 0,
    totalBatches: 0,
  });
  const [summary, setSummary] = useState<{
    processed: number;
    cached: number;
    failed: BulkResumeFailureItem[];
    items: BulkResumeUploadItem[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    const accepted = Array.from(fileList).filter((f) => {
      const lower = f.name.toLowerCase();
      return lower.endsWith(".pdf") || lower.endsWith(".docx");
    });
    if (accepted.length === 0) {
      setError("Please select PDF or DOCX files.");
      return;
    }
    setError(null);
    setSelectedFiles((prev) => {
      const existingKeys = new Set(prev.map((p) => `${p.name}:${p.size}`));
      const uniqueNew = accepted.filter((f) => !existingKeys.has(`${f.name}:${f.size}`));
      return [...prev, ...uniqueNew];
    });
  };

  const pdfCount = selectedFiles.filter((f) => f.name.toLowerCase().endsWith(".pdf")).length;
  const docxCount = selectedFiles.filter((f) => f.name.toLowerCase().endsWith(".docx")).length;

  const runUpload = async (filesToUpload: File[]) => {
    if (filesToUpload.length === 0) return;
    setUploading(true);
    setError(null);

    const totalFiles = filesToUpload.length;
    const totalBatches = Math.ceil(totalFiles / batchSize);
    setProgress({ uploadedFiles: 0, totalFiles, currentBatch: 0, totalBatches });

    const allItems: BulkResumeUploadItem[] = [];
    const allFailed: BulkResumeFailureItem[] = [];
    let totalCached = 0;

    try {
      for (let i = 0; i < totalBatches; i++) {
        const chunk = filesToUpload.slice(i * batchSize, (i + 1) * batchSize);
        setProgress({
          uploadedFiles: i * batchSize,
          totalFiles,
          currentBatch: i + 1,
          totalBatches,
        });

        const formData = new FormData();
        for (const file of chunk) {
          formData.append("files", file);
        }

        const res = await apiRequest<BulkResumeUploadResponse>(endpoint, {
          method: "POST",
          body: formData,
        });

        allItems.push(...res.resumes);
        allFailed.push(...res.failed_files);
        totalCached += res.cached_count;

        setProgress({
          uploadedFiles: Math.min((i + 1) * batchSize, totalFiles),
          totalFiles,
          currentBatch: i + 1,
          totalBatches,
        });
      }

      setSummary({
        processed: allItems.length,
        cached: totalCached,
        failed: allFailed,
        items: allItems,
      });

      const uploadedIds = Array.from(new Set(allItems.map((item) => item.id)));
      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      onComplete?.(uploadedIds, {
        processed: allItems.length,
        cached: totalCached,
        failed: allFailed.length,
      });
    } catch (err: any) {
      setError(err.message || "Batch upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    addFiles(e.dataTransfer.files);
  };

  const uploadPercent =
    progress.totalFiles > 0 ? Math.round((progress.uploadedFiles / progress.totalFiles) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${
          dragActive
            ? "border-indigo-500 bg-indigo-50/70"
            : "border-slate-300 bg-slate-50/60 hover:border-indigo-300"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />

        <div className="w-11 h-11 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto mb-3">
          <Upload className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">Upload Resumes</h3>
        <p className="text-xs text-slate-600 mt-1">
          Select or drag & drop multiple PDF / DOCX files (1, 10, 100, 500, or 1,000+ resumes)
        </p>
        <p className="text-[11px] text-slate-400 mt-1">
          Files are automatically chunked in batches of {batchSize} and cached by content hash
        </p>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-xl shadow-sm transition-colors disabled:opacity-50"
          >
            Select Multiple Files
          </button>

          {selectedFiles.length > 0 && (
            <button
              type="button"
              disabled={uploading}
              onClick={() => runUpload(selectedFiles)}
              className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm transition-colors disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : (
                <span>
                  {actionLabel} ({selectedFiles.length})
                </span>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Selected Files Preview Summary */}
      {selectedFiles.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-4 text-xs">
            <span className="font-bold text-slate-900">
              Selected resumes: {selectedFiles.length.toLocaleString()}
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
              PDF: {pdfCount}
            </span>
            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
              DOCX: {docxCount}
            </span>
          </div>
          {!uploading && (
            <button
              type="button"
              onClick={() => {
                setSelectedFiles([]);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="inline-flex items-center space-x-1 text-xs text-slate-500 hover:text-rose-600"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear selection</span>
            </button>
          )}
        </div>
      )}

      {/* Upload Batch Progress */}
      {uploading && (
        <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-indigo-900">
            <span>
              Uploading batch {progress.currentBatch} / {progress.totalBatches}
            </span>
            <span>
              {progress.uploadedFiles} / {progress.totalFiles} files ({uploadPercent}%)
            </span>
          </div>
          <div className="w-full h-2 bg-indigo-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-600 transition-all duration-300"
              style={{ width: `${uploadPercent}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-2.5 text-rose-800 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Batch Upload Summary & Partial Errors */}
      {summary && (
        <div className="space-y-3">
          <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-900">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span className="font-semibold">
                {summary.processed} resumes ready ({summary.cached} reused from cache)
              </span>
            </div>
            {summary.failed.length > 0 && (
              <span className="font-semibold text-amber-700">
                {summary.failed.length} failed
              </span>
            )}
          </div>

          {summary.failed.length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs text-amber-900">
              <div className="flex items-center justify-between">
                <span className="font-bold flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span>Failed files ({summary.failed.length})</span>
                </span>
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="inline-flex items-center space-x-1 text-xs font-semibold text-amber-800 hover:underline"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Select replacement files</span>
                </button>
              </div>
              <ul className="space-y-1 max-h-36 overflow-y-auto">
                {summary.failed.map((fail, idx) => (
                  <li key={idx} className="font-mono text-[11px]">
                    {fail.filename} — Reason: {fail.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

