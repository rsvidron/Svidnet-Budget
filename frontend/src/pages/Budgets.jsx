import { useState, useEffect } from 'react';
import { budgetsAPI, categoriesAPI } from '../services/api';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    category_id: '',
    amount: '',
    period: 'monthly',
    start_date: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    fetchBudgets();
    fetchCategories();
  }, []);

  const fetchBudgets = async () => {
    try {
      const response = await budgetsAPI.getAll();
      setBudgets(response.data);
    } catch (error) {
      console.error('Failed to fetch budgets:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await categoriesAPI.getAll();
      setCategories(response.data);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await budgetsAPI.create({
        ...formData,
        category_id: parseInt(formData.category_id),
        amount: parseFloat(formData.amount),
      });
      setShowForm(false);
      setFormData({
        category_id: '',
        amount: '',
        period: 'monthly',
        start_date: new Date().toISOString().split('T')[0],
      });
      fetchBudgets();
    } catch (error) {
      console.error('Failed to create budget:', error);
      alert('Failed to create budget');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this budget?')) return;

    try {
      await budgetsAPI.delete(id);
      fetchBudgets();
    } catch (error) {
      console.error('Failed to delete budget:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Budgets</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
          <PlusIcon className="h-5 w-5 mr-2" />
          New Budget
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Create New Budget</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                required
                className="input"
                value={formData.category_id}
                onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
              >
                <option value="">Select a category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
              <input
                type="number"
                step="0.01"
                required
                className="input"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                placeholder="1000.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
              <select
                className="input"
                value={formData.period}
                onChange={(e) => setFormData({ ...formData, period: e.target.value })}
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                required
                className="input"
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              />
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary">
                Create Budget
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {budgets.map((budget) => {
          const category = categories.find((c) => c.id === budget.category_id);
          return (
            <div key={budget.id} className="card">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold">{category?.name}</h3>
                  <p className="text-sm text-gray-500 capitalize">{budget.period}</p>
                </div>
                <button
                  onClick={() => handleDelete(budget.id)}
                  className="text-red-600 hover:text-red-900"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="mb-2">
                <div className="flex justify-between text-sm mb-1">
                  <span>Budget Amount</span>
                  <span className="font-semibold">${budget.amount.toFixed(2)}</span>
                </div>
              </div>
              <div className="text-xs text-gray-500">
                Started: {new Date(budget.start_date).toLocaleDateString()}
              </div>
            </div>
          );
        })}
      </div>

      {budgets.length === 0 && !showForm && (
        <div className="card text-center py-12">
          <p className="text-gray-500">No budgets created yet. Click "New Budget" to get started.</p>
        </div>
      )}
    </div>
  );
}
