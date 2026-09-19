import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { downloadCsv } from '../api';
import type { PricePoint } from '../api';

type Props = {
  symbol: string;
  data: PricePoint[];
  onSymbolChange: (symbol: string) => void;
  symbols: string[];
};

export default function MainChart({ symbol, data, onSymbolChange, symbols }: Props) {
  const gradientId = `price-fill-${symbol}`;

  return (
    <div className="card chart-card">
      <div className="card-header split">
        <h2>Price Trend</h2>
        <div className="toolbar">
          <select value={symbol} onChange={(e) => onSymbolChange(e.target.value)}>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button className="primary-btn" onClick={() => downloadCsv(symbol)}>
            Download CSV
          </button>
        </div>
      </div>
      <div className="chart-legend" aria-label="Chart series">
        <span className="legend-pill close">Close</span>
        <span className="legend-pill average-short">7d Avg</span>
        <span className="legend-pill average-long">30d Avg</span>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 18, left: 8, bottom: 12 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" opacity={0.3} vertical={false} />
            <XAxis dataKey="price_date" tick={{ fontSize: 11, fontFamily: 'DM Sans, sans-serif', fill: '#687582' }} axisLine={false} tickLine={false} />
            <YAxis
              tick={{ fontSize: 11, fontFamily: 'DM Sans, sans-serif', fill: '#687582' }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
            />
            <Tooltip
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #dfe5ea',
                borderRadius: 4,
              }}
              labelStyle={{ color: '#17212b' }}
            />
            <Area type="monotone" dataKey="close" stroke="none" fill={`url(#${gradientId})`} fillOpacity={1} />
            <Line type="monotone" dataKey="close" stroke="#38bdf8" strokeWidth={3} dot={false} name="Close" />
            <Line type="monotone" dataKey="moving_avg_7d" stroke="#64748b" strokeWidth={2} strokeDasharray="6 6" dot={false} name="7d Avg" />
            <Line type="monotone" dataKey="moving_avg_30d" stroke="#94a3b8" strokeWidth={2} strokeDasharray="10 6" dot={false} name="30d Avg" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
