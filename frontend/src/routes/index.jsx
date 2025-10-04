import { Routes, Route, Navigate } from "react-router-dom";
import HomePage from "../pages/HomePage";
import ResultPage from "../pages/ResultPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/results" element={<ResultPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
