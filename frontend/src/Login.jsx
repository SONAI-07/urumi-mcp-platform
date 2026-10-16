import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from './api';
import { Lock } from 'lucide-react';

export default function Login() {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      // Test the key by fetching servers
      await api.get('/admin/servers', { headers: { Authorization: `Bearer ${key}` } });
      localStorage.setItem('urumi_api_key', key);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid or revoked API Key');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleLogin} className="bg-slate-800 p-8 rounded-xl shadow-2xl w-96 border border-slate-700">
        <div className="flex justify-center mb-4"><Lock size={40} className="text-blue-400" /></div>
        <h2 className="text-2xl font-bold text-center mb-6">Urumi Gateway Admin</h2>

        <input
          type="password"
          placeholder="Paste Admin API Key"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="w-full p-3 rounded bg-slate-900 border border-slate-600 focus:border-blue-500 outline-none mb-4"
        />

        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

        <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded transition">
          Authenticate
        </button>
      </form>
    </div>
  );
}