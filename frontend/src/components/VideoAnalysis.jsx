import React, { useState, useRef } from "react";

const VideoAnalysis = () => {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false); // Visual state for drag
  const fileInputRef = useRef(null);

  // Helper to process the file (used by both Input and Drop)
  const processFile = (file) => {
    if (file && file.type.startsWith("video/")) {
      setSelectedVideo(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
    } else {
      alert("Please upload a valid video file (e.g., mp4, webm).");
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    processFile(file);
  };

  // --- DRAG AND DROP HANDLERS ---
  const handleDragOver = (e) => {
    e.preventDefault(); // Prevents browser from opening the file
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault(); // Prevents browser from opening the file
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    processFile(file);
  };
  // ------------------------------

  const handleAnalyze = () => {
    if (!selectedVideo) return alert("Please upload a video first.");
    setLoading(true);
    
    // Mock Backend Call
    setTimeout(() => {
      setLoading(false);
      setResult("REAL (99.1% Confidence)");
    }, 3000);
  };

  return (
    <div className="container">
      <h2>VIDEO ANALYSIS - MCL STREAM</h2>

      <div 
        className={`upload-box ${isDragging ? "drag-active" : ""}`}
        onClick={() => fileInputRef.current.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          accept="video/*" 
          ref={fileInputRef} 
          style={{ display: "none" }} 
          onChange={handleFileChange}
        />
        
        {previewUrl ? (
          <video src={previewUrl} controls className="preview-media" />
        ) : (
          <>
            <p className="upload-text">
              {isDragging ? "Drop Video Here!" : "Drag Your Video Here"}
            </p>
            <p className="upload-text">or</p>
            <span className="link">Choose Video</span>
          </>
        )}
      </div>

      <button className="action-btn" onClick={handleAnalyze} disabled={loading}>
        {loading ? "PROCESSING..." : "ANALYZE VIDEO"}
      </button>

      {result && (
        <div className="result-box">
          Status: <span className={result.includes("FAKE") ? "result-fake" : "result-real"}>{result}</span>
        </div>
      )}
    </div>
  );
};

export default VideoAnalysis;