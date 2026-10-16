import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from './api';
import { Server, Activity, LogOut, Power } from 'lucide-react';

export default function Dashboard() {
  const [servers, setServers] = useState([]);
  const [logs, setLogs] = useState([]);
  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      const sRes = await api.get('/admin/servers');
      const lRes = await api.get('/admin/audit-logs');
      setServers(sRes.data);
      setLogs(lRes.data);
    } catch (err) {
      if (err.response && err.response.status === 401) {
        localStorage.removeItem('urumi_api_key');
        navigate('/');
      }
    }
  };

  const toggleServer = async (id) => {
    await api.patch(`/admin/servers/${id}/toggle`);
    fetchData();
  };

  const handleLogout = () => {
    localStorage.removeItem('urumi_api_key');
    navigate('/');
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-2"><Server /> Urumi Gateway Control</h1>
        <button onClick={handleLogout} className="text-slate-400 hover:text-red-400 flex items-center gap-1"><LogOut size={18}/> Logout</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Servers Panel */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2"><Power size={20}/> Registered MCP Servers</h2>
          {servers.length === 0 && <p className="text-slate-400">No servers registered.</p>}
          <ul className="space-y-3">
            {servers.map(s => (
              <li key={s.id} className="flex justify-between items-center bg-slate-900 p-4 rounded-lg">
                <div>
                  <p className="font-mono font-bold">{s.name}</p>
                  <p className="text-xs text-slate-400">{s.url}</p>
                </div>
                <button
                  onClick={() => toggleServer(s.id)}
                  className={`px-3 py-1 rounded text-xs font-bold ${s.is_enabled ? 'bg-green-600' : 'bg-red-600'}`}
                >
                  {s.is_enabled ? 'ENABLED' : 'DISABLED'}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Audit Log Panel */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2"><Activity size={20}/> Audit Log</h2>
          <div className="max-h-96 overflow-y-auto space-y-2 pr-2">
            {logs.length === 0 && <p className="text-slate-400">No activity yet.</p>}
            {logs.map(l => (
              <div key={l.id} className="bg-slate-900 p-3 rounded text-sm font-mono border-l-4 border-blue-500">
                <div className="flex justify-between">
                  <span className="font-bold text-blue-300">{l.tool_name}</span>
                  <span className={l.success ? 'text-green-400' : 'text-red-400'}>
                    {l.success ? `${l.duration_ms}ms` : 'FAIL'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{l.server_name} • {new Date(l.timestamp).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}