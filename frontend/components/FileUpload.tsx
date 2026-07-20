'use client';

import React, { useCallback, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatFileSize } from '@/lib/api';

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

const SUPPORTED_FORMATS = ['EXE', 'DLL', 'ZIP', 'PDF', 'DOCX'];

const ALLOWED_EXTENSIONS = new Set([
  'exe', 'dll', 'zip', 'pdf', 'docx',
  'msi', 'bat', 'ps1', 'vbs', 'js',
  'jar', 'apk', 'doc', 'xls', 'xlsx',
]);

function isAllowedFile(file: File): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  return ALLOWED_EXTENSIONS.has(ext);
}

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  const icons: Record<string, string> = {
    exe: '⚙️', dll: '🔧', zip: '📦', pdf: '📄',
    docx: '📝', doc: '📝', msi: '📀', bat: '🖥️',
    ps1: '🔵', vbs: '📜', js: '🟡', jar: '☕',
    apk: '🤖', xls: '📊', xlsx: '📊',
  };
  return icons[ext] ?? '📁';
}

const dropzoneVariants = {
  idle: { scale: 1, borderColor: 'rgba(255, 255, 255, 0.1)', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' },
  dragOver: { scale: 1.01, borderColor: '#FF2E55', boxShadow: '0 0 30px rgba(255,46,85,0.2)' },
  hasFile: { scale: 1, borderColor: '#00E599', boxShadow: '0 0 30px rgba(0,229,153,0.15)' },
  disabled: { opacity: 0.5 },
};

const iconVariants = {
  idle: { scale: 1, rotate: 0 },
  dragOver: { scale: 1.15, rotate: [0, -5, 5, -5, 0] },
  hasFile: { scale: 1 },
};

export default function FileUpload({ onFileSelected, disabled = false }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      if (!isAllowedFile(file)) {
        setError(`Unsupported file type. Allowed: ${[...ALLOWED_EXTENSIONS].join(', ')}`);
        return;
      }
      if (file.size > 200 * 1024 * 1024) {
        setError('File too large. Maximum size: 200 MB');
        return;
      }
      setSelectedFile(file);
      onFileSelected(file);
    },
    [onFileSelected],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [disabled, handleFile],
  );

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = '';
    },
    [handleFile],
  );

  const onClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
        e.preventDefault();
        inputRef.current?.click();
      }
    },
    [disabled],
  );

  const getDropzoneState = () => {
    if (disabled) return 'disabled';
    if (selectedFile) return 'hasFile';
    if (isDragOver) return 'dragOver';
    return 'idle';
  };

  return (
    <div style={{ width: '100%' }}>
      <input
        ref={inputRef}
        type="file"
        accept={[...ALLOWED_EXTENSIONS].map((e) => `.${e}`).join(',')}
        onChange={onInputChange}
        style={{ display: 'none' }}
        aria-hidden="true"
        disabled={disabled}
      />

      <AnimatePresence mode="wait">
        <motion.div
          ref={dropzoneRef}
          key={selectedFile ? 'has-file' : 'empty'}
          variants={dropzoneVariants}
          animate={getDropzoneState()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={onClick}
          onKeyDown={onKeyDown}
          tabIndex={disabled ? -1 : 0}
          role="button"
          aria-label="Upload file for malware analysis"
          aria-disabled={disabled}
          aria-describedby={selectedFile ? 'file-info' : error ? 'file-error' : 'dropzone-hint'}
          style={{
            padding: '56px 40px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 20,
            minHeight: 320,
            outline: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            transition: 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
            position: 'relative',
            overflow: 'hidden',
            background: 'rgba(13, 13, 18, 0.85)',
            backdropFilter: 'blur(20px)',
          }}
          className="hover:border-white/20"
          whileHover={!disabled && !selectedFile ? { y: -2 } : undefined}
          whileTap={!disabled && !selectedFile ? { scale: 0.99 } : undefined}
        >
          {selectedFile ? (
            <motion.div
              className="animate-scale-in"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 16,
                position: 'relative',
                zIndex: 1,
              }}
              id="file-info"
            >
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 260, damping: 20 }}
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 20,
                  background: 'rgba(0,229,153,0.1)',
                  border: '1px solid rgba(0,229,153,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 32,
                  boxShadow: '0 0 30px rgba(0,229,153,0.2)',
                }}
                aria-hidden="true"
              >
                {getFileIcon(selectedFile.name)}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                style={{ textAlign: 'center' }}
              >
                <motion.p
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 }}
                  style={{
                    color: '#00E599',
                    fontWeight: 700,
                    fontSize: 16,
                    marginBottom: 4,
                    maxWidth: 400,
                    wordBreak: 'break-all',
                    fontFamily: "'JetBrains Mono', monospace",
                  }}
                >
                  {selectedFile.name}
                </motion.p>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  style={{ color: '#A1A1AA', fontSize: 13 }}
                >
                  {formatFileSize(selectedFile.size)}
                  {' · '}
                  {selectedFile.type || selectedFile.name.split('.').pop()?.toUpperCase() || 'Unknown'}
                </motion.p>
              </motion.div>

              <motion.div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'rgba(0,229,153,0.12)',
                  border: '1px solid rgba(0,229,153,0.3)',
                  color: '#00E599',
                  fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 700,
                  padding: '5px 14px',
                  borderRadius: 20,
                }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.25, type: 'spring', stiffness: 300, damping: 20 }}
              >
                <svg width="6" height="6" viewBox="0 0 6 6" fill="none" aria-hidden="true">
                  <circle cx="3" cy="3" r="3" fill="#00E599" />
                </svg>
                READY FOR INSTRUMENTATION
              </motion.div>

              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8 }}>
                <motion.button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (selectedFile) onFileSelected(selectedFile);
                  }}
                  whileHover={{ scale: 1.04, y: -2 }}
                  whileTap={{ scale: 0.96 }}
                  style={{
                    background: 'linear-gradient(135deg, #FF2E55, #C0392B)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: 8,
                    fontWeight: 800,
                    fontSize: 12,
                    padding: '8px 20px',
                    cursor: 'pointer',
                    boxShadow: '0 0 20px rgba(255, 46, 85, 0.4)',
                  }}
                >
                  RUN DETONATION ↗
                </motion.button>

                <motion.button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    setError(null);
                  }}
                  whileHover={{ background: 'rgba(255,255,255,0.1)', color: '#FFFFFF' }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: 8,
                    color: '#A1A1AA',
                    fontSize: 12,
                    padding: '8px 16px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  aria-label="Change file"
                >
                  Change file
                </motion.button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 16,
                position: 'relative',
                zIndex: 1,
              }}
            >
              <motion.div
                variants={iconVariants}
                animate={getDropzoneState()}
                style={{
                  width: 76,
                  height: 76,
                  borderRadius: '50%',
                  background: isDragOver ? 'rgba(255,46,85,0.15)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${isDragOver ? '#FF2E55' : 'rgba(255,255,255,0.12)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
                  boxShadow: isDragOver ? '0 0 30px rgba(255,46,85,0.3)' : 'none',
                }}
                aria-hidden="true"
              >
                <UploadIcon isDragOver={isDragOver} />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                style={{ textAlign: 'center' }}
              >
                <motion.p
                  style={{
                    fontWeight: 700,
                    fontSize: 17,
                    marginBottom: 6,
                    color: isDragOver ? '#FF2E55' : '#F4F4F6',
                    letterSpacing: '-0.01em',
                    transition: 'color 0.3s ease',
                  }}
                >
                  {isDragOver ? 'Release to Detonate Target' : 'Drop target file here or click to browse'}
                </motion.p>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.15 }}
                  style={{ color: '#71717A', fontSize: 13 }}
                >
                  Maximum payload size: 200 MB
                </motion.p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, staggerChildren: 0.05 }}
                style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}
              >
                {SUPPORTED_FORMATS.map((fmt) => (
                  <motion.span
                    key={fmt}
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: '#A1A1AA',
                      background: 'rgba(255,255,255,0.04)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      padding: '4px 12px',
                      borderRadius: 6,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    whileHover={{ scale: 1.05, y: -1, color: '#F4F4F6', borderColor: 'rgba(255,255,255,0.25)' }}
                  >
                    {fmt}
                  </motion.span>
                ))}
              </motion.div>
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div
            key="error"
            className="animate-fade-in-up"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{
              marginTop: 12,
              padding: '10px 16px',
              background: 'rgba(255,51,102,0.1)',
              border: '1px solid rgba(255,51,102,0.25)',
              borderRadius: 10,
              color: '#ff6688',
              fontSize: 13,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
            id="file-error"
            role="alert"
            aria-live="assertive"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <circle cx="7" cy="7" r="6.5" stroke="#ff3366" strokeOpacity="0.6" />
              <path d="M7 4v3M7 9.5v.5" stroke="#ff6688" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function UploadIcon({ isDragOver }: { isDragOver: boolean }) {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      style={{ transition: 'all 0.3s ease' }}
      aria-hidden="true"
    >
      <path
        d="M16 22V10M16 10L11 15M16 10L21 15"
        stroke={isDragOver ? '#FF2E55' : '#F4F4F6'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8 26h16"
        stroke={isDragOver ? '#FF2E55' : 'rgba(255,255,255,0.3)'}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}