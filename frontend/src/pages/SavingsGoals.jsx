import { useState, useEffect } from 'react';
import { savingsGoalsAPI } from '../services/api';
import { PlusIcon, TrashIcon, BanknotesIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export default function SavingsGoals() {
  const [goals, setGoals] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    target_amount: '',
    target_date: '',
    description: '',
  });
  const [contributionAmount, setContributionAmount] = useState({});

  useEffect(() => {
    fetchGoals();
  }, []);

  const fetchGoals = async () => {
    try {
      const response = await savingsGoalsAPI.getAll();
      setGoals(response.data);
    } catch (error) {
      console.error('Failed to fetch savings goals:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await savingsGoalsAPI.create({
        ...formData,
        target_amount: parseFloat(formData.target_amount),
      });
      setShowForm(false);
      setFormData({
        name: '',
        target_amount: '',
        target_date: '',
        description: '',
      });
      fetchGoals();
    } catch (error) {
      console.error('Failed to create savings goal:', error);
      alert('Failed to create savings goal');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this savings goal?')) return;

    try {
      await savingsGoalsAPI.delete(id);
      fetchGoals();
    } catch (error) {
      console.error('Failed to delete savings goal:', error);
    }
  };

  const handleContribute = async (id) => {
    const amount = parseFloat(contributionAmount[id]);
    if (!amount || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }

    try {
      await savingsGoalsAPI.contribute(id, amount);
      setContributionAmount({ ...contributionAmount, [id]: '' });
      fetchGoals();
    } catch (error) {
      console.error('Failed to contribute to savings goal:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Savings Goals</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
          <PlusIcon className="h-5 w-5 mr-2" />
          New Goal
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Create New Savings Goal</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Goal Name</label>
              <input
                type="text"
                required
                className="input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Emergency Fund"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Amount</label>
              <input
                type="number"
                step="0.01"
                required
                className="input"
                value={formData.target_amount}
                onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                placeholder="10000.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Date (Optional)</label>
              <input
                type="date"
                className="input"
                value={formData.target_date}
                onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
              <textarea
                className="input"
                rows="3"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Save for unexpected expenses"
              />
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary">
                Create Goal
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {goals.map((goal) => {
          const percentage = (goal.current_amount / goal.target_amount) * 100;
          return (
            <div key={goal.id} className={`card ${goal.is_completed ? 'border-2 border-green-500' : ''}`}>
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{goal.name}</h3>
                  {goal.description && (
                    <p className="text-sm text-gray-500 mt-1">{goal.description}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(goal.id)}
                  className="text-red-600 hover:text-red-900"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>

              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Progress</span>
                  <span className="font-semibold">
                    ${goal.current_amount.toFixed(2)} / ${goal.target_amount.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
                      goal.is_completed ? 'bg-green-500' : 'bg-primary-500'
                    }`}
                    style={{ width: `${Math.min(percentage, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{percentage.toFixed(1)}% complete</p>
              </div>

              {goal.target_date && (
                <div className="text-sm text-gray-600 mb-4">
                  Target: {format(new Date(goal.target_date), 'MMM dd, yyyy')}
                </div>
              )}

              {!goal.is_completed && (
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.01"
                    className="input flex-1"
                    placeholder="Amount"
                    value={contributionAmount[goal.id] || ''}
                    onChange={(e) =>
                      setContributionAmount({ ...contributionAmount, [goal.id]: e.target.value })
                    }
                  />
                  <button
                    onClick={() => handleContribute(goal.id)}
                    className="btn btn-primary"
                  >
                    <BanknotesIcon className="h-5 w-5" />
                  </button>
                </div>
              )}

              {goal.is_completed && (
                <div className="text-center py-2 bg-green-50 rounded-lg text-green-700 font-semibold">
                  Goal Completed!
                </div>
              )}
            </div>
          );
        })}
      </div>

      {goals.length === 0 && !showForm && (
        <div className="card text-center py-12">
          <p className="text-gray-500">No savings goals yet. Click "New Goal" to get started.</p>
        </div>
      )}
    </div>
  );
}
