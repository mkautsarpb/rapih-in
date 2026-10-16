// Currency metadata used for price formatting. One table, one reason to change:
// add or correct a currency here.

export const CURRENCIES = {
  IDR: {
    code: 'IDR',
    name: 'Indonesian rupiah',
    symbol: 'Rp',
    decimals: 0,
  },
  USD: {
    code: 'USD',
    name: 'US dollar',
    symbol: '$',
    decimals: 2,
  },
  EUR: {
    code: 'EUR',
    name: 'Euro',
    symbol: '€',
    decimals: 2,
  },
  JPY: {
    code: 'JPY',
    name: 'Japanese yen',
    symbol: '¥',
    decimals: 0,
  },
  SGD: {
    code: 'SGD',
    name: 'Singapore dollar',
    symbol: 'S$',
    decimals: 2,
  },
  MYR: {
    code: 'MYR',
    name: 'Malaysian ringgit',
    symbol: 'RM',
    decimals: 2,
  },
  GBP: {
    code: 'GBP',
    name: 'Pound sterling',
    symbol: '£',
    decimals: 2,
  },
  AUD: {
    code: 'AUD',
    name: 'Australian dollar',
    symbol: 'A$',
    decimals: 2,
  },
  CNY: {
    code: 'CNY',
    name: 'Chinese yuan',
    symbol: '¥',
    decimals: 2,
  },
  KRW: {
    code: 'KRW',
    name: 'South Korean won',
    symbol: '₩',
    decimals: 0,
  },
  THB: {
    code: 'THB',
    name: 'Thai baht',
    symbol: '฿',
    decimals: 2,
  },
  PHP: {
    code: 'PHP',
    name: 'Philippine peso',
    symbol: '₱',
    decimals: 2,
  },
  VND: {
    code: 'VND',
    name: 'Vietnamese dong',
    symbol: '₫',
    decimals: 0,
  },
  INR: {
    code: 'INR',
    name: 'Indian rupee',
    symbol: '₹',
    decimals: 2,
  },
  CHF: {
    code: 'CHF',
    name: 'Swiss franc',
    symbol: 'CHF',
    decimals: 2,
  },
  CAD: {
    code: 'CAD',
    name: 'Canadian dollar',
    symbol: 'C$',
    decimals: 2,
  },
  NZD: {
    code: 'NZD',
    name: 'New Zealand dollar',
    symbol: 'NZ$',
    decimals: 2,
  },
  HKD: {
    code: 'HKD',
    name: 'Hong Kong dollar',
    symbol: 'HK$',
    decimals: 2,
  },
  SAR: {
    code: 'SAR',
    name: 'Saudi riyal',
    symbol: 'SR',
    decimals: 2,
  },
  AED: {
    code: 'AED',
    name: 'UAE dirham',
    symbol: 'AED',
    decimals: 2,
  },
  SEK: {
    code: 'SEK',
    name: 'Swedish krona',
    symbol: 'kr',
    decimals: 2,
  },
  NOK: {
    code: 'NOK',
    name: 'Norwegian krone',
    symbol: 'kr',
    decimals: 2,
  },
  DKK: {
    code: 'DKK',
    name: 'Danish krone',
    symbol: 'kr',
    decimals: 2,
  },
  BRL: {
    code: 'BRL',
    name: 'Brazilian real',
    symbol: 'R$',
    decimals: 2,
  },
};

export function currencyCodes() {
  return Object.keys(CURRENCIES);
}

export function isSupportedCurrency(code) {
  return Object.prototype.hasOwnProperty.call(CURRENCIES, code);
}
