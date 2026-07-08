"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { getReport, downloadReport, ThreatReport, formatFileSize, formatDuration } from "../../lib/api";

function ReportPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const taskId = searchParams.get("task");

  const [report, setReport] = useState<ThreatReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<boolean>(false);

  useEffect(() => {
    if (!taskId) {
      setError("No task ID provided. Please upload a file first.");
      setLoading(false);
      return;
    }

    const fetchReport = async () => {
      try {
        const res = await getReport(taskId);
        setReport(res);
      } catch (err: any) {
        setError(err.message || "Failed to load forensic analysis results.");
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [taskId]);

  const handleDownload = async () => {
    if (!taskId) return;
    setDownloading(true);
    try {
      const url = await downloadReport(taskId);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stealthos_forensic_report_${taskId.slice(0, 8)}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err: any) {
      alert("Failed to download report: " + err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050508] text-gray-100 flex flex-col items-center justify-center p-6 font-sans select-none">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-t-2 border-indigo-500 animate-spin" />
          <p className="text-xs font-mono tracking-widest text-indigo-400 uppercase">RETRIEVING_FORENSIC_DATABASE</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-[#050508] text-gray-100 flex flex-col items-center justify-center p-6 font-sans select-none">
        <div className="glass-panel p-8 rounded-2xl max-w-md text-center">
          <svg className="w-12 h-12 text-rose-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="text-xl font-bold text-white mb-2">Analysis Retrieval Failed</h2>
          <p className="text-sm text-gray-400 mb-6">{error || "Forensic report data is not populated yet."}</p>
          <button 
            onClick={() => router.push("/")}
            className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const { is_threat, threat_type, confidence, risk_score, is_zero_day } = report;
  const risk_level = report.risk_level || "CLEAN";

  return (
    <div className="min-h-screen bg-[#050508] text-gray-100 p-6 md:p-12 font-sans relative overflow-x-hidden select-none">
      
      {/* Immersive Background Gradients */}
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-rose-950/10 blur-[130px] pointer-events-none" />

      <div className="max-w-6xl mx-auto flex flex-col gap-8 z-10 relative">
        
        {/* Header Navigation */}
        <div className="flex items-center justify-between border-b border-white/5 pb-5">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push("/")}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-rose-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <span className="font-bold text-sm tracking-wider">STEALTHOS</span>
              <span className="text-[8px] text-indigo-400 font-mono block tracking-widest mt-[-2px]">FORENSICS</span>
            </div>
          </div>
          <button 
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 text-xs font-semibold tracking-wider font-mono text-gray-200 transition-all uppercase"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {downloading ? "GENERATING..." : "DOWNLOAD_FORENSIC_SUMMARY"}
          </button>
        </div>

        {/* Threat Alert Panel */}
        <div className={`glass-panel p-6 md:p-8 rounded-3xl ${is_threat ? "glass-panel-glow-red" : "glass-panel-glow-green"} animate-fade-in-up`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            
            <div className="flex items-start gap-5">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${is_threat ? "bg-rose-500/10 border-rose-500/20 text-rose-500" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"}`}>
                {is_threat ? (
                  <svg className="w-8 h-8 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                ) : (
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                )}
              </div>
              <div>
                <span className={`text-[10px] font-mono font-bold tracking-widest px-2.5 py-1 rounded border uppercase ${is_threat ? "bg-rose-500/10 border-rose-500/20 text-rose-500" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"}`}>
                  {is_threat ? "THREAT DETECTED" : "VERIFIED CLEAN"}
                </span>
                <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-2 mb-1">{report.filename}</h1>
                <p className="text-xs text-gray-400 font-mono uppercase tracking-wide">SHA256: {report.sha256}</p>
              </div>
            </div>

            <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-8">
              
              {/* Circular Confidence Meter */}
              <div className="relative w-20 h-20 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="40" cy="40" r="34" className="stroke-white/5 fill-transparent" strokeWidth="6" />
                  <circle 
                    cx="40" 
                    cy="40" 
                    r="34" 
                    className={`fill-transparent transition-all duration-1000 ${is_threat ? "stroke-rose-500" : "stroke-emerald-500"}`} 
                    strokeWidth="6" 
                    strokeDasharray={2 * Math.PI * 34}
                    strokeDashoffset={2 * Math.PI * 34 * (1 - confidence)}
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-base font-extrabold text-white mt-1 leading-none">{Math.round(confidence * 100)}%</span>
                  <span className="text-[8px] font-mono text-gray-400 mt-0.5 leading-none">CONFIDENCE</span>
                </div>
              </div>

              <div>
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-[10px] text-gray-400 font-mono tracking-widest leading-none uppercase">RISK_LEVEL:</span>
                  <span className={`text-[10px] font-mono font-bold leading-none ${is_threat ? "text-rose-500" : "text-emerald-500"}`}>{risk_level}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-gray-400 font-mono tracking-widest leading-none uppercase">ZERO_DAY:</span>
                  <span className="text-[10px] text-white font-mono font-bold leading-none">{is_zero_day ? "TRUE" : "FALSE"}</span>
                </div>
              </div>

            </div>

          </div>
        </div>

        {/* Evidence Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in-up delay-100">
          
          {/* 1. Stolen Files Shielded */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase">DATA IT TRIED TO STEAL</h2>
              <span className="text-[10px] font-mono bg-rose-500/10 border border-rose-500/20 text-rose-500 px-2 py-0.5 rounded">SHIELDED</span>
            </div>
            {report.stolen_files && report.stolen_files.length > 0 ? (
              <ul className="flex flex-col gap-2 max-h-[220px] overflow-y-auto">
                {report.stolen_files.map((file, idx) => (
                  <li key={idx} className="flex items-center justify-between text-xs py-2 px-3 bg-white/5 rounded-xl border border-white/5">
                    <span className="font-mono text-gray-300 truncate max-w-[200px]">{file.path}</span>
                    <span className="text-[9px] font-mono text-rose-400 bg-rose-500/5 px-2 py-0.5 rounded border border-rose-500/10 uppercase tracking-widest">Blocked</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400 py-8 text-center font-mono uppercase tracking-wider">No file access events intercepted</p>
            )}
          </div>

          {/* 2. Exfiltration Networks Deflected */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase">WHERE IT TRIED TO SEND IT</h2>
              <span className="text-[10px] font-mono bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded">SINKHOLED</span>
            </div>
            {report.exfil_endpoints && report.exfil_endpoints.length > 0 ? (
              <ul className="flex flex-col gap-2 max-h-[220px] overflow-y-auto">
                {report.exfil_endpoints.map((ip, idx) => (
                  <li key={idx} className="flex items-center justify-between text-xs py-2 px-3 bg-white/5 rounded-xl border border-white/5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{ip.country_flag}</span>
                      <span className="font-mono text-gray-300">{ip.ip}:{ip.port}</span>
                    </div>
                    <span className="text-[9px] font-mono text-indigo-400 bg-indigo-500/5 px-2 py-0.5 rounded border border-indigo-500/10 uppercase tracking-widest">Sinkholed</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400 py-8 text-center font-mono uppercase tracking-wider">No network exfiltration calls deflected</p>
            )}
          </div>

          {/* 3. Decoy Honeypot Mock Data Served */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase">WHAT WE GAVE IT INSTEAD</h2>
              <span className="text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded">MOCK DATA</span>
            </div>
            {report.mock_data_served && report.mock_data_served.length > 0 ? (
              <ul className="flex flex-col gap-2 max-h-[220px] overflow-y-auto">
                {report.mock_data_served.map((item, idx) => (
                  <li key={idx} className="flex items-center justify-between text-xs py-2 px-3 bg-white/5 rounded-xl border border-white/5">
                    <span className="font-mono text-gray-300">{item.original_type}</span>
                    <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10 uppercase tracking-widest">Mock Serve</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400 py-8 text-center font-mono uppercase tracking-wider">No honeypot mock feeds requested</p>
            )}
          </div>

          {/* 4. Allowed Legitimate Connections */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase">SAFE CALLS PASSED THROUGH</h2>
              <span className="text-[10px] font-mono bg-gray-500/10 border border-gray-500/20 text-gray-400 px-2 py-0.5 rounded">PASSTHROUGH</span>
            </div>
            <ul className="flex flex-col gap-2 max-h-[220px] overflow-y-auto">
              <li className="flex items-center justify-between text-xs py-2 px-3 bg-white/5 rounded-xl border border-white/5 opacity-60">
                <span className="font-mono text-gray-300">RegOpenKeyExA | theme settings</span>
                <span className="text-[9px] font-mono text-emerald-500 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10 uppercase tracking-widest">Allowed</span>
              </li>
              <li className="flex items-center justify-between text-xs py-2 px-3 bg-white/5 rounded-xl border border-white/5 opacity-60">
                <span className="font-mono text-gray-300">CreateFileA | kernel32.dll read</span>
                <span className="text-[9px] font-mono text-emerald-500 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/10 uppercase tracking-widest">Allowed</span>
              </li>
            </ul>
          </div>

        </div>

        {/* SHAP / Feature Importance Chart */}
        {report.shap_features && report.shap_features.length > 0 && (
          <div className="glass-panel p-6 md:p-8 rounded-3xl animate-fade-in-up delay-200">
            <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase mb-6 border-b border-white/5 pb-3">
              SHAP FEATURE DETECTOR INFLUENCE (TOP EXPLANATIONS)
            </h2>
            <div className="flex flex-col gap-4">
              {report.shap_features.map((feature, idx) => (
                <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="w-full sm:w-[240px] font-mono text-gray-300 truncate">{feature.name}</div>
                  <div className="flex-1 flex items-center gap-3">
                    <div className="w-full bg-white/5 h-3 rounded-full overflow-hidden border border-white/5">
                      <div 
                        className={`h-full rounded-full transition-all duration-1000 ${is_threat ? "bg-gradient-to-r from-rose-600 to-rose-400" : "bg-gradient-to-r from-emerald-600 to-emerald-400"}`} 
                        style={{ width: `${feature.impact * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-gray-400 min-w-[36px] text-right">{(feature.impact * 10).toFixed(1)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timeline Analysis Section */}
        {report.timeline && report.timeline.length > 0 && (
          <div className="glass-panel p-6 md:p-8 rounded-3xl animate-fade-in-up delay-300">
            <h2 className="text-xs font-mono font-bold tracking-widest text-indigo-400 uppercase mb-8 border-b border-white/5 pb-3">
              SYNTHETIC THREAT ACTIVITY TIMELINE
            </h2>
            <div className="relative pl-6 border-l border-white/10 flex flex-col gap-8">
              {report.timeline.map((event, idx) => (
                <div key={idx} className="relative">
                  {/* Event Marker Node */}
                  <span className={`absolute left-[-31px] top-1.5 w-2.5 h-2.5 rounded-full ring-4 ring-[#050508] ${
                    event.severity === "critical" ? "bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.6)]" :
                    event.severity === "high" ? "bg-rose-500" :
                    event.severity === "medium" ? "bg-indigo-400" : "bg-gray-500"
                  }`} />
                  <div className="flex items-center gap-3 mb-1.5">
                    <span className="text-[10px] text-gray-400 font-mono tracking-wider">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-[8px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                      event.severity === "critical" ? "bg-rose-500/10 border-rose-500/20 text-rose-500" :
                      event.severity === "high" ? "bg-rose-500/10 border-rose-500/20 text-rose-500" :
                      event.severity === "medium" ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400" :
                      "bg-gray-500/10 border-gray-500/20 text-gray-400"
                    }`}>
                      {event.severity}
                    </span>
                  </div>
                  <h3 className="font-semibold text-white text-sm mb-1">{event.description}</h3>
                  {event.details && <p className="text-xs text-gray-400 font-mono mt-1 bg-white/5 p-2 rounded-lg border border-white/5">{event.details}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottom Safety Status Banner */}
        <div className="text-center py-6 border-t border-white/5">
          <p className="text-xs font-mono tracking-wider text-gray-400">
            {is_threat 
              ? "⚠ TARGET SOFTWARE IS SAFE TO USE — MALICIOUS ACTIONS FULLY NEUTRALIZED" 
              : "✔ BINARY DEEMED BENIGN — NO SYSTEM MITIGATIONS REQUIRED"}
          </p>
        </div>

      </div>
    </div>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#050508] text-gray-100 flex items-center justify-center"><div className="w-12 h-12 rounded-full border-t-2 border-indigo-500 animate-spin" /></div>}>
      <ReportPageInner />
    </Suspense>
  );
}
