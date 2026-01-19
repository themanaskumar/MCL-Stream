import React from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";

const Home = () => {
  const navigate = useNavigate();

  return (
    <Layout>
      <h2>Choose from below options</h2>

      <div className="button-group">
        <button onClick={() => navigate("/image")}>IMAGE ANALYSIS</button>
        <button onClick={() => navigate("/video")}>VIDEO ANALYSIS</button>
        <button onClick={() => navigate("/live")}>LIVE ANALYSIS</button>
      </div>
    </Layout>
  );
};

export default Home;
