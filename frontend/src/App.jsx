import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";

// Import components
import Footer from "./components/Footer";
import Home from "./components/Home";
import ImageAnalysis from "./components/ImageAnalysis";
import VideoAnalysis from "./components/VideoAnalysis";
import LiveAnalysis from "./components/LiveAnalysis";

// Import the logo here so it's available globally
import logo from "./assets/logo.png";

const App = () => {
  return (
    <Router>
      {/* This logo stays visible on EVERY page because 
         it is outside the <Routes> wrapper.
      */}
      <img 
        src={logo} 
        alt="MCL Stream Logo" 
        className="top-left-logo" 
        onClick={() => window.location.href = '/'} /* Optional: Click to go Home */
        style={{ cursor: 'pointer' }}
      />

      <div className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/image" element={<ImageAnalysis />} />
          <Route path="/video" element={<VideoAnalysis />} />
          <Route path="/live" element={<LiveAnalysis />} />
        </Routes>
      </div>

      <Footer />
    </Router>
  );
};

export default App;