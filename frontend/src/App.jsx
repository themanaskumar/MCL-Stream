import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";

import Header from "./components/Header";
import Footer from "./components/Footer";
import Home from "./components/Home";
import ImageAnalysis from "./components/ImageAnalysis";
import VideoAnalysis from "./components/VideoAnalysis";
import LiveAnalysis from "./components/LiveAnalysis";

const App = () => {
  return (
    <Router>
      <Header />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/image" element={<ImageAnalysis />} />
        <Route path="/video" element={<VideoAnalysis />} />
        <Route path="/live" element={<LiveAnalysis />} />
      </Routes>

      <Footer />
    </Router>
  );
};

export default App;
