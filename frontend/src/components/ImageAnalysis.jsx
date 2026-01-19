import React from "react";

const ImageAnalysis = () => {
  return (
    <div className="container">
      <h2>IMAGE ANALYSIS - MCL STREAM</h2>

      <div className="upload-box">
        <p>Drag Your Image Here</p>
        <p>or</p>
        <span className="link">Choose Image</span>
      </div>

      <button className="action-btn">ANALYZE IMAGE</button>

      <div className="result-box">
        Result will be displayed here (fake/real)
      </div>
    </div>
  );
};

export default ImageAnalysis;
