import { useState, useEffect, useMemo, Fragment } from 'react';
import { useSearchParams } from 'react-router-dom';
import { transactionsAPI, categoriesAPI, accountsAPI } from '../services/api';
import { format } from 'date-fns';
import {
  ArrowUpTrayIcon,
  PencilIcon,
  TrashIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

const ACCOUNT_TYPE_LABEL = {
  checking: 'Checking',
  savings: 'Savings',
  credit: 'Credit',
  other: 'Other',
};

export default function Transactions() {
  const [searchParams] = useSearchParams();
  const categoryFromUrl = searchParams.get('category_id') || '';
  const [view, setView] = useState('list'); // 'list' | 'merchant' | 'category'
  const [transactions, setTransactions] = useState([]);
  const [merchantGroups, setMerchantGroups] = useState([]);
  const [categoryGroups, setCategoryGroups] = useState([]);
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    merchant: '',
    category_id: categoryFromUrl,
    account_id: '',
  });
  const [sortConfig, setSortConfig] = useState({ sortBy: 'date', sortOrder: 'desc' });
  const [merchantSort, setMerchantSort] = useState({ sortBy: 'total_spend', sortOrder: 'desc' });
  const [categorySort, setCategorySort] = useState({ sortBy: 'total_spend', sortOrder: 'desc' });
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [uploading, setUploading] = useState(false);
  const [uploadAccountId, setUploadAccountId] = useState('');
  const [uploadMessage, setUploadMessage] = useState(null);

  // Multi-select state (list view)
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState('');
  const [bulkAccountId, setBulkAccountId] = useState('');

  // Expanded merchant rows + per-merchant transactions cache
  const [expandedMerchants, setExpandedMerchants] = useState({});
  const [merchantTransactions, setMerchantTransactions] = useState({});

  // Expanded category rows + per-category transactions cache
  const [expandedCategories, setExpandedCategories] = useState({});
  const [categoryTransactions, setCategoryTransactions] = useState({});

  // Rule prompt modal
  const [rulePrompt, setRulePrompt] = useState(null); // { merchant, category_id, category_name }

  const categoriesById = useMemo(() => {
    const m = {};
    categories.forEach((c) => { m[c.id] = c; });
    return m;
  }, [categories]);

  const accountsById = useMemo(() => {
    const m = {};
    accounts.forEach((a) => { m[a.id] = a; });
    return m;
  }, [accounts]);

  useEffect(() => {
    fetchCategories();
    fetchAccounts();
  }, []);

  useEffect(() => {
    if (categoryFromUrl) {
      setFilters((f) => ({ ...f, category_id: categoryFromUrl }));
    }
  }, [categoryFromUrl]);

  useEffect(() => {
    if (view === 'list') {
      fetchTransactions();
    } else if (view === 'merchant') {
      fetchMerchantGroups();
    } else {
      fetchCategoryGroups();
    }
  }, [view, filters.category_id, filters.merchant, filters.account_id, sortConfig, merchantSort, categorySort]);

  const fetchTransactions = async () => {
    try {
      const response = await transactionsAPI.getAll({
        ...filters,
        sort_by: sortConfig.sortBy,
        sort_order: sortConfig.sortOrder,
        limit: 500,
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMerchantGroups = async () => {
    try {
      const response = await transactionsAPI.getMerchants({
        ...filters,
        sort_by: merchantSort.sortBy,
        sort_order: merchantSort.sortOrder,
      });
      setMerchantGroups(response.data);
    } catch (error) {
      console.error('Failed to fetch merchant groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategoryGroups = async () => {
    try {
      const response = await transactionsAPI.getCategoryGroups({
        ...filters,
        sort_by: categorySort.sortBy,
        sort_order: categorySort.sortOrder,
      });
      setCategoryGroups(response.data);
    } catch (error) {
      console.error('Failed to fetch category groups:', error);
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

  const fetchAccounts = async () => {
    try {
      const response = await accountsAPI.getAll();
      setAccounts(response.data);
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = '';

    setUploadMessage(null);
    setUploading(true);
    try {
      const { data } = await transactionsAPI.upload(file, uploadAccountId || null);
      setUploadMessage({
        type: 'success',
        text: data.message || `Imported ${data.count ?? 0} transactions.`,
      });
      fetchAccounts();
      if (view === 'list') fetchTransactions();
      else fetchMerchantGroups();
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
      account_id: transaction.account_id,
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

  const handleMerchantSort = (column) => {
    setMerchantSort((prev) => ({
      sortBy: column,
      sortOrder: prev.sortBy === column && prev.sortOrder === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleCategorySort = (column) => {
    setCategorySort((prev) => ({
      sortBy: column,
      sortOrder: prev.sortBy === column && prev.sortOrder === 'asc' ? 'desc' : 'asc',
    }));
  };

  const SortIcon = ({ column, active }) => {
    if (active.sortBy !== column) {
      return <ChevronUpIcon className="w-4 h-4 text-gray-400" />;
    }
    return active.sortOrder === 'asc' ? (
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

  const handleClearAll = async () => {
    if (!confirm('Delete ALL your transactions? Categories and accounts will be kept.')) return;
    try {
      const { data } = await transactionsAPI.clear();
      setUploadMessage({ type: 'success', text: data.message });
      if (view === 'list') fetchTransactions();
      else fetchMerchantGroups();
    } catch (error) {
      const detail = error.response?.data?.detail;
      const text = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg || 'Failed to clear.' : 'Failed to clear.';
      setUploadMessage({ type: 'error', text: typeof text === 'string' ? text : 'Failed to clear.' });
    }
  };

  // ---- Multi-select / bulk update -----------------------------------------
  const toggleSelected = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const togglePageSelected = () => {
    setSelectedIds((prev) => {
      const allSelected = transactions.every((t) => prev.has(t.id));
      if (allSelected) return new Set();
      const next = new Set(prev);
      transactions.forEach((t) => next.add(t.id));
      return next;
    });
  };

  const clearSelection = () => setSelectedIds(new Set());

  const applyBulk = async () => {
    if (!bulkCategoryId && !bulkAccountId) return;
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    try {
      const body = { ids };
      if (bulkCategoryId) body.category_id = parseInt(bulkCategoryId);
      if (bulkAccountId) body.account_id = parseInt(bulkAccountId);
      const { data } = await transactionsAPI.bulkUpdate(body);
      setUploadMessage({ type: 'success', text: `Updated ${data.updated} transaction(s).` });

      // If category was changed, and selected rows share the same merchant, offer to create a rule.
      if (bulkCategoryId) {
        const selectedRows = transactions.filter((t) => selectedIds.has(t.id));
        const merchants = new Set(selectedRows.map((t) => (t.merchant || '').trim().toLowerCase()));
        if (merchants.size === 1) {
          const sample = selectedRows[0].merchant;
          const cat = categoriesById[parseInt(bulkCategoryId)];
          setRulePrompt({
            merchant: sample,
            category_id: parseInt(bulkCategoryId),
            category_name: cat?.name || 'this category',
          });
        }
      }

      clearSelection();
      setBulkCategoryId('');
      setBulkAccountId('');
      fetchTransactions();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setUploadMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Bulk update failed.' });
    }
  };

  // ---- Merchant view actions ----------------------------------------------
  const toggleMerchantExpand = async (group) => {
    const key = group.normalized_key;
    setExpandedMerchants((prev) => ({ ...prev, [key]: !prev[key] }));
    if (!merchantTransactions[key]) {
      try {
        const response = await transactionsAPI.getAll({
          normalized_merchant: key,
          category_id: filters.category_id,
          account_id: filters.account_id,
          sort_by: 'date',
          sort_order: 'desc',
          limit: 500,
        });
        setMerchantTransactions((prev) => ({ ...prev, [key]: response.data }));
      } catch (error) {
        console.error('Failed to load merchant transactions:', error);
      }
    }
  };

  const toggleCategoryExpand = async (group) => {
    const key = group.category_id == null ? 'uncategorized' : String(group.category_id);
    setExpandedCategories((prev) => ({ ...prev, [key]: !prev[key] }));
    if (categoryTransactions[key]) return;
    try {
      const params = {
        sort_by: 'date',
        sort_order: 'desc',
        limit: 500,
        merchant: filters.merchant,
        account_id: filters.account_id,
      };
      // If this group is the "Uncategorized" bucket, we still hit the same endpoint
      // and filter to category_id=null client-side; the server has no nullable filter.
      if (group.category_id != null) {
        params.category_id = group.category_id;
      }
      const response = await transactionsAPI.getAll(params);
      let rows = response.data;
      if (group.category_id == null) {
        rows = rows.filter((t) => t.category_id == null);
      }
      setCategoryTransactions((prev) => ({ ...prev, [key]: rows }));
    } catch (error) {
      console.error('Failed to load category transactions:', error);
    }
  };

  const recategorizeMerchant = async (group) => {
    const target = prompt(`Recategorize ALL "${group.merchant}" transactions to which category?\n\n${categories.map((c) => `• ${c.name}`).join('\n')}\n\nType the category name:`);
    if (!target) return;
    const cat = categories.find((c) => c.name.toLowerCase() === target.trim().toLowerCase());
    if (!cat) {
      setUploadMessage({ type: 'error', text: `Category "${target}" not found.` });
      return;
    }
    try {
      const { data } = await transactionsAPI.bulkUpdateByMerchant({
        merchant: group.normalized_key,
        normalized: true,
        category_id: cat.id,
      });
      setUploadMessage({ type: 'success', text: `Updated ${data.updated} "${group.merchant}" transaction(s) → ${cat.name}.` });
      setRulePrompt({ merchant: group.merchant, category_id: cat.id, category_name: cat.name });
      setMerchantTransactions({});
      setExpandedMerchants({});
      fetchMerchantGroups();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setUploadMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Recategorize failed.' });
    }
  };

  // ---- Rule prompt --------------------------------------------------------
  const acceptRule = async () => {
    if (!rulePrompt) return;
    try {
      const keyword = (rulePrompt.merchant || '').trim().toLowerCase();
      await categoriesAPI.addRule({
        category_id: rulePrompt.category_id,
        keyword,
        priority: 10,
      });
      setUploadMessage({
        type: 'success',
        text: `Rule added: future "${rulePrompt.merchant}" transactions → ${rulePrompt.category_name}.`,
      });
    } catch (error) {
      setUploadMessage({ type: 'error', text: 'Failed to add rule.' });
    } finally {
      setRulePrompt(null);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading transactions...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Transactions</h1>
        <div className="flex gap-2 items-center">
          <select
            className="input"
            value={uploadAccountId}
            onChange={(e) => setUploadAccountId(e.target.value)}
            title="Upload into this account (or leave blank for auto-detect)"
          >
            <option value="">Upload to: auto-detect</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <button onClick={handleExport} className="btn btn-secondary">
            Export CSV
          </button>
          <button onClick={handleClearAll} className="btn btn-secondary text-red-600 hover:text-red-700 hover:bg-red-50">
            Clear all transactions
          </button>
          <label className={`btn btn-primary cursor-pointer ${uploading ? 'opacity-70 pointer-events-none' : ''}`}>
            <ArrowUpTrayIcon className="h-5 w-5 mr-2" />
            {uploading ? 'Uploading...' : 'Upload Statement'}
            <input type="file" className="hidden" accept=".csv,.pdf" onChange={handleFileUpload} disabled={uploading} />
          </label>
        </div>
      </div>
      <p className="text-sm text-gray-500">
        Upload CSV or PDF. Spend, savings, and credit-card statements are auto-tagged to an account. Override with the dropdown if needed.
      </p>

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
        {/* View toggle */}
        <div className="flex items-center gap-2 mb-4">
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium border rounded-l-md ${
                view === 'list'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => setView('list')}
            >
              List
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium border -ml-px ${
                view === 'merchant'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => setView('merchant')}
            >
              By Merchant
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium border rounded-r-md -ml-px ${
                view === 'category'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => setView('category')}
            >
              By Category
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          <select
            className="input"
            value={filters.account_id}
            onChange={(e) => setFilters({ ...filters, account_id: e.target.value })}
          >
            <option value="">All Accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>

        {/* Bulk action bar */}
        {view === 'list' && selectedIds.size > 0 && (
          <div className="sticky top-0 z-10 mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-blue-900">
              {selectedIds.size} selected
            </span>
            <select
              className="input"
              value={bulkCategoryId}
              onChange={(e) => setBulkCategoryId(e.target.value)}
            >
              <option value="">Change category to…</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
            <select
              className="input"
              value={bulkAccountId}
              onChange={(e) => setBulkAccountId(e.target.value)}
            >
              <option value="">Move to account…</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            <button
              onClick={applyBulk}
              disabled={!bulkCategoryId && !bulkAccountId}
              className="btn btn-primary"
            >
              Apply
            </button>
            <button onClick={clearSelection} className="btn btn-secondary">
              Clear selection
            </button>
          </div>
        )}

        {/* ----- LIST VIEW ----- */}
        {view === 'list' && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={transactions.length > 0 && transactions.every((t) => selectedIds.has(t.id))}
                      onChange={togglePageSelected}
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('date')}>
                    <div className="flex items-center gap-1">Date <SortIcon column="date" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('merchant')}>
                    <div className="flex items-center gap-1">Merchant <SortIcon column="merchant" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none min-w-[140px]" onClick={() => handleSort('description')}>
                    <div className="flex items-center gap-1">Description <SortIcon column="description" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('category')}>
                    <div className="flex items-center gap-1">Category <SortIcon column="category" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('account')}>
                    <div className="flex items-center gap-1">Account <SortIcon column="account" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('amount')}>
                    <div className="flex items-center gap-1">Amount <SortIcon column="amount" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort('type')}>
                    <div className="flex items-center gap-1">Type <SortIcon column="type" active={sortConfig} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {transactions.map((t) => (
                  <tr key={t.id} className={selectedIds.has(t.id) ? 'bg-blue-50' : ''}>
                    <td className="px-3 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(t.id)}
                        onChange={() => toggleSelected(t.id)}
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {format(new Date(t.date), 'MMM dd, yyyy')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {editingId === t.id ? (
                        <input type="text" className="input" value={editData.merchant} onChange={(e) => setEditData({ ...editData, merchant: e.target.value })} />
                      ) : t.merchant}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-[220px]" title={t.description || ''}>
                      {t.description || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {editingId === t.id ? (
                        <select className="input" value={editData.category_id || ''} onChange={(e) => setEditData({ ...editData, category_id: parseInt(e.target.value) })}>
                          {categories.map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
                        </select>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs" style={{
                          backgroundColor: (categoriesById[t.category_id]?.color || '#999') + '20',
                          color: categoriesById[t.category_id]?.color || '#666',
                        }}>
                          {categoriesById[t.category_id]?.name || 'Uncategorized'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {editingId === t.id ? (
                        <select className="input" value={editData.account_id || ''} onChange={(e) => setEditData({ ...editData, account_id: parseInt(e.target.value) })}>
                          <option value="">—</option>
                          {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                        </select>
                      ) : (
                        <span className="text-xs text-gray-700">{accountsById[t.account_id]?.name || '—'}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {editingId === t.id ? (
                        <input type="number" step="0.01" className="input" value={editData.amount} onChange={(e) => setEditData({ ...editData, amount: parseFloat(e.target.value) })} />
                      ) : `$${Number(t.amount).toFixed(2)}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs ${t.transaction_type === 'credit' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {t.transaction_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {editingId === t.id ? (
                        <>
                          <button onClick={() => handleSave(t.id)} className="text-green-600 hover:text-green-900 mr-3">Save</button>
                          <button onClick={() => setEditingId(null)} className="text-gray-600 hover:text-gray-900">Cancel</button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => handleEdit(t)} className="text-primary-600 hover:text-primary-900 mr-3"><PencilIcon className="h-5 w-5" /></button>
                          <button onClick={() => handleDelete(t.id)} className="text-red-600 hover:text-red-900"><TrashIcon className="h-5 w-5" /></button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {transactions.length === 0 && (
              <p className="py-8 text-center text-sm text-gray-500">No transactions match your filters.</p>
            )}
          </div>
        )}

        {/* ----- MERCHANT VIEW ----- */}
        {view === 'merchant' && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 w-10"></th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('merchant')}>
                    <div className="flex items-center gap-1">Merchant <SortIcon column="merchant" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('count')}>
                    <div className="flex items-center justify-end gap-1">Count <SortIcon column="count" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('total_spend')}>
                    <div className="flex items-center justify-end gap-1">Total Spend <SortIcon column="total_spend" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('total_income')}>
                    <div className="flex items-center justify-end gap-1">Total Income <SortIcon column="total_income" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('first_date')}>
                    <div className="flex items-center gap-1">First <SortIcon column="first_date" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleMerchantSort('last_date')}>
                    <div className="flex items-center gap-1">Last <SortIcon column="last_date" active={merchantSort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categories</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {merchantGroups.map((g) => {
                  const isOpen = !!expandedMerchants[g.normalized_key];
                  return (
                    <Fragment key={g.normalized_key}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-3 py-4">
                          <button onClick={() => toggleMerchantExpand(g)} className="text-gray-500">
                            {isOpen ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
                          </button>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <div className="font-medium text-gray-900">{g.merchant}</div>
                          {g.variants && g.variants.length > 0 && (
                            <div
                              className="text-xs text-gray-500 mt-0.5 truncate max-w-[360px]"
                              title={g.variants.join('\n')}
                            >
                              also: {g.variants.slice(0, 2).join(' · ')}
                              {g.variants.length > 2 && ` · +${g.variants.length - 2} more`}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">{g.count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-700">${g.total_debit.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-700">${g.total_credit.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{format(new Date(g.first_date), 'MMM dd, yyyy')}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{format(new Date(g.last_date), 'MMM dd, yyyy')}</td>
                        <td className="px-6 py-4 text-sm">
                          <div className="flex flex-wrap gap-1">
                            {g.category_ids.length === 0 && <span className="text-gray-400 text-xs">—</span>}
                            {g.category_ids.map((cid) => (
                              <span key={cid} className="px-2 py-1 rounded-full text-xs" style={{
                                backgroundColor: (categoriesById[cid]?.color || '#999') + '20',
                                color: categoriesById[cid]?.color || '#666',
                              }}>
                                {categoriesById[cid]?.name || `#${cid}`}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                          <button onClick={() => recategorizeMerchant(g)} className="btn btn-secondary text-xs">
                            Recategorize all
                          </button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={9} className="bg-gray-50 px-6 py-4">
                            <div className="space-y-1">
                              {(merchantTransactions[g.normalized_key] || []).map((t) => (
                                <div key={t.id} className="flex items-center justify-between text-sm">
                                  <span className="text-gray-600">{format(new Date(t.date), 'MMM dd, yyyy')}</span>
                                  <span className="text-gray-800 flex-1 mx-3 truncate" title={t.merchant}>{t.merchant}</span>
                                  <span className="text-gray-500 flex-1 mr-3 truncate text-xs">{t.description || ''}</span>
                                  <span className="text-xs text-gray-500 mr-3">{accountsById[t.account_id]?.name || '—'}</span>
                                  <span className="px-2 py-0.5 rounded-full text-xs mr-3" style={{
                                    backgroundColor: (categoriesById[t.category_id]?.color || '#999') + '20',
                                    color: categoriesById[t.category_id]?.color || '#666',
                                  }}>
                                    {categoriesById[t.category_id]?.name || 'Uncategorized'}
                                  </span>
                                  <span className={t.transaction_type === 'credit' ? 'text-green-700' : 'text-red-700'}>
                                    ${Number(t.amount).toFixed(2)}
                                  </span>
                                </div>
                              ))}
                              {(merchantTransactions[g.normalized_key] || []).length === 0 && (
                                <p className="text-xs text-gray-500">Loading…</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
            {merchantGroups.length === 0 && (
              <p className="py-8 text-center text-sm text-gray-500">No merchants match your filters.</p>
            )}
          </div>
        )}

        {/* ----- CATEGORY VIEW ----- */}
        {view === 'category' && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 w-10"></th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('category')}>
                    <div className="flex items-center gap-1">Category <SortIcon column="category" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('count')}>
                    <div className="flex items-center justify-end gap-1">Count <SortIcon column="count" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('total_spend')}>
                    <div className="flex items-center justify-end gap-1">Total Spend <SortIcon column="total_spend" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('total_income')}>
                    <div className="flex items-center justify-end gap-1">Total Income <SortIcon column="total_income" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('first_date')}>
                    <div className="flex items-center gap-1">First <SortIcon column="first_date" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleCategorySort('last_date')}>
                    <div className="flex items-center gap-1">Last <SortIcon column="last_date" active={categorySort} /></div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Top merchants</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {categoryGroups.map((g) => {
                  const expandKey = g.category_id == null ? 'uncategorized' : String(g.category_id);
                  const isOpen = !!expandedCategories[expandKey];
                  const catColor = g.category_id != null ? categoriesById[g.category_id]?.color : '#9CA3AF';
                  return (
                    <Fragment key={expandKey}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-3 py-4">
                          <button onClick={() => toggleCategoryExpand(g)} className="text-gray-500">
                            {isOpen ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
                          </button>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className="px-2 py-1 rounded-full text-xs font-medium" style={{
                            backgroundColor: (catColor || '#999') + '20',
                            color: catColor || '#666',
                          }}>
                            {g.category_name}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">{g.count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-700">${g.total_debit.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-700">${g.total_credit.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{format(new Date(g.first_date), 'MMM dd, yyyy')}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{format(new Date(g.last_date), 'MMM dd, yyyy')}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">
                          <span className="truncate inline-block max-w-[280px]" title={g.top_merchants.join(', ')}>
                            {g.top_merchants.length ? g.top_merchants.join(', ') : '—'}
                          </span>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={8} className="bg-gray-50 px-6 py-4">
                            <div className="space-y-1">
                              {(categoryTransactions[expandKey] || []).map((t) => (
                                <div key={t.id} className="flex items-center justify-between text-sm">
                                  <span className="text-gray-600">{format(new Date(t.date), 'MMM dd, yyyy')}</span>
                                  <span className="text-gray-900 flex-1 mx-4 truncate">{t.merchant}</span>
                                  <span className="text-gray-700 flex-1 mr-4 truncate">{t.description || ''}</span>
                                  <span className="text-xs text-gray-500 mr-3">{accountsById[t.account_id]?.name || '—'}</span>
                                  <span className={t.transaction_type === 'credit' ? 'text-green-700' : 'text-red-700'}>
                                    ${Number(t.amount).toFixed(2)}
                                  </span>
                                </div>
                              ))}
                              {(categoryTransactions[expandKey] || []).length === 0 && (
                                <p className="text-xs text-gray-500">Loading…</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
            {categoryGroups.length === 0 && (
              <p className="py-8 text-center text-sm text-gray-500">No categories match your filters.</p>
            )}
          </div>
        )}
      </div>

      {/* Rule prompt modal */}
      {rulePrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Create rule?</h3>
            <p className="text-sm text-gray-700 mb-4">
              Also categorize future transactions matching <strong>"{rulePrompt.merchant}"</strong> as <strong>{rulePrompt.category_name}</strong>?
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setRulePrompt(null)} className="btn btn-secondary">No, just these</button>
              <button onClick={acceptRule} className="btn btn-primary">Yes, create rule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
