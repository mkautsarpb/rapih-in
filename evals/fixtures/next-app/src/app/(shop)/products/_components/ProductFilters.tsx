'use client';
import { useState } from 'react';

export function ProductFilters() {
  const [q, setQ] = useState('');
  return <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search" />;
}
