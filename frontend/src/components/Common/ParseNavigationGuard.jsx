import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppContext } from "../../context/AppContext";

const SUCCESS_STATUSES = new Set(["completed", "success", "succeeded", "done"]);
const RESET_STATUSES = new Set(["idle", "ready", "running", "queued", "pending"]);
const ERROR_STATUSES = new Set(["failed", "error"]);

function ParseNavigationGuard() {
  const { parseState } = useAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const hasNavigatedRef = useRef(false);

  useEffect(() => {
    const status = parseState?.status || "idle";

    // 1) 在解析未完成或出错的情况下，阻止停留在结果页，强制回到首页
    if (!SUCCESS_STATUSES.has(status) && location.pathname === "/results") {
      if (!hasNavigatedRef.current) {
        hasNavigatedRef.current = true;
        navigate("/", { replace: true });
      }
      return;
    }

    // 2) 状态在准备/运行/空闲/失败等，重置导航开关，等待后续状态变化
    if (RESET_STATUSES.has(status) || ERROR_STATUSES.has(status)) {
      hasNavigatedRef.current = false;
      return;
    }

    // 3) 解析成功时，如不在结果页则跳转到结果页
    if (!hasNavigatedRef.current && SUCCESS_STATUSES.has(status) && location.pathname !== "/results") {
      hasNavigatedRef.current = true;
      navigate("/results");
    }
  }, [parseState?.status, location.pathname, navigate]);

  return null;
}

export default ParseNavigationGuard;
