import { useState, useEffect } from 'react';
import { accountsAPI } from '../services/api';
import { PencilIcon, TrashIcon, PlusIcon } from '@heroicons/react/24/outline';

const ACCOUNT_TYPES = [
  { value: 'checking', label: 'Checking' },
  { value: 'savings', label: 'Savings' },
  { value: 'credit', label: 'Credit' },
  { value: 'other', label: 'Other' },
];

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newAccount, setNewAccount] = useState({
    name: '',
    account_type: 'other',
    institution: '',
  });
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [deleteState, setDeleteState] = useState(null); // { account, reassign_to }

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const { data } = await accountsAPI.getAll();
      setAccounts(data);
    } catch (error) {
      console.error('Failed to load accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newAccount.name.trim()) return;
    try {
      await accountsAPI.create({
        name: newAccount.name.trim(),
        account_type: newAccount.account_type,
        institution: newAccount.institution.trim() || null,
      });
      setMessage({ type: 'success', text: `Account "${newAccount.name}" created.` });
      setNewAccount({ name: '', account_type: 'other', institution: '' });
      setShowCreate(false);
      fetchAccounts();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to create account.' });
    }
  };

  const startEdit = (account) => {
    setEditingId(account.id);
    setEditData({
      name: account.name,
      account_type: account.account_type,
      institution: account.institution || '',
    });
  };

  const saveEdit = async (id) => {
    try {
      await accountsAPI.update(id, {
        name: editData.name.trim(),
        account_type: editData.account_type,
        institution: editData.institution.trim() || null,
      });
      setEditingId(null);
      setMessage({ type: 'success', text: 'Account updated.' });
      fetchAccounts();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to update account.' });
    }
  };

  const startDelete = (account) => {
    setDeleteState({ account, reassign_to: '' });
  };

  const confirmDelete = async () => {
    if (!deleteState) return;
    const { account, reassign_to } = deleteState;
    try {
      const { data } = await accountsAPI.delete(account.id, reassign_to || null);
      setMessage({
        type: 'success',
        text: `"${account.name}" deleted. ${data.reassigned_transactions ? `Moved ${data.reassigned_transactions} transaction(s).` : ''}`,
      });
      setDeleteState(null);
      fetchAccounts();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setMessage({ type: 'error', text: typeof detail === 'string' ? detail : 'Failed to delete account.' });
    }
  };

  if (loading) return <div className="text-center py-8">Loading accounts...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Accounts</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="btn btn-primary">
          <PlusIcon className="h-5 w-5 mr-1" />
          Add Account
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {message.text}
        </div>
      )}

      {showCreate && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">New account</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Name (e.g. PNC Checking)"
              className="input"
              value={newAccount.name}
              onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
            />
            <select
              className="input"
              value={newAccount.account_type}
              onChange={(e) => setNewAccount({ ...newAccount, account_type: e.target.value })}
            >
              {ACCOUNT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input
              type="text"
              placeholder="Institution (optional)"
              className="input"
              value={newAccount.institution}
              onChange={(e) => setNewAccount({ ...newAccount, institution: e.target.value })}
            />
          </div>
          <div className="mt-3 flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="btn btn-secondary">Cancel</button>
            <button onClick={handleCreate} className="btn btn-primary">Create</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Institution</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Transactions</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {editingId === a.id ? (
                      <input className="input" value={editData.name} onChange={(e) => setEditData({ ...editData, name: e.target.value })} />
                    ) : (
                      <span className="font-medium">
                        {a.name}
                        {a.is_default && <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">default</span>}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {editingId === a.id ? (
                      <select className="input" value={editData.account_type} onChange={(e) => setEditData({ ...editData, account_type: e.target.value })}>
                        {ACCOUNT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                      </select>
                    ) : (
                      ACCOUNT_TYPES.find((t) => t.value === a.account_type)?.label || a.account_type
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {editingId === a.id ? (
                      <input className="input" value={editData.institution} onChange={(e) => setEditData({ ...editData, institution: e.target.value })} />
                    ) : (
                      a.institution || '—'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-700">{a.transaction_count}</td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right ${a.balance < 0 ? 'text-red-700' : 'text-green-700'}`}>
                    ${Number(a.balance).toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    {editingId === a.id ? (
                      <>
                        <button onClick={() => saveEdit(a.id)} className="text-green-600 hover:text-green-900 mr-3">Save</button>
                        <button onClick={() => setEditingId(null)} className="text-gray-600 hover:text-gray-900">Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEdit(a)} className="text-primary-600 hover:text-primary-900 mr-3"><PencilIcon className="h-5 w-5" /></button>
                        <button onClick={() => startDelete(a)} className="text-red-600 hover:text-red-900"><TrashIcon className="h-5 w-5" /></button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {accounts.length === 0 && (
            <p className="py-8 text-center text-sm text-gray-500">No accounts yet — upload a statement or click "Add Account".</p>
          )}
        </div>
      </div>

      {/* Delete modal */}
      {deleteState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete "{deleteState.account.name}"?</h3>
            {deleteState.account.transaction_count > 0 ? (
              <>
                <p className="text-sm text-gray-700 mb-4">
                  This account has <strong>{deleteState.account.transaction_count}</strong> transaction(s). Pick another account to move them into:
                </p>
                <select
                  className="input mb-4"
                  value={deleteState.reassign_to}
                  onChange={(e) => setDeleteState({ ...deleteState, reassign_to: e.target.value })}
                >
                  <option value="">Select account…</option>
                  {accounts
                    .filter((a) => a.id !== deleteState.account.id)
                    .map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </>
            ) : (
              <p className="text-sm text-gray-700 mb-4">No transactions to move. This will be permanent.</p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteState(null)} className="btn btn-secondary">Cancel</button>
              <button
                onClick={confirmDelete}
                disabled={deleteState.account.transaction_count > 0 && !deleteState.reassign_to}
                className="btn btn-primary bg-red-600 hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
