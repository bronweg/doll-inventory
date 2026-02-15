import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { DollsList } from './pages/DollsList';
import { DollDetail } from './pages/DollDetail';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/list/:scope" element={<DollsList />} />
        <Route path="/doll/:id" element={<DollDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

