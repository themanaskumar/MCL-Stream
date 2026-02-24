import React, { useState, useRef } from "react";

const VideoAnalysis = () => {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // Added error state
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Helper to process the file (used by both Input and Drop)
  const processFile = (file) => {
    if (file && file.type.startsWith("video/")) {
      setSelectedVideo(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null); // Clear previous errors
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
    e.preventDefault(); 
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault(); 
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    processFile(file);
  };
  // ------------------------------

  const handleAnalyze = async () => {
    if (!selectedVideo) return alert("Please upload a video first.");
    
    setLoading(true);
    setResult(null);
    setError(null);
    
    // 1. Package the video into a FormData object
    const formData = new FormData();
    formData.append("video", selectedVideo);

    try {
      // 2. Make the POST request to your Django backend
      const response = await fetch("http://127.0.0.1:8000/api/analyze-video/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server Error: ${response.statusText}`);
      }

      // 3. Parse the JSON response
      const data = await response.json();
      setResult(data);

    } catch (err) {
      console.error("Analysis failed:", err);
      setError("Failed to reach the server. Make sure your Django backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>VIDEO ANALYSIS - MCL STREAM</h2>

      <div 
        className={`upload-box ${isDragging ? "drag-active" : ""}`}
        onClick={() => fileInputRef.current.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={{ cursor: 'pointer' }} // Added for better UX
      >
        <input 
          type="file" 
          accept="video/*" 
          ref={fileInputRef} 
          style={{ display: "none" }} 
          onChange={handleFileChange}
        />
        
        {previewUrl ? (
          <video src={previewUrl} controls className="preview-media" style={{ maxWidth: '100%' }} />
        ) : (
          <>
            <p className="upload-text">
              {isDragging ? "Drop Video Here!" : "Drag Your Video Here"}
            </p>
            <p className="upload-text">or</p>
            <span className="link" style={{ color: '#007BFF', textDecoration: 'underline' }}>Choose Video</span>
          </>
        )}
      </div>

      <button 
        className="action-btn" 
        onClick={handleAnalyze} 
        disabled={loading || !selectedVideo}
        style={{ marginTop: '15px' }}
      >
        {loading ? "🎬 EXTRACTING FRAMES & PROCESSING..." : "ANALYZE VIDEO"}
      </button>

      {/* Error Display */}
      {error && (
        <div style={{ color: "red", marginTop: "15px", fontWeight: "bold" }}>
          ❌ {error}
        </div>
      )}

      {/* Dynamic Result Display */}
      {result && (
        <div className="result-box" style={{ marginTop: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <h3>
            Status: {" "}
            <span className={result.status === "FAKE" ? "result-fake" : "result-real"} style={{ color: result.status === "FAKE" ? "red" : "green" }}>
              {result.status}
            </span>
          </h3>
          <p><strong>Confidence:</strong> {result.confidence}%</p>
          <p><strong>Frames Analyzed:</strong> {result.frames_analyzed}</p>
          <p style={{ fontSize: '0.85em', color: '#666', marginTop: '10px' }}>
            <em>{result.note}</em> <br/>
            Engine: {result.architecture_used}
          </p>
        </div>
      )}
    </div>
  );
};

export default VideoAnalysis;