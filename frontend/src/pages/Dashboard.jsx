import { useState, useEffect } from 'react';
import { analyticsAPI } from '../services/api';
import { PieChart, Pie, Cell, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await analyticsAPI.getDashboard();
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  const { summary, spending_by_category, monthly_trends, budget_progress, top_merchants } = dashboardData;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Spent This Month</p>
              <p className="text-2xl font-bold text-gray-900">
                ${summary.total_spent_this_month?.toFixed(2) || '0.00'}
              </p>
            </div>
            <ArrowUpIcon className="h-8 w-8 text-red-500" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Budgeted</p>
              <p className="text-2xl font-bold text-gray-900">
                ${summary.total_budgeted?.toFixed(2) || '0.00'}
              </p>
            </div>
            <ArrowDownIcon className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Budget Remaining</p>
              <p className={`text-2xl font-bold ${summary.budget_remaining >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${summary.budget_remaining?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Spending by Category</h2>
          {spending_by_category?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={spending_by_category}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.category}: $${entry.amount.toFixed(0)}`}
                >
                  {spending_by_category.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No spending data available</p>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Monthly Trends</h2>
          {monthly_trends?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthly_trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                <Legend />
                <Line type="monotone" dataKey="expenses" stroke="#EF4444" name="Expenses" />
                <Line type="monotone" dataKey="income" stroke="#10B981" name="Income" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No trend data available</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Budget Progress</h2>
          {budget_progress?.length > 0 ? (
            <div className="space-y-4">
              {budget_progress.map((budget, index) => (
                <div key={index}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{budget.category}</span>
                    <span className="text-gray-600">
                      ${budget.spent.toFixed(0)} / ${budget.budgeted.toFixed(0)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        budget.percentage > 100 ? 'bg-red-500' : budget.percentage > 80 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(budget.percentage, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {budget.percentage.toFixed(1)}% used
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No budgets set</p>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Top Merchants</h2>
          {top_merchants?.length > 0 ? (
            <div className="space-y-3">
              {top_merchants.map((merchant, index) => (
                <div key={index} className="flex justify-between items-center">
                  <div>
                    <p className="font-medium">{merchant.merchant}</p>
                    <p className="text-sm text-gray-500">{merchant.count} transactions</p>
                  </div>
                  <p className="font-semibold text-gray-900">${merchant.total.toFixed(2)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No merchant data available</p>
          )}
        </div>
      </div>
    </div>
  );
}
