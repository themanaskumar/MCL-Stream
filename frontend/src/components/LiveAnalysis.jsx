import React, { useState, useRef } from "react";

const LiveAnalysis = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [liveResult, setLiveResult] = useState("Waiting for stream...");
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false, // Change to true if you need system audio
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsStreaming(true);
      setLiveResult("Initializing Analysis...");

      // Handle user clicking "Stop Sharing" from the browser's native UI
      stream.getVideoTracks()[0].onended = () => {
        stopScreenShare();
      };

      // Start the mock analysis loop
      startAnalysisLoop();

    } catch (err) {
      console.error("Error accessing screen:", err);
    }
  };

  const stopScreenShare = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setLiveResult("Analysis Stopped");
    
    // Clear the analysis loop
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const startAnalysisLoop = () => {
    // This mocks receiving data from the backend every 1 second
    intervalRef.current = setInterval(() => {
      // Randomly switching to simulate live detection
      const mockStatus = Math.random() > 0.5 ? "REAL" : "FAKE";
      setLiveResult(mockStatus);
    }, 1000); 
  };

  return (
    <div className="container">
      <h2>LIVE ANALYSIS - MCL STREAM</h2>

      <div className="live-box">
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          className="live-video" 
          muted
        />
        {!isStreaming && <p style={{position: 'absolute'}}>Click Start to share screen</p>}
      </div>

      <button 
        className="action-btn" 
        onClick={isStreaming ? stopScreenShare : startScreenShare}
        style={{ backgroundColor: isStreaming ? '#ff4d4d' : '' }} // Red when stopping
      >
        {isStreaming ? "STOP LIVE ANALYSIS" : "START LIVE ANALYSIS"}
      </button>

      <div className="result-box">
        Current Frame: <span className={liveResult === "FAKE" ? "result-fake" : "result-real"}>{liveResult}</span>
      </div>
    </div>
  );
};

export default LiveAnalysis;