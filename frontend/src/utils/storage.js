export function getPendingResources() {
  try {
    const value = JSON.parse(localStorage.getItem("pendingResources") || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}
