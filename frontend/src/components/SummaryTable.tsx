import { useMemo, useState } from 'react';
import { downloadCsv } from '../api';
import type { SymbolRow } from '../api';

type Props = {
  rows: SymbolRow[];
};

const sectorMap: Record<string, string> = {
  AAPL: 'Tech', MSFT: 'Tech', NVDA: 'Tech', GOOGL: 'Tech', AMZN: 'Tech', META: 'Tech', NFLX: 'Tech',
  IBM: 'Tech', INTC: 'Tech', AMD: 'Tech', CSCO: 'Tech', ORCL: 'Tech',
  JPM: 'Finance', V: 'Finance', MA: 'Finance',
  UNH: 'Healthcare', PFE: 'Healthcare', ABBV: 'Healthcare',
  XOM: 'Energy', CVX: 'Energy',
};

function sparklinePath(values: number[], width = 100, height = 28) {
  if (values.length < 2) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const stepX = width / (values.length - 1);
  const firstY = height - ((values[0] - min) / range) * height;
  let path = `M 0 ${firstY}`;

  for (let index = 1; index < values.length; index += 1) {
    const x = index * stepX;
    const y = height - ((values[index] - min) / range) * height;
    path += ` H ${x} V ${y}`;
  }

  return path;
}

export default function SummaryTable({ rows }: Props) {
  const pageSize = 8;
  const [query, setQuery] = useState('');
  const [activeTag, setActiveTag] = useState('All');
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<'symbol' | 'close' | 'daily_return_pct' | 'volatility_30d'>('symbol');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const tags = useMemo(() => ['All', ...new Set(Object.values(sectorMap))], []);

  const filteredRows = useMemo(() => {
    const lower = query.trim().toLowerCase();

    return [...rows]
      .filter((row) => {
        const matchesQuery = !lower || row.symbol.toLowerCase().includes(lower);
        const sector = sectorMap[row.symbol] ?? 'Other';
        const matchesTag = activeTag === 'All' || sector === activeTag;
        return matchesQuery && matchesTag;
      })
      .sort((a, b) => {
        const left = Number(a[sortKey]);
        const right = Number(b[sortKey]);
        const comparison = left > right ? 1 : left < right ? -1 : 0;
        return sortDirection === 'asc' ? comparison : -comparison;
      });
  }, [rows, query, activeTag, sortKey, sortDirection]);

  const toggleSort = (key: 'symbol' | 'close' | 'daily_return_pct' | 'volatility_30d') => {
    setPage(1);
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const visibleRows = filteredRows.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="card summary-card">
      <div className="card-header split">
        <h2>Summary</h2>
        <div className="toolbar toolbar-compact">
          <input
            className="search-input"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Search symbol..."
          />
          <button className="export-btn" onClick={() => rows.forEach((row) => downloadCsv(row.symbol))}>
            Export All
          </button>
        </div>
      </div>

      <div className="filter-row">
        {tags.map((tag) => (
          <button
            key={tag}
            className={tag === activeTag ? 'chip active' : 'chip'}
            onClick={() => {
              setActiveTag(tag);
              setPage(1);
            }}
          >
            {tag}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="clickable" onClick={() => toggleSort('symbol')}>Symbol</th>
              <th>Trend</th>
              <th className="clickable" onClick={() => toggleSort('close')}>Latest Close</th>
              <th className="clickable" onClick={() => toggleSort('daily_return_pct')}>Daily Return %</th>
              <th className="clickable" onClick={() => toggleSort('volatility_30d')}>Volatility (30d)</th>
              <th>Export</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const sparkValues = Array.from({ length: 7 }, (_, idx) => {
                const scale = (idx - 3) * 0.18;
                const base = Number(row.close) * (1 + Number(row.daily_return_pct) / 100 * scale);
                return base;
              });
              const trendColor = Number(row.daily_return_pct) >= 0 ? '#10b981' : '#f43f5e';

              return (
                <tr key={row.symbol}>
                  <td className="ticker-cell">{row.symbol}</td>
                  <td className="spark-cell">
                    <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="sparkline" aria-label={`${row.symbol} trend`}>
                      <path d={sparklinePath(sparkValues)} stroke={trendColor} strokeWidth="2" fill="none" strokeLinecap="round" />
                    </svg>
                  </td>
                  <td className="money-cell">${Number(row.close).toFixed(2)}</td>
                  <td>
                    <span className={Number(row.daily_return_pct) >= 0 ? 'change-pill good' : 'change-pill bad'}>
                      <span className="step-arrow" aria-hidden="true" />
                      {Number(row.daily_return_pct).toFixed(2)}%
                    </span>
                  </td>
                  <td>{Number(row.volatility_30d).toFixed(2)}</td>
                  <td>
                    <button className="row-action" onClick={() => downloadCsv(row.symbol)} aria-label={`Download ${row.symbol} CSV`}>
                      <span className="download-mark" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span className="pagination-count">
          Showing {filteredRows.length ? (page - 1) * pageSize + 1 : 0}-{Math.min(page * pageSize, filteredRows.length)} of {filteredRows.length}
        </span>
        <div className="pagination-actions">
          <button className="page-button" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
          <span className="page-number">{page} / {pageCount}</span>
          <button className="page-button" disabled={page === pageCount} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>Next</button>
        </div>
      </div>
    </div>
  );
}
