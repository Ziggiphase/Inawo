"use client";

import { useState } from 'react';

export default function SettingsPage() {
  const [formData, setFormData] = useState({
    knowledge_base_text: '',
    brand_color: '#111111'
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // In a full implementation, this POSTs to the backend to update models.Business
    alert('Settings updated successfully!');
  };

  return (
    <div style={{ padding: '48px', maxWidth: '800px' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>Store Settings</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>Configure how your brand appears to customers and give your AI custom instructions.</p>

      <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Brand Color</label>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <input type="color" value={formData.brand_color} onChange={(e) => setFormData({...formData, brand_color: e.target.value})} style={{ width: '50px', height: '50px', padding: '0', border: 'none', borderRadius: '8px', cursor: 'pointer' }} />
            <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Used on your public storefront banner.</span>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>AI Knowledge Base & Tone</label>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Tell your AI how to speak to customers (e.g. "Be very polite, we don't do refunds, delivery takes 2 days").
          </p>
          <textarea 
            value={formData.knowledge_base_text}
            onChange={(e) => setFormData({...formData, knowledge_base_text: e.target.value})}
            style={{ width: '100%', height: '150px', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none', resize: 'vertical' }}
            placeholder="We are a premium fashion brand based in Lagos. We accept returns within 3 days..."
          />
        </div>

        <button type="submit" className="button-primary" style={{ alignSelf: 'flex-start', padding: '12px 24px' }}>
          Save Changes
        </button>
      </form>
    </div>
  );
}
