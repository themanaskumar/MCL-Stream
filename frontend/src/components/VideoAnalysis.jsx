import React from "react";

const VideoAnalysis = () => {
  return (
    <div className="container">
      <h2>VIDEO ANALYSIS - MCL STREAM</h2>

      <div className="upload-box">
        <p>Drag Your Video Here</p>
        <p>or</p>
        <span className="link">Choose Video</span>
      </div>

      <button className="action-btn">ANALYZE VIDEO</button>

      <div className="result-box">
        Result will be displayed here (fake/real)
      </div>
    </div>
  );
};

export default VideoAnalysis;
