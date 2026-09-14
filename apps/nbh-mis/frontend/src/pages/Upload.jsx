import React, { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileSpreadsheet, Download, CheckCircle2 } from "lucide-react";
import { uploadFile, templateDownloadUrl } from "../services/api.js";
import { useMasterData } from "../context/MasterDataContext.jsx";
import { useRagColors } from "../context/RagColorsContext.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";

export default function Upload() {
  const navigate = useNavigate();
  const { reload: reloadMaster } = useMasterData();
  const { reload: reloadRagColors } = useRagColors();
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const inputRef = useRef(null);

  const doUpload = useCallback(
    async (file) => {
      if (!file) return;
      setUploading(true);
      setError(null);
      setSuccess(null);
      setProgress(0);
      try {
        const result = await uploadFile(file, (evt) => {
          if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
        });
        setSuccess(result);
        reloadMaster();
        reloadRagColors();
        setTimeout(() => navigate("/dashboard"), 900);
      } catch (err) {
        setError(err?.response?.data?.detail || "Upload failed. Please check the file and try again.");
      } finally {
        setUploading(false);
      }
    },
    [navigate, reloadMaster, reloadRagColors]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) doUpload(file);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 flex flex-col items-center gap-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-ink-900">NBH Customer Complaint Management Dashboard</h1>
        <p className="text-sm text-ink-500 mt-1">
          Upload the NoBrokerHood complaint export (.xlsx / .xls / .csv) to build the management MIS.
        </p>
      </div>

      <div
        className={`w-full card border-2 border-dashed p-10 flex flex-col items-center gap-4 text-center transition-colors ${
          dragOver ? "border-brand-500 bg-brand-500/5" : "border-line"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
      >
        <UploadCloud className="h-10 w-10 text-brand-600" />
        <div>
          <p className="text-sm font-medium text-ink-800">Drag & drop your NBH Excel file here</p>
          <p className="text-xs text-ink-500 mt-1">or click below to browse (.xlsx, .xls, .csv)</p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={(e) => doUpload(e.target.files?.[0])}
        />
        <button className="btn-primary" disabled={uploading} onClick={() => inputRef.current?.click()}>
          <FileSpreadsheet className="h-4 w-4" />
          {uploading ? `Uploading… ${progress}%` : "Upload NBH Excel File"}
        </button>

        {uploading && (
          <div className="w-full max-w-xs h-1.5 rounded-full bg-canvas overflow-hidden">
            <div className="h-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {success && (
        <div className="w-full card p-4 border-emerald-200 bg-emerald-50 flex items-start gap-2 text-emerald-800">
          <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
          <div className="text-sm">
            <p className="font-medium">
              Uploaded {success.filename} — {success.total_records.toLocaleString("en-IN")} records
              ({success.num_projects} projects, {success.num_categories} categories). Redirecting to dashboard…
            </p>
          </div>
        </div>
      )}

      <a
        href={templateDownloadUrl()}
        className="btn"
        title="Download a sample .xlsx template with the expected columns"
      >
        <Download className="h-4 w-4" />
        Download Sample Template
      </a>

      <p className="text-[11px] text-ink-400 max-w-lg text-center">
        Once uploaded, all dashboards, reports and exports are generated dynamically from the columns found in your
        file — no manual configuration required.
      </p>
    </div>
  );
}
