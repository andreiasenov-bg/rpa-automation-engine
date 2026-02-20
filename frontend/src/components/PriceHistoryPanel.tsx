import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, BarChart3, RefreshCw } from 'lucide-react';

interface PriceProduct {
  product_id: string; marketplace: string; product_title: string | null;
  min_price: number; max_price: number; avg_price: number; current_price: number; data_points: number;
}

export default function PriceHistoryPanel({ workflowId }: { workflowId: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const r = await fetch('/api/v1/price-history/workflow/' + workflowId + '/summary', {
        headers: { 'Authorization': 'Bearer ' + token },
      });
      if (r.ok) setData(await r.json());
    } catch (e) {}
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, [workflowId]);

  if (loading) return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center gap-2 text-slate-400">
        <RefreshCw className="w-4 h-4 animate-spin" /> Loading price data...
      </div>
    </div>
  );

  if (!data || data.total_products === 0) return null;

  const sorted = [...data.products].sort((a: any, b: any) => (b.max_price - b.min_price) - (a.max_price - a.min_price));
  const avgAll = data.products.reduce((s: number, p: any) => s + (p.avg_price || 0), 0) / data.products.length;
  const totalPts = data.products.reduce((s: number, p: any) => s + p.data_points, 0);
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-emerald-500" /> Price Analytics
          <span className="text-xs font-normal text-slate-400">({data.total_products} products)</span>
        </h3>
        <button onClick={fetchData} className="text-xs text-slate-400 hover:text-blue-500 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 text-center">
          <div className="text-xs text-emerald-600 dark:text-emerald-400">Avg Price</div>
          <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300">{avgAll.toFixed(2)} €</div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
          <div className="text-xs text-blue-600 dark:text-blue-400">Products</div>
          <div className="text-lg font-bold text-blue-700 dark:text-blue-300">{data.total_products}</div>
        </div>
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 text-center">
          <div className="text-xs text-purple-600 dark:text-purple-400">Data Points</div>
          <div className="text-lg font-bold text-purple-700 dark:text-purple-300">{totalPts}</div>
        </div>
      </div>

      <div className="overflow-x-auto max-h-[400px] overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="min-w-full text-xs">
          <thead className="bg-slate-50 dark:bg-slate-900 sticky top-0 z-10">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Product</th>
              <th className="px-3 py-2 text-right font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Current</th>
              <th className="px-3 py-2 text-right font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Min</th>
              <th className="px-3 py-2 text-right font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Max</th>
              <th className="px-3 py-2 text-right font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Spread</th>
              <th className="px-3 py-2 text-center font-semibold text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">Trend</th>
            </tr>
          </thead>          <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
            {sorted.map((p: any, i: number) => {
              const spread = p.max_price - p.min_price;
              const spreadPct = p.min_price > 0 ? (spread / p.min_price * 100) : 0;
              const trend = p.current_price > p.avg_price ? 'up' : p.current_price < p.avg_price ? 'down' : 'flat';
              return (
                <tr key={p.product_id + p.marketplace} className={i % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50/50 dark:bg-slate-800/50'}>
                  <td className="px-3 py-2 text-slate-700 dark:text-slate-300 max-w-[250px] truncate" title={p.product_title || p.product_id}>
                    <span className="font-mono text-[10px] text-slate-400">{p.product_id}</span>
                    {p.product_title && <div className="truncate">{p.product_title}</div>}
                  </td>
                  <td className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-300">{p.current_price?.toFixed(2)} €</td>
                  <td className="px-3 py-2 text-right text-emerald-600">{p.min_price?.toFixed(2)} €</td>
                  <td className="px-3 py-2 text-right text-red-500">{p.max_price?.toFixed(2)} €</td>
                  <td className="px-3 py-2 text-right">
                    <span className={spreadPct > 10 ? 'text-orange-500 font-bold' : 'text-slate-500'}>
                      {spread.toFixed(2)} € ({spreadPct.toFixed(1)}%)
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {trend === 'up' && <TrendingUp className="w-4 h-4 text-red-500 inline" />}
                    {trend === 'down' && <TrendingDown className="w-4 h-4 text-emerald-500 inline" />}
                    {trend === 'flat' && <Minus className="w-4 h-4 text-slate-400 inline" />}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}