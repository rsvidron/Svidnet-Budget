import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyticsAPI, categoriesAPI } from '../services/api';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import {
  ArrowTrendingUpIcon, ArrowTrendingDownIcon, BanknotesIcon, CreditCardIcon,
  ChartBarIcon, ShoppingBagIcon, FunnelIcon, CalendarDaysIcon,
} from '@heroicons/react/24/outline';
import { format, parseISO } from 'date-fns';

const DATE_PRESETS = [
  { value: 'this_month', label: 'This month' },
  { value: 'last_3_months', label: 'Last 3 months' },
  { value: 'last_6_months', label: 'Last 6 months' },
  { value: 'last_year', label: 'Last year' },
];

const TRANSACTION_TYPE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'debit', label: 'Expenses' },
  { value: 'credit', label: 'Income' },
  { value: 'transfer', label: 'Transfers' },
];

function TrendBadge({ value, invertColor = false }) {
  if (value == null || value === 0) return <span className="text-xs text-gray-400">—</span>;
  const isPositive = value > 0;
  const showRed = invertColor ? isPositive : !isPositive;
  return (
    <span className={`text-xs ${showRed ? 'text-red-600' : 'text-green-600'}`}>
      {isPositive ? '+' : ''}{value}% vs previous
    </span>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    preset: 'this_month',
    start_date: '',
    end_date: '',
    category_ids: [],
    category_exclude: false,
    transaction_types: '',
  });
  const [largestSort, setLargestSort] = useState({ key: 'amount', dir: 'desc' });
  const [trendView, setTrendView] = useState('monthly');

  const queryParams = useMemo(() => {
    const p = { preset: filters.preset || 'this_month' };
    if (filters.start_date) p.start_date = filters.start_date;
    if (filters.end_date) p.end_date = filters.end_date;
    if (filters.category_ids?.length) {
      p.category_ids = filters.category_ids.join(',');
      p.category_exclude = filters.category_exclude;
    }
    if (filters.transaction_types) p.transaction_types = filters.transaction_types;
    return p;
  }, [filters]);

  useEffect(() => {
    categoriesAPI.getAll().then((r) => setCategories(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    analyticsAPI
      .getDashboard(queryParams)
      .then((res) => setDashboardData(res.data))
      .catch(() => setDashboardData(null))
      .finally(() => setLoading(false));
  }, [queryParams]);

  const toggleCategory = (id) => {
    setFilters((prev) => ({
      ...prev,
      category_ids: prev.category_ids.includes(id)
        ? prev.category_ids.filter((c) => c !== id)
        : [...prev.category_ids, id],
    }));
  };

  const sortedLargest = useMemo(() => {
    if (!dashboardData?.largest_transactions?.length) return [];
    const list = [...dashboardData.largest_transactions];
    const k = largestSort.key;
    const dir = largestSort.dir === 'asc' ? 1 : -1;
    list.sort((a, b) => {
      if (k === 'date') return dir * (new Date(a.date) - new Date(b.date));
      if (k === 'amount') return dir * (a.amount - b.amount);
      return 0;
    });
    return list;
  }, [dashboardData?.largest_transactions, largestSort]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-500">Unable to load dashboard</div>
      </div>
    );
  }

  const {
    summary,
    category_breakdown,
    largest_transactions,
    merchant_analysis,
    monthly_trends,
    category_trends,
    budget_progress,
    insights,
  } = dashboardData;
  const ch = summary?.change_vs_previous || {};

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>

      {/* Global filters */}
      <div className="card border border-gray-200">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <CalendarDaysIcon className="h-5 w-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Date range</span>
          </div>
          <select
            className="input w-auto"
            value={filters.preset}
            onChange={(e) => setFilters((f) => ({ ...f, preset: e.target.value }))}
          >
            {DATE_PRESETS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Category</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.slice(0, 12).map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => toggleCategory(cat.id)}
                className={`px-3 py-1 rounded-full text-sm border ${
                  filters.category_ids.includes(cat.id)
                    ? 'bg-primary-100 border-primary-500 text-primary-800'
                    : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
          {filters.category_ids.length > 0 && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.category_exclude}
                onChange={(e) => setFilters((f) => ({ ...f, category_exclude: e.target.checked }))}
              />
              Exclude selected
            </label>
          )}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Type</span>
            <select
              className="input w-auto"
              value={filters.transaction_types}
              onChange={(e) => setFilters((f) => ({ ...f, transaction_types: e.target.value }))}
            >
              {TRANSACTION_TYPE_OPTIONS.map((o) => (
                <option key={o.value || 'all'} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Spending</p>
              <p className="text-xl font-bold text-gray-900">
                ${(summary?.total_spending ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
              <TrendBadge value={ch.total_spending_pct} invertColor />
            </div>
            <BanknotesIcon className="h-8 w-8 text-red-500/80" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Income</p>
              <p className="text-xl font-bold text-gray-900">
                ${(summary?.total_income ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
              <TrendBadge value={ch.total_income_pct} />
            </div>
            <ArrowTrendingUpIcon className="h-8 w-8 text-green-500/80" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Net Cash Flow</p>
              <p className={`text-xl font-bold ${(summary?.net_cash_flow ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${(summary?.net_cash_flow ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
              <TrendBadge value={ch.net_cash_flow_pct} />
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Avg Monthly Spending</p>
              <p className="text-xl font-bold text-gray-900">
                ${(summary?.average_monthly_spending ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
            </div>
            <ChartBarIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Largest Expense</p>
              <p className="text-xl font-bold text-gray-900">
                ${(summary?.largest_single_expense ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
            </div>
            <CreditCardIcon className="h-8 w-8 text-amber-500/80" />
          </div>
        </div>
        <div className="card">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Transactions</p>
              <p className="text-xl font-bold text-gray-900">{summary?.transaction_count ?? 0}</p>
              <TrendBadge value={ch.transaction_count_pct} />
            </div>
            <ShoppingBagIcon className="h-8 w-8 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Category breakdown - horizontal bar */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Spending by Category</h2>
        {category_breakdown?.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.min(400, category_breakdown.length * 36)}>
            <BarChart layout="vertical" data={category_breakdown} margin={{ left: 20, right: 60 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => `$${v}`} />
              <YAxis type="category" dataKey="category" width={120} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Spent']} />
              <Bar
                dataKey="amount"
                fill="#6366f1"
                radius={[0, 4, 4, 0]}
                onClick={(data) => data?.category_id && navigate(`/transactions?category_id=${data.category_id}`)}
                cursor="pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 py-8 text-center">No spending data in this period</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Largest transactions */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Largest Transactions</h2>
          {sortedLargest.length > 0 ? (
            <>
              <div className="flex gap-2 mb-3">
                <button
                  type="button"
                  className={`text-sm ${largestSort.key === 'amount' ? 'font-semibold' : ''}`}
                  onClick={() => setLargestSort((s) => ({ key: 'amount', dir: s.key === 'amount' && s.dir === 'desc' ? 'asc' : 'desc' }))}
                >
                  Sort by amount
                </button>
                <button
                  type="button"
                  className={`text-sm ${largestSort.key === 'date' ? 'font-semibold' : ''}`}
                  onClick={() => setLargestSort((s) => ({ key: 'date', dir: s.key === 'date' && s.dir === 'desc' ? 'asc' : 'desc' }))}
                >
                  Sort by date
                </button>
              </div>
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-2">Date</th>
                      <th className="py-2">Merchant</th>
                      <th className="py-2">Category</th>
                      <th className="py-2 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedLargest.map((t) => (
                      <tr key={t.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-2">{format(parseISO(t.date), 'MMM d, yyyy')}</td>
                        <td className="py-2">{t.merchant}</td>
                        <td className="py-2">{t.category}</td>
                        <td className="py-2 text-right font-medium">${t.amount.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-gray-500 py-8 text-center">No transactions in this period</p>
          )}
        </div>

        {/* Merchant analysis */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Top Merchants</h2>
          {merchant_analysis?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={merchant_analysis} layout="vertical" margin={{ left: 20, right: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `$${v}`} />
                <YAxis type="category" dataKey="merchant" width={140} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value, name) => (name === 'total' ? [`$${value.toFixed(2)}`, 'Total'] : [value, name])}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.merchant}
                />
                <Bar dataKey="total" fill="#10b981" radius={[0, 4, 4, 0]} name="total" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 py-8 text-center">No merchant data</p>
          )}
        </div>
      </div>

      {/* Monthly trends */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Income vs Expenses</h2>
          <div className="flex gap-2">
            <button
              type="button"
              className={`text-sm px-2 py-1 rounded ${trendView === 'monthly' ? 'bg-primary-100 text-primary-800' : 'text-gray-600'}`}
              onClick={() => setTrendView('monthly')}
            >
              Monthly
            </button>
          </div>
        </div>
        {monthly_trends?.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={monthly_trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(v) => `$${v}`} />
              <Tooltip formatter={(v) => `$${Number(v).toFixed(2)}`} />
              <Legend />
              <Line type="monotone" dataKey="income" stroke="#10b981" name="Income" strokeWidth={2} />
              <Line type="monotone" dataKey="expenses" stroke="#ef4444" name="Expenses" strokeWidth={2} />
              <Line type="monotone" dataKey="net" stroke="#6366f1" name="Net" strokeWidth={2} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 py-8 text-center">No trend data</p>
        )}
      </div>

      {/* Category trends over time */}
      {category_trends?.length > 0 && (() => {
        const keys = Object.keys(category_trends[0] || {}).filter((k) => k !== 'month');
        const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];
        return (
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Category Trends Over Time</h2>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={category_trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(v) => `$${v}`} />
                <Tooltip formatter={(v) => `$${Number(v).toFixed(2)}`} />
                <Legend />
                {keys.map((key, i) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={colors[i % colors.length]}
                    name={key}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Budget progress */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Budget Performance</h2>
          {budget_progress?.length > 0 ? (
            <div className="space-y-4">
              {budget_progress.map((b, i) => (
                <div key={i}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{b.category}</span>
                    <span className="text-gray-600">
                      ${b.spent.toFixed(0)} / ${b.budgeted.toFixed(0)}
                      {b.percentage > 100 && (
                        <span className="ml-2 text-red-600 font-medium">Over budget</span>
                      )}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        b.percentage > 100 ? 'bg-red-500' : b.percentage > 80 ? 'bg-amber-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(b.percentage, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {b.percentage.toFixed(1)}% used
                    {b.remaining >= 0 && ` · $${b.remaining.toFixed(0)} remaining`}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 py-8 text-center">No budgets set</p>
          )}
        </div>

        {/* Insights */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Insights</h2>
          {insights?.length > 0 ? (
            <ul className="space-y-3">
              {insights.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
                  <span className="text-primary-500 mt-0.5">•</span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 py-8 text-center">No insights for this period</p>
          )}
        </div>
      </div>
    </div>
  );
}
