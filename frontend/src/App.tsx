import { useEffect, useMemo, useState } from 'react';
import {
  fetchMostVolatile,
  fetchSymbolHistory,
  fetchSymbols,
  fetchTopMovers,
  type Movement,
  type PricePoint,
  type SymbolRow,
  type VolatileRow,
} from './api';
import MainChart from './components/MainChart';
import MostVolatile from './components/MostVolatile';
import SummaryTable from './components/SummaryTable';
import TopMovers from './components/TopMovers';

type TopMoversState = {
  gainers: Movement[];
  losers: Movement[];
};

export default function App() {
  const [symbols, setSymbols] = useState<SymbolRow[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState('IBM');
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [topMovers, setTopMovers] = useState<TopMoversState>({ gainers: [], losers: [] });
  const [mostVolatile, setMostVolatile] = useState<VolatileRow[]>([]);

  useEffect(() => {
    fetchSymbols()
      .then((rows) => {
        setSymbols(rows);
        if (rows.length && !rows.some((row) => row.symbol === selectedSymbol)) {
          setSelectedSymbol(rows[0].symbol);
        }
      })
      .catch((error) => {
        console.error('Failed to load symbols', error);
      });

    fetchTopMovers()
      .then(setTopMovers)
      .catch((error) => {
        console.error('Failed to load top movers', error);
      });

    fetchMostVolatile()
      .then(setMostVolatile)
      .catch((error) => {
        console.error('Failed to load most volatile', error);
      });
  }, []);

  useEffect(() => {
    if (!selectedSymbol) return;
    fetchSymbolHistory(selectedSymbol, 30)
      .then((response) => {
        setHistory(response.data);
      })
      .catch((error) => {
        console.error('Failed to load symbol history', error);
      });
  }, [selectedSymbol]);

  const symbolChoices = useMemo(() => symbols.map((row) => row.symbol).sort(), [symbols]);

  const summaryMetrics = useMemo(() => {
    if (!symbols.length) {
      return { topGainer: null, avgVolatility: 0, marketSentiment: 'Neutral', alertCount: 0 };
    }

    const topGainer = [...symbols].sort((a, b) => Number(b.daily_return_pct) - Number(a.daily_return_pct))[0];
    const avgVolatility = symbols.reduce((sum, row) => sum + Number(row.volatility_30d), 0) / symbols.length;
    const avgMove = symbols.reduce((sum, row) => sum + Number(row.daily_return_pct), 0) / symbols.length;
    const marketSentiment = avgMove >= 0 ? 'Bullish' : 'Bearish';
    const alertCount = symbols.filter((row) => Math.abs(Number(row.daily_return_pct)) > 1.5).length;

    return {
      topGainer,
      avgVolatility,
      marketSentiment,
      alertCount,
    };
  }, [symbols]);

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <span className="eyebrow">LIVE MARKET DATA</span>
          <h1>MarketPlus — Stock Analytics Dashboard</h1>
        </div>
      </header>

      <section className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">Top Market Gainer</span>
          <strong className="metric-value">
            {summaryMetrics.topGainer ? summaryMetrics.topGainer.symbol : '—'}
          </strong>
          <span className="kpi-trend good">
            {summaryMetrics.topGainer ? `${Number(summaryMetrics.topGainer.daily_return_pct).toFixed(2)}%` : '—'}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Market Sentiment</span>
          <strong className="metric-value">{summaryMetrics.marketSentiment}</strong>
          <span className="kpi-trend neutral">{symbols.length ? `${Number((summaryMetrics.avgVolatility || 0)).toFixed(2)} avg vol` : '—'}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Average 30D Volatility</span>
          <strong className="metric-value">{summaryMetrics.avgVolatility.toFixed(2)}</strong>
          <span className="kpi-trend neutral">30-day view</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Active Alerts Tracked</span>
          <strong className="metric-value">{summaryMetrics.alertCount}</strong>
          <span className="kpi-trend warning">monitoring</span>
        </div>
      </section>

      <section className="widget widget-full">
        <SummaryTable rows={symbols} />
      </section>

      <div className="dashboard-row">
        <section className="widget widget-main">
          <MainChart
            symbol={selectedSymbol}
            data={history}
            symbols={symbolChoices}
            onSymbolChange={setSelectedSymbol}
          />
        </section>

        <div className="widget-stack">
          <section className="widget">
            <TopMovers gainers={topMovers.gainers} losers={topMovers.losers} />
          </section>
          <section className="widget">
            <MostVolatile rows={mostVolatile} />
          </section>
        </div>
      </div>
    </div>
  );
}
