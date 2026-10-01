import { format, parseISO, isValid } from "date-fns";

/**
 * Format ISO date string or Date object to readable UTC string
 * Example: "2026-09-26T14:30:00Z" -> "Sep 26, 2026 · 14:30 UTC"
 */
export function formatDetectedDate(dateInput) {
  if (!dateInput) return "Unknown";
  try {
    const d =
      typeof dateInput === "string" ? parseISO(dateInput) : new Date(dateInput);
    if (!isValid(d)) {
      return String(dateInput);
    }
    return format(d, "MMM d, yyyy · HH:mm 'UTC'");
  } catch (err) {
    return String(dateInput);
  }
}
