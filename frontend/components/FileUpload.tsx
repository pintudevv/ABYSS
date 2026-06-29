'use client';

import React, { useCallback, useRef, useState } from 'react';
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

export default function FileUpload({ onFileSelected, disabled = false }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      // Reset input so same file can be re-selected
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

  const dropzoneClass = [
    'dropzone',
    isDragOver ? 'drag-over' : '',
    selectedFile ? 'has-file' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div style={{ width: '100%' }}>
      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={[...ALLOWED_EXTENSIONS].map((e) => `.${e}`).join(',')}
        onChange={onInputChange}
        style={{ display: 'none' }}
        aria-hidden="true"
        disabled={disabled}
      />

      {/* Drop zone */}
      <div
        className={dropzoneClass}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onClick}
        onKeyDown={onKeyDown}
        tabIndex={disabled ? -1 : 0}
        role="button"
        aria-label="Upload file for malware analysis"
        aria-disabled={disabled}
        style={{
          padding: '56px 40px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 20,
          minHeight: 320,
          outline: 'none',
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Animated rotating border */}
        <div className="dropzone-animated-border" aria-hidden="true" />

        {selectedFile ? (
          /* ── File Selected State ── */
          <div
            className="animate-scale-in"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 16,
              position: 'relative',
              zIndex: 1,
            }}
          >
            {/* File icon */}
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 16,
                background: 'rgba(0,255,136,0.1)',
                border: '1px solid rgba(0,255,136,0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 32,
                boxShadow: '0 0 30px rgba(0,255,136,0.15)',
              }}
            >
              {getFileIcon(selectedFile.name)}
            </div>

            {/* File name */}
            <div style={{ textAlign: 'center' }}>
              <p
                style={{
                  color: '#00ff88',
                  fontWeight: 600,
                  fontSize: 16,
                  marginBottom: 4,
                  maxWidth: 400,
                  wordBreak: 'break-all',
                  textShadow: '0 0 16px rgba(0,255,136,0.4)',
                }}
              >
                {selectedFile.name}
              </p>
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>
                {formatFileSize(selectedFile.size)}
                {' · '}
                {selectedFile.type || selectedFile.name.split('.').pop()?.toUpperCase() || 'Unknown'}
              </p>
            </div>

            {/* Status */}
            <div className="badge badge-green">
              <svg width="6" height="6" viewBox="0 0 6 6" fill="none" aria-hidden="true">
                <circle cx="3" cy="3" r="3" fill="#00ff88" />
              </svg>
              Ready for Analysis
            </div>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setError(null);
              }}
              style={{
                background: 'none',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                color: 'rgba(255,255,255,0.4)',
                fontSize: 12,
                padding: '4px 14px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              Change file
            </button>
          </div>
        ) : (
          /* ── Empty State ── */
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 16,
              position: 'relative',
              zIndex: 1,
            }}
          >
            {/* Upload icon */}
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: isDragOver
                  ? 'rgba(99,102,241,0.15)'
                  : 'rgba(255,255,255,0.04)',
                border: `1px solid ${isDragOver ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.08)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
                boxShadow: isDragOver ? '0 0 30px rgba(99,102,241,0.2)' : 'none',
              }}
            >
              <UploadIcon isDragOver={isDragOver} />
            </div>

            <div style={{ textAlign: 'center' }}>
              <p
                style={{
                  color: isDragOver ? '#a5b4fc' : 'rgba(255,255,255,0.75)',
                  fontWeight: 600,
                  fontSize: 17,
                  marginBottom: 6,
                  transition: 'color 0.3s ease',
                }}
              >
                {isDragOver ? 'Drop to scan' : 'Drop file here or click to browse'}
              </p>
              <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13 }}>
                Maximum file size: 200 MB
              </p>
            </div>

            {/* Format badges */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
              {SUPPORTED_FORMATS.map((fmt) => (
                <span key={fmt} className="format-badge">
                  {fmt}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div
          className="animate-fade-in"
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
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <circle cx="7" cy="7" r="6.5" stroke="#ff3366" strokeOpacity="0.6" />
            <path d="M7 4v3M7 9.5v.5" stroke="#ff6688" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          {error}
        </div>
      )}
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
    >
      <path
        d="M16 22V10M16 10L11 15M16 10L21 15"
        stroke={isDragOver ? '#6366f1' : 'rgba(255,255,255,0.4)'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M8 26h16"
        stroke={isDragOver ? '#6366f1' : 'rgba(255,255,255,0.2)'}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
