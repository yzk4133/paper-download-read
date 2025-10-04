import { createContext, useContext, useMemo, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState([]);
  const [parseState, setParseState] = useState({ status: "idle", message: "等待解析", updatedAt: null, sourceDir: null });
  const [excelInfo, setExcelInfo] = useState({ status: "idle", message: "Excel 尚未生成", file: null, path: null, updatedAt: null });
  const [storage, setStorage] = useState({ pdfDir: "", excelDir: "" });
  const [keywordPlan, setKeywordPlan] = useState([]);

  const value = useMemo(
    () => ({
      progress,
      setProgress,
      results,
      setResults,
      parseState,
      setParseState,
      excelInfo,
      setExcelInfo,
      storage,
      setStorage,
      keywordPlan,
      setKeywordPlan,
    }),
    [progress, results, parseState, excelInfo, storage, keywordPlan]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used inside AppProvider");
  }
  return context;
}
