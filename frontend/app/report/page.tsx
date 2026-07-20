'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSearchParams, useRouter } from 'next/navigation';
import ThreatReportView from '@/components/ThreatReport';
import { downloadReport, ThreatReport, mapBackendReport, getReport } from '@/lib/api';
import { Loader2, AlertCircle, Shield, ArrowLeft } from 'lucide-react';

const pageVariants = {
  initial: { opacity: 0, y: 15 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -15, transition: { duration: 0.2 } },
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const } },
};

function ReportContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const taskId = searchParams.get('task');
  const [report, setReport] = useState<ThreatReport | null>(null);
  const [loading, setLoading] = useState(taskId ? true : false);
  const [error, setError] = useState<string | null>(taskId ? null : 'No task ID provided');

  useEffect(() => {
    if (!taskId) return;

    let mounted = true;

    const fetchReport = async () => {
      try {
        const data = await getReport(taskId);
        if (mounted) {
          setReport(data);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load report');
          setLoading(false);
        }
      }
    };

    fetchReport();

    return () => {
      mounted = false;
    };
  }, [taskId]);

  const handleDownload = async () => {
    if (!taskId) return;
    try {
      const blobUrl = await downloadReport(taskId);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `abyss-report-${taskId}.txt`;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const loadingVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1, transition: { type: 'spring' as const, stiffness: 300, damping: 20 } },
    exit: { opacity: 0, scale: 0.95, transition: { duration: 0.2 } },
  };

  if (loading) {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key="loading"
          className="min-h-screen bg-[#070709] flex items-center justify-center"
          initial="hidden"
          animate="visible"
          exit="exit"
          variants={loadingVariants}
        >
          <div className="text-center">
            <motion.div
              className="w-10 h-10 mx-auto text-[#FF2E55]"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 className="w-full h-full" />
            </motion.div>
            <motion.p
              className="mt-4 text-[#A1A1AA] text-xs font-mono tracking-wider"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              RETRIEVING TELEMETRY DATA...
            </motion.p>
          </div>
        </motion.div>
      </AnimatePresence>
    );
  }

  if (error) {
    return (
      <AnimatePresence mode="wait">
        <motion.div
          key="error"
          className="min-h-screen bg-[#070709] flex items-center justify-center p-6"
          initial="hidden"
          animate="visible"
          exit="exit"
          variants={loadingVariants}
        >
          <div className="max-w-md w-full text-center bg-[#0D0D12] p-8 border border-white/10 rounded-2xl shadow-2xl">
            <motion.div
              className="w-14 h-14 mx-auto text-[#FF2E55] mb-4"
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            >
              <AlertCircle className="w-full h-full" />
            </motion.div>
            <motion.h1
              className="text-xl font-bold text-[#F4F4F6] mb-2 uppercase tracking-wide"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              Failed to Load Report
            </motion.h1>
            <motion.p
              className="text-[#A1A1AA] text-xs mb-6 font-mono"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              {error}
            </motion.p>
            <motion.button
              onClick={() => router.push('/')}
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#FF2E55] text-white text-xs font-mono tracking-wider hover:bg-[#E02647] transition-all uppercase font-semibold rounded-lg shadow-lg shadow-red-500/20"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Analysis
            </motion.button>
          </div>
        </motion.div>
      </AnimatePresence>
    );
  }

  if (!report) {
    return (
      <motion.div
        className="min-h-screen bg-[#070709] flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <p className="text-[#A1A1AA] text-xs font-mono uppercase tracking-wider">No report data available</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="min-h-screen bg-[#070709] py-12 px-6"
      initial="initial"
      animate="animate"
      variants={pageVariants}
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      <motion.div
        className="max-w-6xl mx-auto"
        variants={containerVariants}
      >
        <motion.div
          className="mb-10 flex items-center justify-between flex-wrap gap-6 pb-6 border-b border-white/10"
          variants={sectionVariants}
        >
          <motion.div variants={sectionVariants}>
            <div className="flex items-center gap-3 mb-1.5">
              <button 
                onClick={() => router.push('/')}
                className="w-9 h-9 border border-white/10 bg-white/5 rounded-lg flex items-center justify-center text-zinc-300 hover:text-white hover:border-white/30 hover:bg-white/10 transition-all cursor-pointer"
                title="Back to Upload"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <h1 className="text-2xl font-extrabold text-[#F4F4F6] uppercase tracking-wide font-mono">
                Analysis Report
              </h1>
            </div>
            <motion.p
              className="text-[#71717A] font-mono text-[11px] tracking-wider"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              TASK_ID: {taskId}
            </motion.p>
          </motion.div>
          <motion.button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#FF2E55] text-white text-xs font-mono uppercase tracking-wider hover:bg-[#E02647] transition-all font-bold cursor-pointer rounded-lg shadow-lg shadow-red-500/20"
            variants={sectionVariants}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Report
          </motion.button>
        </motion.div>

        <ThreatReportView report={report} onDownload={handleDownload} />
      </motion.div>
    </motion.div>
  );
}

export default function ReportPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#070709] flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 mx-auto text-[#FF2E55] animate-spin">
            <Loader2 className="w-full h-full" />
          </div>
          <p className="mt-4 text-[#A1A1AA] text-xs font-mono tracking-wider">INITIALIZING ABYSS</p>
        </div>
      </div>
    }>
      <ReportContent />
    </Suspense>
  );
}