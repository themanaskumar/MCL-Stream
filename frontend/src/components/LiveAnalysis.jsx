import React, { useState, useRef, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from "recharts";

const LiveAnalysis = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  
  const [videoResult, setVideoResult] = useState({ status: "Waiting...", confidence: null });
  const [audioResult, setAudioResult] = useState({ status: "Waiting...", confidence: null });
  
  const [chartData, setChartData] = useState([]);
  const latestScores = useRef({ video: 0, audio: 0 });

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  
  const videoIntervalRef = useRef(null);
  const audioIntervalRef = useRef(null);
  const chartIntervalRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const wsRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));

  const startScreenShare = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true, 
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsStreaming(true);
      setVideoResult({ status: "Connecting...", confidence: null });
      setAudioResult({ status: "Connecting...", confidence: null });
      setChartData([]); 

      wsRef.current = new WebSocket("ws://127.0.0.1:8000/ws/live-stream/");

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket Connected");
        startVideoAnalysisLoop();
        startAudioAnalysisLoop(stream);
        startChartLoop(); 
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        let fakeProb = 0;
        if (data.status === "FAKE") {
            fakeProb = data.confidence;
        } else if (data.status === "REAL") {
            fakeProb = 100 - data.confidence;
        }

        if (data.type === "video_result") {
          setVideoResult({ status: data.status, confidence: data.confidence });
          
          // Only plot actual predictions on the chart, ignore "Buffering" or "No Face" strings
          if (data.status === "FAKE" || data.status === "REAL") {
              latestScores.current.video = fakeProb;
          }
        } else if (data.type === "audio_result") {
          setAudioResult({ status: data.status, confidence: data.confidence });
          latestScores.current.audio = fakeProb;
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ WebSocket Error:", error);
      };

      stream.getVideoTracks()[0].onended = () => stopScreenShare();

    } catch (err) {
      console.error("Error accessing screen:", err);
    }
  };

  const startAudioAnalysisLoop = (stream) => {
    const audioTracks = stream.getAudioTracks();
    if (audioTracks.length === 0) {
      setAudioResult({ status: "No Audio Track Shared", confidence: null });
      return;
    }

    const audioOnlyStream = new MediaStream([audioTracks[0]]);

    audioIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return;

      const mediaRecorder = new MediaRecorder(audioOnlyStream);
      const chunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = () => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ audio: reader.result }));
          }
        };
      };

      mediaRecorder.start();
      setTimeout(() => {
        if (mediaRecorder.state === "recording") mediaRecorder.stop();
      }, 1450); 
    }, 1500); 
  };

  const startVideoAnalysisLoop = () => {
    videoIntervalRef.current = setInterval(() => {
      if (videoRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
        const video = videoRef.current;
        if (!video.videoWidth) return; // Prevent crashing if video hasn't loaded yet

        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");

        // THE FIX: Smart Downscaling. Prevents WebSocket Payload Crashes.
        const MAX_WIDTH = 640;
        let canvasWidth = video.videoWidth;
        let canvasHeight = video.videoHeight;

        if (canvasWidth > MAX_WIDTH) {
            const scale = MAX_WIDTH / canvasWidth;
            canvasWidth = MAX_WIDTH;
            canvasHeight = Math.floor(canvasHeight * scale);
        }

        if (canvas.width !== canvasWidth || canvas.height !== canvasHeight) {
            canvas.width = canvasWidth;
            canvas.height = canvasHeight;
        }

        context.drawImage(video, 0, 0, canvasWidth, canvasHeight);
        
        // 0.85 Quality drops file size massively while retaining ML-ready detail
        const frameData = canvas.toDataURL("image/jpeg", 0.85); 
        wsRef.current.send(JSON.stringify({ image: frameData }));
      }
    }, 333); 
  };

  const startChartLoop = () => {
    chartIntervalRef.current = setInterval(() => {
      const timeString = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit', second:'2-digit' });
      
      setChartData(prevData => {
        const newData = [...prevData, { 
            time: timeString, 
            video: latestScores.current.video, 
            audio: latestScores.current.audio 
        }];
        return newData.length > 20 ? newData.slice(newData.length - 20) : newData;
      });
    }, 1000);
  };

  const stopScreenShare = () => {
    if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    if (videoIntervalRef.current) clearInterval(videoIntervalRef.current);
    if (audioIntervalRef.current) clearInterval(audioIntervalRef.current);
    if (chartIntervalRef.current) clearInterval(chartIntervalRef.current);
    if (wsRef.current) wsRef.current.close();
    
    setIsStreaming(false);
  };

  useEffect(() => {
    return () => stopScreenShare();
  }, []);

  return (
    <div className="container" style={{ paddingBottom: '50px' }}>
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

      <div style={{ textAlign: 'center' }}>
        <button 
          className="action-btn" 
          onClick={isStreaming ? stopScreenShare : startScreenShare}
          style={{ 
            backgroundColor: isStreaming ? '#ff4d4d' : '#007bff', 
            color: '#fff', 
            padding: '12px 24px', 
            marginTop: '20px', 
            border: 'none', 
            borderRadius: '5px', 
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isStreaming ? "STOP LIVE ANALYSIS" : "START LIVE ANALYSIS"}
        </button>
      </div>

      <div className="results-wrapper">
        <div className="result-box">
          <h3 style={{ margin: '0 0 10px 0', borderBottom: '1px solid rgba(255,255,255,0.2)', paddingBottom: '10px' }}>📸 Video Scan</h3>
          <h2 className={videoResult.status === "FAKE" ? "result-fake" : videoResult.status === "REAL" ? "result-real" : ""}>
            {videoResult.status}
          </h2>
          {videoResult.confidence && <p style={{ fontSize: '0.9rem', color: '#ccc' }}>Confidence: {videoResult.confidence}%</p>}
        </div>

        <div className="result-box">
          <h3 style={{ margin: '0 0 10px 0', borderBottom: '1px solid rgba(255,255,255,0.2)', paddingBottom: '10px' }}>🎤 Audio Scan</h3>
          <h2 className={audioResult.status === "FAKE" ? "result-fake" : audioResult.status === "REAL" ? "result-real" : ""}>
            {audioResult.status}
          </h2>
          {audioResult.confidence && <p style={{ fontSize: '0.9rem', color: '#ccc' }}>Confidence: {audioResult.confidence}%</p>}
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="chart-container">
          <h3 className="chart-title">Deepfake Probability Tracker</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} stroke="#ffffff" />
              <XAxis dataKey="time" tick={{ fontSize: 12, fill: '#cccccc' }} stroke="#555" />
              <YAxis domain={[0, 100]} tickFormatter={(tick) => `${tick}%`} tick={{ fill: '#cccccc' }} stroke="#555" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#000', borderColor: '#333', color: '#fff' }} 
                formatter={(value) => `${value.toFixed(1)}% Fake Prob.`} 
              />
              <Legend wrapperStyle={{ color: '#ccc' }} />
              <ReferenceLine y={50} stroke="#ff4d4d" strokeDasharray="3 3" label={{ position: 'top', value: 'FAKE THRESHOLD', fill: '#ff4d4d', fontSize: 12 }} />
              <Line type="monotone" dataKey="video" name="Video Anomaly" stroke="#00d4ff" strokeWidth={3} dot={false} animationDuration={300} />
              <Line type="monotone" dataKey="audio" name="Audio Anomaly" stroke="#b145e9" strokeWidth={3} dot={false} animationDuration={300} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default LiveAnalysis;