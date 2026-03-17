import React, { useState, useRef, useCallback } from 'react';
import { Upload, Link, FileText, X, Image, Video, File } from 'lucide-react';
import toast from 'react-hot-toast';
import AnalyzeButton from './AnalyzeButton.jsx';

const TABS = [
  { id: 'video', label: 'Upload Video', icon: Video },
  { id: 'image', label: 'Upload Image', icon: Image },
  { id: 'url', label: 'Paste URL', icon: Link },
];

const ACCEPTED_TYPES = {
  'image/png': 'image', 'image/jpeg': 'image', 'image/jpg': 'image',
  'image/gif': 'image', 'image/webp': 'image',
  'video/mp4': 'video', 'video/webm': 'video', 'video/avi': 'video', 'video/mov': 'video',
  'text/plain': 'text', 'application/pdf': 'text',
};

const MAX_SIZE = 50 * 1024 * 1024;

export default function UploadSection({ onResult }) {
  const [activeTab, setActiveTab] = useState('video');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [fileType, setFileType] = useState(null);
  const [url, setUrl] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = useCallback((f) => {
    if (!f) return;
    const type = ACCEPTED_TYPES[f.type];
    if (!type) { toast.error(`Unsupported file type: ${f.type || 'unknown'}`); return; }
    if (f.size > MAX_SIZE) { toast.error('File too large. Maximum size is 50MB.'); return; }
    setFile(f); setFileType(type);
    if (type === 'image') {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target.result);
      reader.readAsDataURL(f);
    } else if (type === 'video') { setPreview(URL.createObjectURL(f)); }
    else { setPreview(null); }
    toast.success(`File "${f.name}" loaded successfully!`);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const handleDrag = useCallback((e) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const clearFile = () => {
    setFile(null); setPreview(null); setFileType(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const getInputData = () => {
    if ((activeTab === 'video' || activeTab === 'image') && file) {
      return { type: fileType, name: file.name, size: file.size };
    }
    if (activeTab === 'url' && url.trim()) return { type: 'url', name: url.trim() };
    return null;
  };

  return (
    <div className="w-full flex flex-col gap-8 animate-fade-in-up">
      {/* Section Header */}
      <div className="text-center flex flex-col items-center gap-2">
        <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
          Upload & <span className="gradient-text">Analyze</span>
        </h2>
        <p className="text-sm text-white/35 font-light">Choose your input method below</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 p-1.5 rounded-xl bg-white/[0.02] border border-white/[0.05] w-full max-w-md mx-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-300 cursor-pointer
                ${isActive
                  ? 'bg-white/[0.06] text-neon-blue border border-white/[0.08]'
                  : 'text-white/35 hover:text-white/55 hover:bg-white/[0.02] border border-transparent'
                }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Upload Card — centered */}
      <div className="w-full glass-elevated rounded-2xl p-6 sm:p-8 flex flex-col gap-6">        {/* File Tabs (Video/Image) */}
        {(activeTab === 'video' || activeTab === 'image') && (
          <div
            onDrop={handleDrop}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onClick={() => fileInputRef.current?.click()}
            className={`border border-dashed rounded-xl p-10 sm:p-12 text-center cursor-pointer transition-all duration-300
              ${dragActive
                ? (activeTab === 'video' ? 'border-neon-purple/40 bg-neon-purple/[0.04]' : 'border-neon-blue/40 bg-neon-blue/[0.04]')
                : 'border-white/[0.06] hover:border-white/[0.1] hover:bg-white/[0.01]'
              }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={activeTab === 'video' ? 'video/*' : 'image/*'}
              onChange={(e) => handleFile(e.target.files?.[0])}
              className="hidden"
              id="file-input"
            />

            {!file ? (
              <div className="flex flex-col items-center gap-5">
                <div className="w-14 h-14 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                  {activeTab === 'video' ? (
                    <Video className="w-6 h-6 text-neon-purple/60 shadow-[0_0_15px_rgba(191,64,191,0.3)]" />
                  ) : (
                    <Image className="w-6 h-6 text-neon-blue/60 shadow-[0_0_15px_rgba(0,212,255,0.3)]" />
                  )}
                </div>
                <div className="flex flex-col items-center gap-1">
                  <p className="text-white/70 font-semibold text-[15px]">
                    {dragActive ? 'Drop your file here' : `Drag & drop or click to upload ${activeTab}`}
                  </p>
                  <p className="text-white/25 text-sm font-light">
                    {activeTab === 'video' ? 'MP4, WebM, AVI — Max 50MB' : 'PNG, JPG, WebP — Max 50MB'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4" onClick={(e) => e.stopPropagation()}>
                {fileType === 'image' && preview && (
                  <img src={preview} alt="Preview" className="max-h-44 rounded-lg object-contain" />
                )}
                {fileType === 'video' && preview && (
                  <video src={preview} controls className="max-h-44 rounded-lg" />
                )}
                <div className="flex items-center gap-3">
                  <div className="glass px-4 py-2.5 rounded-lg flex items-center gap-2">
                    {fileType === 'image' && <Image className="w-4 h-4 text-neon-blue/60" />}
                    {fileType === 'video' && <Video className="w-4 h-4 text-neon-purple/60" />}
                    <span className="text-sm text-white/60 truncate max-w-[150px]">{file.name}</span>
                    <span className="text-xs text-white/20">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                  <button
                    onClick={clearFile}
                    className="p-2.5 rounded-lg text-white/25 hover:text-red-400 hover:bg-red-500/[0.06] transition-all duration-200 cursor-pointer border border-white/[0.04]"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* URL Tab */}
        {activeTab === 'url' && (
          <div className="flex flex-col gap-3">
            <label className="text-[13px] text-white/40 font-medium">Enter URL to analyze</label>
            <div className="relative">
              <Link className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/suspicious-content"
                className="w-full pl-11 pr-4 py-3.5 bg-white/[0.025] border border-white/[0.06] rounded-xl text-white/80 text-sm placeholder-white/15 focus:outline-none focus:border-neon-blue/25 transition-all duration-200"
              />
            </div>
            <p className="text-xs text-white/20 font-light">Paste a link to an image, video, or news article</p>
          </div>
        )}



        {/* Analyze Button */}
        <AnalyzeButton 
          inputData={getInputData()} 
          onResult={onResult} 
          file={file}
          url={url}
          activeTab={activeTab}
        />
      </div>
    </div>
  );
}
