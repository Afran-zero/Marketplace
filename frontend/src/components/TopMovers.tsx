import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Movement } from '../api';

type Props = {
  gainers: Movement[];
  losers: Movement[];
};

const percentTick = (value: number) => `${Number(value).toFixed(0)}%`;

export default function TopMovers({ gainers, losers }: Props) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>Top Movers</h2>
      </div>
      <div className="movers-grid">
        <div>
          <h3>Top 5 Gainers</h3>
          <div className="mini-chart">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={gainers} layout="vertical" margin={{ top: 10, right: 18, left: 8, bottom: 10 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" opacity={0.22} horizontal={false} />
                <XAxis type="number" hide domain={['auto', 'auto']} />
                <YAxis dataKey="symbol" type="category" width={54} tick={{ fill: '#687582', fontFamily: 'DM Sans, sans-serif', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(value: number) => [`${Number(value).toFixed(2)}%`, 'Daily Return']}
                  contentStyle={{ background: '#ffffff', border: '1px solid #dfe5ea', borderRadius: 4 }}
                />
                <Bar dataKey="daily_return_pct" fill="#10b981" radius={[0, 4, 4, 0]}>
                  <LabelList dataKey="daily_return_pct" position="right" formatter={percentTick} fill="#94a3b8" fontSize={11} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h3>Top 5 Losers</h3>
          <div className="mini-chart">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={losers} layout="vertical" margin={{ top: 10, right: 18, left: 8, bottom: 10 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" opacity={0.22} horizontal={false} />
                <XAxis type="number" hide domain={['auto', 'auto']} />
                <YAxis dataKey="symbol" type="category" width={54} tick={{ fill: '#687582', fontFamily: 'DM Sans, sans-serif', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(value: number) => [`${Number(value).toFixed(2)}%`, 'Daily Return']}
                  contentStyle={{ background: '#ffffff', border: '1px solid #dfe5ea', borderRadius: 4 }}
                />
                <Bar dataKey="daily_return_pct" fill="#f43f5e" radius={[0, 4, 4, 0]}>
                  <LabelList dataKey="daily_return_pct" position="right" formatter={percentTick} fill="#94a3b8" fontSize={11} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
