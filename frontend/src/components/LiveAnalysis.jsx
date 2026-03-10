import React, { useState, useRef, useEffect } from "react";

const LiveAnalysis = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [liveResult, setLiveResult] = useState({ status: "Waiting for stream...", confidence: null });
  
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  
  // New Refs for WebSockets and Frame Extraction
  const wsRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));

  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false, 
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsStreaming(true);
      setLiveResult({ status: "Connecting to server...", confidence: null });

      // 1. Open the WebSocket connection to Django
      wsRef.current = new WebSocket("ws://127.0.0.1:8000/ws/live-stream/");

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket Connected");
        setLiveResult({ status: "Extracting frames...", confidence: null });
        startAnalysisLoop(); // Only start sending frames ONCE the tunnel is open
      };

      // 2. Listen for predictions coming back from Django
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status) {
          setLiveResult({ status: data.status, confidence: data.confidence });
        } else if (data.error) {
          console.error("Server Error:", data.error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ WebSocket Error:", error);
        setLiveResult({ status: "Connection Error. Is Django running?", confidence: null });
      };

      // Handle user clicking "Stop Sharing" from the browser's native UI
      stream.getVideoTracks()[0].onended = () => {
        stopScreenShare();
      };

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
    setLiveResult({ status: "Analysis Stopped", confidence: null });
    
    // Clear the analysis loop
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // 3. Gracefully close the WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const startAnalysisLoop = () => {
    // 4. Extract and send frames at 3 FPS (333ms intervals)
    intervalRef.current = setInterval(() => {
      // Ensure video is playing and WebSocket is ready
      if (videoRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");

        // Match the hidden canvas size to the actual video stream size
        if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
        }

        // Draw the current video frame onto the canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert the canvas drawing into a Base64 JPEG string (0.8 quality for speed)
        const frameData = canvas.toDataURL("image/jpeg", 0.8);

        // Package it into JSON and fire it down the WebSocket
        wsRef.current.send(JSON.stringify({ image: frameData }));
      }
    }, 333); 
  };

  // Cleanup to ensure WebSockets don't stay open if the user navigates away
  useEffect(() => {
    return () => {
      stopScreenShare();
    };
  }, []);

  return (
    <div className="container">
      <h2>LIVE ANALYSIS - MCL STREAM</h2>

      <div className="live-box" style={{ position: 'relative', width: '100%', maxWidth: '800px', margin: '0 auto' }}>
        <video 
          ref={videoRef} 
          autoPlay 
          playsInline 
          className="live-video" 
          muted
          style={{ width: '100%', borderRadius: '8px', backgroundColor: '#000' }}
        />
        {!isStreaming && (
          <p style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'white' }}>
            Click Start to share screen
          </p>
        )}
      </div>

      <button 
        className="action-btn" 
        onClick={isStreaming ? stopScreenShare : startScreenShare}
        style={{ 
          backgroundColor: isStreaming ? '#ff4d4d' : '#007bff', 
          color: '#fff', 
          padding: '10px 20px', 
          marginTop: '20px', 
          border: 'none', 
          borderRadius: '5px', 
          cursor: 'pointer' 
        }}
      >
        {isStreaming ? "STOP LIVE ANALYSIS" : "START LIVE ANALYSIS"}
      </button>

      <div className="result-box" style={{ marginTop: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px', textAlign: 'center' }}>
        <h3>
          Status: <span style={{ color: liveResult.status === "FAKE" ? "red" : liveResult.status === "REAL" ? "green" : "black" }}>
            {liveResult.status}
          </span>
        </h3>
        {liveResult.confidence && (
          <p><strong>Confidence:</strong> {liveResult.confidence}%</p>
        )}
      </div>
    </div>
  );
};

export default LiveAnalysis;