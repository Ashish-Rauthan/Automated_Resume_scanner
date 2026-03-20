import React, { useRef, useState } from 'react'

const MAX_SIZE_MB = 5
const MAX_FILES   = 20

export default function ResumeUpload({ files, onChange }) {
  const inputRef    = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const addFiles = (incoming) => {
    const valid = []
    const seen  = new Set(files.map((f) => f.name))

    for (const file of incoming) {
      if (!file.name.toLowerCase().endsWith('.pdf')) continue
      if (file.size > MAX_SIZE_MB * 1024 * 1024) continue
      if (seen.has(file.name)) continue
      valid.push(file)
      seen.add(file.name)
    }

    const combined = [...files, ...valid].slice(0, MAX_FILES)
    onChange(combined)
  }

  const handleInputChange = (e) => {
    addFiles(Array.from(e.target.files || []))
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    addFiles(Array.from(e.dataTransfer.files))
  }

  const removeFile = (name) => onChange(files.filter((f) => f.name !== name))

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div>
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        <div className="upload-icon">📄</div>
        <div className="upload-title">
          {dragOver ? 'Drop PDFs here' : 'Click or drag PDF resumes here'}
        </div>
        <div className="upload-hint">
          PDF only · Max {MAX_SIZE_MB}MB per file · Up to {MAX_FILES} resumes
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          style={{ display: 'none' }}
          onChange={handleInputChange}
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((file) => (
            <div key={file.name} className="file-item">
              <div>
                <div className="file-name">{file.name}</div>
                <div className="file-size">{formatSize(file.size)}</div>
              </div>
              <button
                className="file-remove"
                onClick={(e) => { e.stopPropagation(); removeFile(file.name) }}
                title="Remove"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
