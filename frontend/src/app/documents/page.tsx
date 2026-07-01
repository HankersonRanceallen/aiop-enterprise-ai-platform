"use client";
import { useState, useEffect, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Trash2, CheckCircle, Clock, XCircle, Loader2 } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { docsApi } from "@/lib/api";

interface Doc {
  id: number;
  title: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  created_at: string;
}

const StatusIcon = ({ status }: { status: Doc["status"] }) => {
  if (status === "ready") return <CheckCircle className="w-4 h-4 text-green-500" />;
  if (status === "processing" || status === "pending")
    return <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />;
  return <XCircle className="w-4 h-4 text-red-400" />;
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [loading, setLoading] = useState(true);

  async function fetchDocs() {
    try {
      const { data } = await docsApi.list();
      setDocs(data.documents);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDocs();
    // Poll every 5s to refresh status of processing documents
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, []);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploadError("");
    setUploading(true);
    for (const file of acceptedFiles) {
      try {
        await docsApi.upload(file);
      } catch (err: any) {
        setUploadError(err.response?.data?.detail || `Failed to upload ${file.name}`);
      }
    }
    await fetchDocs();
    setUploading(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxSize: 50 * 1024 * 1024,
  });

  async function handleDelete(id: number) {
    if (!confirm("Delete this document?")) return;
    await docsApi.delete(id);
    setDocs((prev) => prev.filter((d) => d.id !== id));
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-6 max-w-4xl">
          <h1 className="text-xl font-semibold text-gray-900 mb-1">Documents</h1>
          <p className="text-sm text-gray-400 mb-6">
            Upload PDF, DOCX, or TXT files. They'll be indexed automatically.
          </p>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors mb-6 ${
              isDragActive
                ? "border-primary-400 bg-primary-50"
                : "border-gray-200 hover:border-gray-300 bg-white"
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-8 h-8 text-gray-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-600">
              {isDragActive ? "Drop files here" : "Drag & drop or click to upload"}
            </p>
            <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT — up to 50MB each</p>
            {uploading && (
              <div className="flex items-center justify-center gap-2 mt-3">
                <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
                <span className="text-xs text-primary-500">Uploading and indexing…</span>
              </div>
            )}
          </div>

          {uploadError && (
            <p className="text-sm text-red-500 bg-red-50 rounded-lg px-4 py-2 mb-4">{uploadError}</p>
          )}

          {/* Document list */}
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
            </div>
          ) : docs.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-10 h-10 text-gray-200 mx-auto mb-3" />
              <p className="text-sm text-gray-400">No documents yet. Upload one to get started.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-4 bg-white border border-gray-100 rounded-xl px-4 py-3 shadow-sm"
                >
                  <FileText className="w-5 h-5 text-gray-300 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{doc.title}</p>
                    <p className="text-xs text-gray-400">
                      {doc.file_type.toUpperCase()} · {formatBytes(doc.file_size_bytes)}
                      {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusIcon status={doc.status} />
                    <span className="text-xs text-gray-400 capitalize">{doc.status}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-gray-300 hover:text-red-400 transition-colors p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
