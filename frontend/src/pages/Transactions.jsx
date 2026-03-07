import { useState, useEffect } from 'react';
import { transactionsAPI, categoriesAPI } from '../services/api';
import { format } from 'date-fns';
import { ArrowUpTrayIcon, PencilIcon, TrashIcon, ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    merchant: '',
    category_id: '',
  });
  const [sortConfig, setSortConfig] = useState({
    sortBy: 'date',
    sortOrder: 'desc',
  });
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);

  useEffect(() => {
    fetchTransactions();
    fetchCategories();
  }, []);

  useEffect(() => {
    if (loading === false) {
      fetchTransactions();
    }
  }, [sortConfig]);

  const fetchTransactions = async () => {
    try {
      const response = await transactionsAPI.getAll({
        ...filters,
        sort_by: sortConfig.sortBy,
        sort_order: sortConfig.sortOrder,
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
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

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = '';

    setUploadMessage(null);
    setUploading(true);
    try {
      const { data } = await transactionsAPI.upload(file);
      setUploadMessage({
        type: 'success',
        text: data.message || `Imported ${data.count ?? 0} transactions.`,
      });
      fetchTransactions();
    } catch (error) {
      const detail = error.response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : 'Failed to upload file. Please try again.';
      setUploadMessage({ type: 'error', text: message });
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (transaction) => {
    setEditingId(transaction.id);
    setEditData({
      merchant: transaction.merchant,
      amount: transaction.amount,
      category_id: transaction.category_id,
    });
  };

  const handleSave = async (id) => {
    try {
      await transactionsAPI.update(id, editData);
      setEditingId(null);
      fetchTransactions();
    } catch (error) {
      console.error('Failed to update transaction:', error);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this transaction?')) return;

    try {
      await transactionsAPI.delete(id);
      fetchTransactions();
    } catch (error) {
      console.error('Failed to delete transaction:', error);
    }
  };

  const handleSort = (column) => {
    setSortConfig((prev) => ({
      sortBy: column,
      sortOrder: prev.sortBy === column && prev.sortOrder === 'asc' ? 'desc' : 'asc',
    }));
  };

  const SortIcon = ({ column }) => {
    if (sortConfig.sortBy !== column) {
      return <ChevronUpIcon className="w-4 h-4 text-gray-400" />;
    }
    return sortConfig.sortOrder === 'asc' ? (
      <ChevronUpIcon className="w-4 h-4 text-blue-600" />
    ) : (
      <ChevronDownIcon className="w-4 h-4 text-blue-600" />
    );
  };

  const handleExport = async () => {
    try {
      const response = await transactionsAPI.export();
      const blob = new Blob([response.data.csv_data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `transactions-${format(new Date(), 'yyyy-MM-dd')}.csv`;
      a.click();
    } catch (error) {
      console.error('Failed to export transactions:', error);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading transactions...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Transactions</h1>
        <div className="flex gap-2">
          <button onClick={handleExport} className="btn btn-secondary">
            Export CSV
          </button>
          <label className={`btn btn-primary cursor-pointer ${uploading ? 'opacity-70 pointer-events-none' : ''}`}>
            <ArrowUpTrayIcon className="h-5 w-5 mr-2" />
            {uploading ? 'Uploading...' : 'Upload Statement'}
            <input type="file" className="hidden" accept=".csv,.pdf" onChange={handleFileUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {uploadMessage && (
        <div
          className={`p-4 rounded-lg ${
            uploadMessage.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
          role="alert"
        >
          {uploadMessage.text}
        </div>
      )}

      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <input
            type="text"
            placeholder="Search by merchant..."
            className="input"
            value={filters.merchant}
            onChange={(e) => setFilters({ ...filters, merchant: e.target.value })}
          />
          <select
            className="input"
            value={filters.category_id}
            onChange={(e) => setFilters({ ...filters, category_id: e.target.value })}
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>

        <button onClick={fetchTransactions} className="btn btn-primary mb-4">
          Apply Filters
        </button>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  onClick={() => handleSort('date')}
                >
                  <div className="flex items-center gap-1">
                    Date
                    <SortIcon column="date" />
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  onClick={() => handleSort('merchant')}
                >
                  <div className="flex items-center gap-1">
                    Merchant
                    <SortIcon column="merchant" />
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none min-w-[140px]"
                  onClick={() => handleSort('description')}
                >
                  <div className="flex items-center gap-1">
                    Description
                    <SortIcon column="description" />
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  onClick={() => handleSort('category')}
                >
                  <div className="flex items-center gap-1">
                    Category
                    <SortIcon column="category" />
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  onClick={() => handleSort('amount')}
                >
                  <div className="flex items-center gap-1">
                    Amount
                    <SortIcon column="amount" />
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  onClick={() => handleSort('type')}
                >
                  <div className="flex items-center gap-1">
                    Type
                    <SortIcon column="type" />
                  </div>
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {format(new Date(transaction.date), 'MMM dd, yyyy')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {editingId === transaction.id ? (
                      <input
                        type="text"
                        className="input"
                        value={editData.merchant}
                        onChange={(e) => setEditData({ ...editData, merchant: e.target.value })}
                      />
                    ) : (
                      transaction.merchant
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-[220px]" title={transaction.description || ''}>
                    {transaction.description || '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {editingId === transaction.id ? (
                      <select
                        className="input"
                        value={editData.category_id || ''}
                        onChange={(e) => setEditData({ ...editData, category_id: parseInt(e.target.value) })}
                      >
                        {categories.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span
                        className="px-2 py-1 rounded-full text-xs"
                        style={{
                          backgroundColor: categories.find((c) => c.id === transaction.category_id)?.color + '20',
                          color: categories.find((c) => c.id === transaction.category_id)?.color,
                        }}
                      >
                        {categories.find((c) => c.id === transaction.category_id)?.name || 'Uncategorized'}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {editingId === transaction.id ? (
                      <input
                        type="number"
                        step="0.01"
                        className="input"
                        value={editData.amount}
                        onChange={(e) => setEditData({ ...editData, amount: parseFloat(e.target.value) })}
                      />
                    ) : (
                      `$${transaction.amount.toFixed(2)}`
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        transaction.transaction_type === 'credit'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {transaction.transaction_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    {editingId === transaction.id ? (
                      <>
                        <button
                          onClick={() => handleSave(transaction.id)}
                          className="text-green-600 hover:text-green-900 mr-3"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-gray-600 hover:text-gray-900"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => handleEdit(transaction)}
                          className="text-primary-600 hover:text-primary-900 mr-3"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(transaction.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
