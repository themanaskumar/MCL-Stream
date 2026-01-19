import React, { useState, useRef } from "react";

const ImageAnalysis = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false); // New state for visual feedback
  const fileInputRef = useRef(null);

  // Helper to process the file (used by both Input and Drop)
  const processFile = (file) => {
    if (file && file.type.startsWith("image/")) {
      setSelectedImage(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
    } else {
      alert("Please upload a valid image file.");
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    processFile(file);
  };

  // --- DRAG AND DROP HANDLERS ---
  const handleDragOver = (e) => {
    e.preventDefault(); // Essential: prevents browser from opening the file
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault(); // Essential: prevents browser from opening the file
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    processFile(file);
  };
  // ------------------------------

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const handleAnalyze = async () => {
    if (!selectedImage) return alert("Please upload an image first.");
    
    setLoading(true);

    const formData = new FormData();
    formData.append("image", selectedImage);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/analyze-image/", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      
      setLoading(false);
      
      // Update result state based on backend response
      // Example response: { status: "FAKE", confidence: 98.2 }
      if (data.status) {
        setResult(`${data.status} (${data.confidence}%)`);
      } else {
        alert("Analysis failed");
      }

    } catch (error) {
      console.error(error);
      setLoading(false);
      alert("Error connecting to server");
    }
  };

  return (
    <Layout>
      <h2>IMAGE ANALYSIS - MCL STREAM</h2>

      <div 
        className={`upload-box ${isDragging ? "drag-active" : ""}`}
        onClick={triggerFileInput}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          accept="image/*" 
          ref={fileInputRef} 
          style={{ display: "none" }} 
          onChange={handleFileChange}
        />
        
        {previewUrl ? (
          <img src={previewUrl} alt="Preview" className="preview-media" />
        ) : (
          <>
            <p className="upload-text">
              {isDragging ? "Drop it!" : "Drag Your Image Here"}
            </p>
            <p className="upload-text">or</p>
            <span className="link">Choose Image</span>
          </>
        )}
      </div>

      <button className="action-btn" onClick={handleAnalyze} disabled={loading}>
        {loading ? "ANALYZING..." : "ANALYZE IMAGE"}
      </button>

      {result && (
        <div className="result-box">
          Result: <span className={result.includes("FAKE") ? "result-fake" : "result-real"}>{result}</span>
        </div>
      )}
    </div>
  );
};

export default ImageAnalysis;