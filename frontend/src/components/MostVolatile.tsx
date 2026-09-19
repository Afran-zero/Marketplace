import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { VolatileRow } from '../api';

type Props = {
  rows: VolatileRow[];
};

export default function MostVolatile({ rows }: Props) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>Most Volatile</h2>
      </div>
      <div className="mini-chart volatility-chart">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rows} layout="vertical" margin={{ top: 10, right: 28, left: 10, bottom: 25 }}>
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" opacity={0.22} horizontal={false} />
            <XAxis type="number" hide domain={['auto', 'auto']} />
            <YAxis dataKey="symbol" type="category" width={50} tick={{ fill: '#687582', fontFamily: 'DM Sans, sans-serif', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Bar dataKey="volatility_30d" fill="#818cf8" radius={[0, 4, 4, 0]}>
              <LabelList dataKey="volatility_30d" position="right" formatter={(value: number) => Number(value).toFixed(2)} fill="#94a3b8" fontSize={11} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
