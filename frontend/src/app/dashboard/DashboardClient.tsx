"use client";

import { useEffect, useState } from 'react';

// Define the shape of our API response
interface AnalyticsData {
  ai_performance: {
    total_conversations: number;
    handoff_rate: string;
    active_chats: number;
  };
  sales: {
    total_revenue: number;
    conversion_rate: string;
    orders_processed: number;
  };
  reputation: {
    average_rating: number;
  };
  product_insights: Array<{ name: string; inquiries: number }>;
  is_ai_active: boolean;
}

export default function DashboardClient() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('inawo_token');
      if (!token) {
         window.location.href = '/login';
         return;
      }
      
      const res = await fetch('http://localhost:10000/api/analytics/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Failed to fetch analytics');
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message);
      
      // MOCK DATA FOR DEMONSTRATION PURPOSES (If backend is offline)
      setData({
        ai_performance: { total_conversations: 1240, handoff_rate: "2.1%", active_chats: 45 },
        sales: { total_revenue: 1540000, conversion_rate: "68.4%", orders_processed: 848 },
        reputation: { average_rating: 4.9 },
        product_insights: [
          { name: "Wedding Catering Package", inquiries: 432 },
          { name: "Corporate Event Setup", inquiries: 210 },
          { name: "Custom Branded Merch", inquiries: 156 }
        ],
        is_ai_active: true
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const toggleAiSwitch = async () => {
    if (!data) return;
    
    // Optimistic UI update
    const newStatus = !data.is_ai_active;
    setData({ ...data, is_ai_active: newStatus });

    try {
      await fetch(`http://localhost:10000/api/analytics/toggle-ai?active=${newStatus}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${MOCK_TOKEN}` }
      });
    } catch (err) {
      console.error("Failed to toggle AI switch", err);
      // Revert if failed
      setData({ ...data, is_ai_active: !newStatus });
    }
  };

  if (isLoading) return <div>Loading dashboard data...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Master Kill Switch */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '18px', marginBottom: '4px' }}>AI Autopilot Status</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Turn this off to pause the AI globally and manually reply to customers on WhatsApp.
          </p>
        </div>
        <button 
          onClick={toggleAiSwitch}
          style={{
            padding: '12px 24px',
            borderRadius: 'var(--radius-full)',
            fontWeight: 600,
            transition: 'all var(--transition-fast)',
            backgroundColor: data?.is_ai_active ? '#10b981' : '#ef4444',
            color: '#ffffff'
          }}
        >
          {data?.is_ai_active ? 'Autopilot: ON' : 'Autopilot: OFF (Handoff Mode)'}
        </button>
      </div>

      {/* 2. Top Level Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Sales Conversion Rate</p>
          <p style={{ fontSize: '36px', fontWeight: 500, letterSpacing: '-0.04em' }}>{data?.sales.conversion_rate}</p>
        </div>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Human Handoff Rate</p>
          <p style={{ fontSize: '36px', fontWeight: 500, letterSpacing: '-0.04em' }}>{data?.ai_performance.handoff_rate}</p>
        </div>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Avg. Customer Rating</p>
          <p style={{ fontSize: '36px', fontWeight: 500, letterSpacing: '-0.04em' }}>{data?.reputation.average_rating}</p>
        </div>
      </div>

      {/* 3. Lower Section: Product Insights */}
      <div className="glass-panel" style={{ padding: '24px', marginTop: '12px' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>Top Customer Inquiries</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {data?.product_insights.map((item, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontWeight: 500 }}>{item.name}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{item.inquiries} requests</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
