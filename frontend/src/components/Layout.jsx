import React from "react";
import Header from "./Header";
import Footer from "./Footer";

const Layout = ({ children }) => {
  return (
    <div className="app">
      
      <div className="container">
        {children}
      </div>
     
    </div>
  );
};

export default Layout;
