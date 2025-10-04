import api from "./api";

export async function fetchStorageInfo() {
  const { data } = await api.get("/system/storage");
  return data;
}
