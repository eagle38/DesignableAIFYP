import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import SculptStudio from "./pages/SculptStudio";
import RoomPreview from "./pages/Roompreview";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/signup" element={<Signup />} />
        
        <Route path="/sculpt" element={<SculptStudio />} /> 
        <Route path="/room-preview" element={<RoomPreview />} />
      </Routes>
    </Router>
  );
}

export default App;