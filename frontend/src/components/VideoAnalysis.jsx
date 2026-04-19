import React, { useState, useRef } from "react";

const VideoAnalysis = () => {
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); 
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Helper to process the file (used by both Input and Drop)
  const processFile = (file) => {
    if (file && file.type.startsWith("video/")) {
      setSelectedVideo(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null); 
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
        style={{ cursor: 'pointer' }} 
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
        {loading ? "🎬 EXTRACTING & PROCESSING..." : "ANALYZE VIDEO"}
      </button>
      
      {/* Error Display */}
      {error && (
        <div style={{ color: "red", marginTop: "15px", fontWeight: "bold", textAlign: "center" }}>
          ❌ {error}
        </div>
      )}

      {/* NEW DUAL-MODALITY RESULT DASHBOARD */}
      {result && (
        <div style={{ marginTop: '30px', padding: '20px', border: '1px solid #444', borderRadius: '12px', backgroundColor: '#0a0a2a', color: 'white', maxWidth: '700px', margin: '30px auto' }}>
          
          <h2 style={{ textAlign: 'center', color: result.overall_status === "FAKE" ? "#ff4d4d" : "#28a745", marginBottom: '20px' }}>
            OVERALL VERDICT: {result.overall_status}
          </h2>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
            
            {/* VIDEO RESULTS */}
            <div style={{ flex: 1, minWidth: '250px', padding: '15px', backgroundColor: '#11113a', borderRadius: '8px', border: '1px solid #333' }}>
              <h3 style={{ textAlign: 'center', borderBottom: '1px solid #444', paddingBottom: '10px', marginTop: 0 }}>📸 Video Scan</h3>
              <p><strong>Status:</strong> <span style={{ color: result.video?.status === "FAKE" ? "#ff4d4d" : "#28a745", fontWeight: 'bold' }}>{result.video?.status || "N/A"}</span></p>
              <p><strong>Confidence:</strong> {result.video?.confidence ? `${result.video.confidence}%` : "N/A"}</p>
              {result.video?.frames_analyzed && <p><strong>Frames Analyzed:</strong> {result.video.frames_analyzed}</p>}
              <p style={{ fontSize: '0.8em', color: '#aaa', marginTop: '10px' }}>Engine: CNN-LSTM Hybrid</p>
            </div>

            {/* AUDIO RESULTS */}
            <div style={{ flex: 1, minWidth: '250px', padding: '15px', backgroundColor: '#11113a', borderRadius: '8px', border: '1px solid #333' }}>
              <h3 style={{ textAlign: 'center', borderBottom: '1px solid #444', paddingBottom: '10px', marginTop: 0 }}>🎤 Audio Scan</h3>
              <p><strong>Status:</strong> <span style={{ color: result.audio?.status === "FAKE" ? "#ff4d4d" : result.audio?.status === "NO_AUDIO" ? "#ffcc00" : "#28a745", fontWeight: 'bold' }}>{result.audio?.status || "N/A"}</span></p>
              <p><strong>Confidence:</strong> {result.audio?.confidence ? `${result.audio.confidence}%` : "N/A"}</p>
              {result.audio?.status === "NO_AUDIO" && <p style={{ fontSize: '0.9em', color: '#ffcc00' }}>No audio track found in this video.</p>}
              <p style={{ fontSize: '0.8em', color: '#aaa', marginTop: '10px' }}>Engine: 1D-CNN + BiLSTM</p>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

export default VideoAnalysis;