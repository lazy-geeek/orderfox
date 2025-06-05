/**
 * Formats large numbers with K, M, or B suffixes for better readability.
 * 
 * @param num - The number to format
 * @param precision - Number of decimal places to show (default: 2)
 * @returns Formatted string with appropriate suffix
 * 
 * @example
 * formatLargeNumber(1234567890, 2) // "1.23B"
 * formatLargeNumber(1234567, 2) // "1.23M"
 * formatLargeNumber(1234, 2) // "1.23K"
 * formatLargeNumber(123.456, 2) // "123.46"
 * formatLargeNumber(-1234, 2) // "-1.23K"
 */
export function formatLargeNumber(num: number, precision: number = 2): string {
  const isNegative = num < 0;
  const absNum = Math.abs(num);
  
  let formattedValue: string;
  
  if (absNum >= 1_000_000_000) {
    // Billions
    const value = absNum / 1_000_000_000;
    formattedValue = value.toFixed(precision) + 'B';
  } else if (absNum >= 1_000_000) {
    // Millions
    const value = absNum / 1_000_000;
    formattedValue = value.toFixed(precision) + 'M';
  } else if (absNum >= 1_000) {
    // Thousands
    const value = absNum / 1_000;
    formattedValue = value.toFixed(precision) + 'K';
  } else {
    // Less than 1000
    formattedValue = absNum.toFixed(precision);
  }
  
  return isNegative ? '-' + formattedValue : formattedValue;
}