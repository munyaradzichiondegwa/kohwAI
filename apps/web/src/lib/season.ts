/** Insurance season label for a date, e.g. 2026-11-05 -> "2026-27" (season runs Nov 1 – Mar 31). */
export function currentSeason(d: Date = new Date()): string {
  const y = d.getMonth() >= 10 ? d.getFullYear() : d.getFullYear() - 1;   // getMonth(): Nov = 10
  return `${y}-${String((y + 1) % 100).padStart(2, '0')}`;
}
