import React from "react";

const LiveAnalysis = () => {
  return (
    <div className="container">
      <h2>VIDEO ANALYSIS - MCL STREAM</h2>

      <div className="live-box">
        Placeholder for live video from screen sharing
      </div>

      <button className="action-btn">STOP LIVE ANALYSIS</button>

      <div className="result-box">
        Result will be displayed here in a loop (fake/real)
      </div>
    </div>
  );
};

export default LiveAnalysis;
