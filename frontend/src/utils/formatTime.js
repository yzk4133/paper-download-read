import dayjs from "dayjs";

export function formatDateTime(value) {
  if (!value) return "-";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}
