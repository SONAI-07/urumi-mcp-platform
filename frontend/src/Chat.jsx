import { useState } from 'react';
import api from './api';
import { Bot, Send } from 'lucide-react';

export default function Chat() {
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  const send = async (e) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    const userMsg = input.trim();
    setInput('');
    setHistory(h => [...h, { role: 'user', content: userMsg }]);
    setBusy(true);
    try {
      const res = await api.post('/agent/chat', { message: userMsg, history });
      setHistory(res.data.history);
    } catch (err) {
      setHistory(h => [...h, { role: 'assistant',
        content: '⚠️ Agent error: ' + (err.response?.data?.detail || err.message) }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="container mx-auto p-8 max-w-3xl flex flex-col h-screen">
      <h1 className="text-2xl font-bold mb-4 flex items-center gap-2"><Bot /> Urumi Store Agent</h1>
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 bg-slate-800 rounded-xl p-4 border border-slate-700">
        {history.length === 0 && (
          <p className="text-slate-400 text-sm">
            Try: “What products do we have?” · “Create a product called Urumi Mug for 499” · “Show the latest orders”
          </p>
        )}
        {history.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-lg text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-blue-600' : 'bg-slate-700'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {busy && <p className="text-slate-400 text-sm animate-pulse">Agent is reasoning & calling tools…</p>}
      </div>
      <form onSubmit={send} className="flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask the store agent…"
          className="flex-1 p-3 rounded bg-slate-900 border border-slate-600 focus:border-blue-500 outline-none" />
        <button type="submit" disabled={busy} className="bg-blue-600 hover:bg-blue-500 px-4 rounded disabled:opacity-50">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}