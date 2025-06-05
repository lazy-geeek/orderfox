import { formatLargeNumber } from './formatting';

describe('formatLargeNumber', () => {
  describe('Billions range (>= 1,000,000,000)', () => {
    it('should format positive billions correctly', () => {
      expect(formatLargeNumber(1234567890, 2)).toBe('1.23B');
      expect(formatLargeNumber(5678901234, 2)).toBe('5.68B');
      expect(formatLargeNumber(1000000000, 2)).toBe('1.00B');
    });

    it('should format negative billions correctly', () => {
      expect(formatLargeNumber(-1234567890, 2)).toBe('-1.23B');
      expect(formatLargeNumber(-5678901234, 2)).toBe('-5.68B');
    });

    it('should handle different precision values for billions', () => {
      expect(formatLargeNumber(1234567890, 0)).toBe('1B');
      expect(formatLargeNumber(1234567890, 1)).toBe('1.2B');
      expect(formatLargeNumber(1234567890, 3)).toBe('1.235B');
    });
  });

  describe('Millions range (>= 1,000,000)', () => {
    it('should format positive millions correctly', () => {
      expect(formatLargeNumber(1234567, 2)).toBe('1.23M');
      expect(formatLargeNumber(5678901, 2)).toBe('5.68M');
      expect(formatLargeNumber(1000000, 2)).toBe('1.00M');
    });

    it('should format negative millions correctly', () => {
      expect(formatLargeNumber(-1234567, 2)).toBe('-1.23M');
      expect(formatLargeNumber(-5678901, 2)).toBe('-5.68M');
    });

    it('should handle different precision values for millions', () => {
      expect(formatLargeNumber(1234567, 0)).toBe('1M');
      expect(formatLargeNumber(1234567, 1)).toBe('1.2M');
      expect(formatLargeNumber(1234567, 3)).toBe('1.235M');
    });
  });

  describe('Thousands range (>= 1,000)', () => {
    it('should format positive thousands correctly', () => {
      expect(formatLargeNumber(1234, 2)).toBe('1.23K');
      expect(formatLargeNumber(5678, 2)).toBe('5.68K');
      expect(formatLargeNumber(1000, 2)).toBe('1.00K');
    });

    it('should format negative thousands correctly', () => {
      expect(formatLargeNumber(-1234, 2)).toBe('-1.23K');
      expect(formatLargeNumber(-5678, 2)).toBe('-5.68K');
    });

    it('should handle different precision values for thousands', () => {
      expect(formatLargeNumber(1234, 0)).toBe('1K');
      expect(formatLargeNumber(1234, 1)).toBe('1.2K');
      expect(formatLargeNumber(1234, 3)).toBe('1.234K');
    });
  });

  describe('Numbers less than 1,000', () => {
    it('should format positive numbers less than 1000 correctly', () => {
      expect(formatLargeNumber(123.456, 2)).toBe('123.46');
      expect(formatLargeNumber(999.99, 2)).toBe('999.99');
      expect(formatLargeNumber(1, 2)).toBe('1.00');
    });

    it('should format negative numbers less than 1000 correctly', () => {
      expect(formatLargeNumber(-123.456, 2)).toBe('-123.46');
      expect(formatLargeNumber(-999.99, 2)).toBe('-999.99');
    });

    it('should handle different precision values for numbers less than 1000', () => {
      expect(formatLargeNumber(123.456, 0)).toBe('123');
      expect(formatLargeNumber(123.456, 1)).toBe('123.5');
      expect(formatLargeNumber(123.456, 3)).toBe('123.456');
    });
  });

  describe('Zero handling', () => {
    it('should format zero correctly with different precision values', () => {
      expect(formatLargeNumber(0, 2)).toBe('0.00');
      expect(formatLargeNumber(0, 0)).toBe('0');
      expect(formatLargeNumber(0, 1)).toBe('0.0');
      expect(formatLargeNumber(0, 3)).toBe('0.000');
    });
  });

  describe('Edge cases for range transitions', () => {
    it('should handle transitions between thousands and millions', () => {
      expect(formatLargeNumber(999999, 2)).toBe('1000.00K');
      expect(formatLargeNumber(1000000, 2)).toBe('1.00M');
      expect(formatLargeNumber(1000001, 2)).toBe('1.00M');
    });

    it('should handle transitions between millions and billions', () => {
      expect(formatLargeNumber(999999999, 2)).toBe('1000.00M');
      expect(formatLargeNumber(1000000000, 2)).toBe('1.00B');
      expect(formatLargeNumber(1000000001, 2)).toBe('1.00B');
    });

    it('should handle transitions between hundreds and thousands', () => {
      expect(formatLargeNumber(999.99, 2)).toBe('999.99');
      expect(formatLargeNumber(1000, 2)).toBe('1.00K');
      expect(formatLargeNumber(1000.01, 2)).toBe('1.00K');
    });
  });

  describe('Rounding behavior', () => {
    it('should round correctly using toFixed behavior', () => {
      // Test standard rounding rules
      expect(formatLargeNumber(1234.5, 0)).toBe('1K');
      expect(formatLargeNumber(1234.4, 0)).toBe('1K');
      expect(formatLargeNumber(1234.567, 2)).toBe('1.23K');
      expect(formatLargeNumber(1234.564, 2)).toBe('1.23K');
    });

    it('should round correctly for thousands', () => {
      expect(formatLargeNumber(1234.5, 0)).toBe('1K');
      expect(formatLargeNumber(1235.6, 0)).toBe('1K');
      expect(formatLargeNumber(1999.9, 0)).toBe('2K');
    });

    it('should round correctly for millions', () => {
      expect(formatLargeNumber(1234567.8, 2)).toBe('1.23M');
      expect(formatLargeNumber(1235567.8, 2)).toBe('1.24M');
    });

    it('should round correctly for billions', () => {
      expect(formatLargeNumber(1234567890.8, 2)).toBe('1.23B');
      expect(formatLargeNumber(1235567890.8, 2)).toBe('1.24B');
    });
  });

  describe('Default precision parameter', () => {
    it('should use precision 2 as default', () => {
      expect(formatLargeNumber(1234567890)).toBe('1.23B');
      expect(formatLargeNumber(1234567)).toBe('1.23M');
      expect(formatLargeNumber(1234)).toBe('1.23K');
      expect(formatLargeNumber(123.456)).toBe('123.46');
    });
  });

  describe('Large numbers and extreme cases', () => {
    it('should handle very large numbers', () => {
      expect(formatLargeNumber(999999999999, 2)).toBe('1000.00B');
      expect(formatLargeNumber(1000000000000, 2)).toBe('1000.00B');
    });

    it('should handle very small positive numbers', () => {
      expect(formatLargeNumber(0.01, 2)).toBe('0.01');
      expect(formatLargeNumber(0.001, 3)).toBe('0.001');
    });

    it('should handle very small negative numbers', () => {
      expect(formatLargeNumber(-0.01, 2)).toBe('-0.01');
      expect(formatLargeNumber(-0.001, 3)).toBe('-0.001');
    });
  });
});