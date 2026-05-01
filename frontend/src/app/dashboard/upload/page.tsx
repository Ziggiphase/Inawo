"use client";

import { useState, useRef } from 'react';
import styles from './upload.module.css';

export default function CatalogUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{type: 'success' | 'error', message: string} | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (selectedFile: File) => {
    setFile(selectedFile);
    await uploadFile(selectedFile);
  };

  const uploadFile = async (fileToUpload: File) => {
    setIsUploading(true);
    setStatus(null);
    
    const formData = new FormData();
    formData.append('file', fileToUpload);

    try {
      const token = localStorage.getItem('inawo_token');
      const res = await fetch('http://localhost:10000/api/catalog/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      setStatus({
        type: 'success',
        message: `Successfully processed! Added ${data.items_processed || 'multiple'} items to your AI's brain.`
      });
    } catch (err: any) {
      setStatus({
        type: 'error',
        message: err.message
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Train your AI Agent</h1>
        <p className={styles.subtitle}>
          Upload your product catalog, price list, or menu. Our system will automatically parse the data and train your agent.
        </p>
      </div>

      <div 
        className={styles.uploadArea}
        data-dragactive={dragActive}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <span className={styles.uploadIcon}>📄</span>
        <p className={styles.uploadText}>
          {isUploading ? 'Uploading & Parsing...' : 'Click or drag file to upload'}
        </p>
        <p className={styles.uploadSubtext}>Supports .PDF, .XLSX, and .CSV</p>
        
        <input
          ref={inputRef}
          type="file"
          className={styles.fileInput}
          accept=".pdf,.csv,.xlsx,.xls"
          onChange={handleChange}
        />
      </div>

      {file && !isUploading && (
        <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', fontSize: '14px' }}>
          Selected File: <strong>{file.name}</strong>
        </div>
      )}

      {status && (
        <div className={`${styles.statusCard} ${status.type === 'success' ? styles.statusSuccess : styles.statusError}`}>
          <p style={{ fontWeight: 500 }}>{status.type === 'success' ? '✅ Success' : '❌ Error'}</p>
          <p style={{ marginTop: '8px', fontSize: '14px' }}>{status.message}</p>
        </div>
      )}
    </div>
  );
}
