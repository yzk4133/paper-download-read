import { useEffect } from "react";
import api from "../services/api";
import { useAppContext } from "../context/AppContext";

export default function useExcelStatus(interval = 5000) {
  const { setExcelInfo } = useAppContext();

  useEffect(() => {
    let timer;

    const fetchStatus = async () => {
      try {
        const { data } = await api.get("/excel/status");
        if (data) {
          setExcelInfo((prev) => ({
            status: data.status || "idle",
            message: data.message || "",
            file: data.file || null,
            path: data.path || (prev ? prev.path : null),
            updatedAt: data.updated_at || null,
          }));
        }
      } catch (error) {
        // ignore polling errors
      }
    };

    fetchStatus();
    timer = setInterval(fetchStatus, interval);
    return () => clearInterval(timer);
  }, [interval, setExcelInfo]);
}
