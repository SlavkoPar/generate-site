import { Link, Route, Routes } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Home from './pages/Home';
import ItemPage from './pages/ItemPage';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <div className="layout">
      <header className="top">
        <Link to="/">🥗 Fruits &amp; Vegetables</Link>
      </header>
      <Sidebar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/item/:slug" element={<ItemPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}
