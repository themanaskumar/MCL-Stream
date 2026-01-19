import React, { useState } from "react";
import Layout from "../components/Layout";

const ImageAnalysis = () => {
  const [image, setImage] = useState(null);

  return (
    <Layout>
      <h2>IMAGE ANALYSIS - MCL STREAM</h2>

      <div
        className="upload-box"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setImage(e.dataTransfer.files[0]);
        }}
      >
        <p>{image ? image.name : "Drag Your Image Here"}</p>
        <p>or</p>

        <label className="link">
          Choose Image
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => setImage(e.target.files[0])}
          />
        </label>
      </div>

      <button className="action-btn">ANALYZE IMAGE</button>

      <div className="result-box">
        Result will be displayed here (fake/real)
      </div>
    </Layout>
  );
};

export default ImageAnalysis;
