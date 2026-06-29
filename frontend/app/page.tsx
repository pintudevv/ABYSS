"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { uploadFile, getStatus, STAGE_LABELS, formatFileSize, TaskStatus } from "../lib/api";
import FileUpload from "../components/FileUpload";
import ProgressPipeline from "../components/ProgressPipeline";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [stage, setStage] = useState<TaskStatus>("pending");
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Poll status when task is running
  useEffect(() => {
    if (!taskId) return;

    let active = true;
    const interval = setInterval(async () => {
      try {
        const res = await getStatus(taskId);
        if (!active) return;

        setStage(res.status);
        setProgress(res.progress);
        setStatusMessage(res.message);

        if (res.status === "complete" || res.progress === 100) {
          clearInterval(interval);
          // Wait 1.5 seconds so user can see completion state before redirect
          setTimeout(() => {
            router.push(`/report?task=${taskId}`);
          }, 1500);
        } else if (res.status === "failed") {
          clearInterval(interval);
          setError(res.message || "Analysis pipeline execution failed");
        }
      } catch (err: any) {
        logError(err);
      }
    }, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [taskId, router]);

  const logError = (err: any) => {
    setError(err.message || "An unexpected error occurred during status check.");
  };

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
    setProgress(0);
    setStage("pending");
    setStatusMessage("Uploading binary target...");

    try {
      const res = await uploadFile(selectedFile);
      setTaskId(res.task_id);
    } catch (err: any) {
      setError(err.message || "Failed to initiate file analysis. Please check backend connection.");
      setFile(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#050508] text-gray-100 flex flex-col items-center justify-between p-6 md:p-12 relative overflow-hidden select-none">
      
      {/* Immersive Background Gradients */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-indigo-900/10 blur-[120px] pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-rose-950/10 blur-[120px] pointer-events-none animate-pulse-glow" />

      {/* Header */}
      <header className="w-full max-w-4xl flex items-center justify-between z-10 animate-fade-in-up">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-rose-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 border border-white/10">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <div>
            <span className="font-bold text-lg tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-white via-gray-200 to-gray-400">STEALTHOS</span>
            <span className="text-[10px] text-indigo-400 font-mono block tracking-widest mt-[-2px]">SECURE_LAB</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-mono text-emerald-400 tracking-wider">ENGINE_ONLINE</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="w-full max-w-xl flex flex-col items-center justify-center flex-1 z-10 my-8">
        
        {/* Title and Intro */}
        {!file && (
          <div className="text-center mb-8 max-w-md animate-fade-in-up">
            <h1 className="text-4xl font-extrabold tracking-tight text-white mb-3">
              Deceive &amp; Capture
            </h1>
            <p className="text-sm text-gray-400 leading-relaxed">
              Upload executable targets or archives into StealthOS. Run threat analysis models and observe full logs inside a weightless instrumented sandbox.
            </p>
          </div>
        )}

        {/* Upload Dropzone */}
        {!file ? (
          <div className="w-full animate-fade-in-up delay-100">
            <FileUpload onFileSelected={handleFileSelect} />
          </div>
        ) : (
          <div className="w-full flex flex-col gap-6 animate-fade-in-up">
            {/* Active File Summary */}
            <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                  <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-white truncate max-w-[240px]">{file.name}</h3>
                  <p className="text-xs text-gray-400 font-mono mt-0.5">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 uppercase tracking-widest">
                  {stage}
                </span>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs px-4 py-3.5 rounded-xl flex items-center gap-3 animate-fade-in-up">
                <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{error}</span>
                <button 
                  onClick={() => setFile(null)} 
                  className="ml-auto hover:text-white underline font-mono text-[10px] tracking-wider"
                >
                  RESET
                </button>
              </div>
            )}

            {/* Processing Pipeline View */}
            {!error && (
              <div className="glass-panel p-6 rounded-2xl">
                <div className="flex justify-between items-center mb-6">
                  <h4 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase">ANALYSIS_PIPELINE</h4>
                  <span className="text-xs font-mono text-gray-400">{progress}%</span>
                </div>
                <ProgressPipeline status={stage} progress={progress} message={statusMessage} />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full text-center z-10 py-4">
        <p className="text-[10px] text-gray-500 font-mono tracking-widest">
          STEALTHOS VERSION 1.0.0 — SEMESTER PROJECT
        </p>
      </footer>
    </div>
  );
}
