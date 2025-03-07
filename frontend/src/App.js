import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import WorkOrders from './pages/WorkOrders';
import Equipment from './pages/Equipment';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/work-orders" element={<WorkOrders />} />
                <Route path="/equipment" element={<Equipment />} />
            </Routes>
        </Router>
    );
}

export default App;