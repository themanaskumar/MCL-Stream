import React, { useState } from "react";
import Layout from "../components/Layout";

const VideoAnalysis = () => {
  const [video, setVideo] = useState(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setVideo(e.dataTransfer.files[0]);
  };

  return (
    <Layout>
      <h2>VIDEO ANALYSIS - MCL STREAM</h2>

      <div
        className="upload-box"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <p>{video ? video.name : "Drag Your Video Here"}</p>
        <p>or</p>

        <label className="link">
          Choose Video
          <input
            type="file"
            hidden
            accept="video/*"
            onChange={(e) => setVideo(e.target.files[0])}
          />
        </label>
      </div>

      <button className="action-btn">ANALYZE VIDEO</button>

      <div className="result-box">
        Result will be displayed here
      </div>
    </Layout>
  );
};

export default VideoAnalysis;
