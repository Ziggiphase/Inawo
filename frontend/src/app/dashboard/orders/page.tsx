"use client";

import { useEffect, useState } from 'react';

interface Order {
  id: number;
  customer_phone: string;
  items: any;
  total_amount: number;
  status: string;
  created_at: string;
}

interface Chat {
  id: number;
  customer_phone: string;
  is_ai_paused: boolean;
}

export default function OrdersAndChats() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('inawo_token');
      if (!token) return;

      try {
        const [ordersRes, chatsRes] = await Promise.all([
          fetch('http://localhost:10000/api/analytics/orders', { headers: { 'Authorization': `Bearer ${token}` } }),
          fetch('http://localhost:10000/api/analytics/chats', { headers: { 'Authorization': `Bearer ${token}` } })
        ]);

        if (ordersRes.ok) setOrders(await ordersRes.json());
        if (chatsRes.ok) setChats(await chatsRes.json());
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading) return <div>Loading...</div>;

  return (
    <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '32px' }}>Operations Control Center</h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}>
        
        {/* Left: Orders Table */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Recent Orders</h2>
          {orders.length === 0 ? <p style={{ color: 'var(--text-secondary)' }}>No orders yet.</p> : (
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '13px' }}>
                  <th style={{ padding: '12px 8px' }}>Customer</th>
                  <th style={{ padding: '12px 8px' }}>Amount</th>
                  <th style={{ padding: '12px 8px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '12px 8px', fontSize: '14px' }}>{o.customer_phone}</td>
                    <td style={{ padding: '12px 8px', fontSize: '14px', fontWeight: 500 }}>₦{o.total_amount}</td>
                    <td style={{ padding: '12px 8px' }}>
                      <span style={{ 
                        padding: '4px 8px', borderRadius: '4px', fontSize: '12px',
                        backgroundColor: o.status === 'paid' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                        color: o.status === 'paid' ? '#10b981' : '#f59e0b'
                      }}>
                        {o.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Right: Live WhatsApp Chats */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Live WhatsApp Sessions</h2>
          {chats.length === 0 ? <p style={{ color: 'var(--text-secondary)' }}>No active chats.</p> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {chats.map(c => (
                <div key={c.id} style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <p style={{ fontWeight: 500, fontSize: '15px' }}>{c.customer_phone}</p>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Status: {c.is_ai_paused ? 'Human Handling' : 'AI Autopilot'}</p>
                  </div>
                  <button className="button-secondary" style={{ padding: '6px 12px', fontSize: '13px' }}>
                    View Chat
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
