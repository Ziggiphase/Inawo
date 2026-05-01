"use client";

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Signup() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    business_name: '', category: 'General', email: '', phone_number: '', password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:10000/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const data = await res.json();
      if (!res.ok) {
        // FastAPI 422 errors return detail as an array of objects
        const errorMsg = typeof data.detail === 'string' 
          ? data.detail 
          : JSON.stringify(data.detail);
        throw new Error(errorMsg);
      }
      
      // Auto-login or redirect
      router.push('/login');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', backgroundColor: 'var(--bg-primary)' }}>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '64px' }}>
        <div className="glass-panel" style={{ width: '100%', maxWidth: '500px', padding: '40px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '8px', textAlign: 'center' }}>Create Business Profile</h2>
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '14px' }}>
            Set up your 24/7 AI agent in minutes.
          </p>
          
          {error && <div style={{ color: '#ef4444', marginBottom: '16px', fontSize: '14px', textAlign: 'center' }}>{error}</div>}
          
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Business Name</label>
                <input required type="text" placeholder="Aura Fashion" style={inputStyles} 
                  value={formData.business_name} onChange={e => setFormData({...formData, business_name: e.target.value})} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Category</label>
                <select style={inputStyles} value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})}>
                  <option>Fashion & Tailoring</option>
                  <option>Food & Catering</option>
                  <option>Real Estate & Events</option>
                  <option>General</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Email Address</label>
              <input required type="email" placeholder="contact@business.com" style={inputStyles} 
                value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Phone Number (WhatsApp)</label>
                <input required type="tel" placeholder="+234..." style={inputStyles} 
                  value={formData.phone_number} onChange={e => setFormData({...formData, phone_number: e.target.value})} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Password</label>
                <input required type="password" placeholder="••••••••" style={inputStyles} 
                  value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
              </div>
            </div>

            <button type="submit" disabled={loading} className="button-primary" style={{ width: '100%', marginTop: '12px' }}>
              {loading ? 'Creating...' : 'Create Account'}
            </button>
          </form>

          <p style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: 'var(--text-secondary)' }}>
            Already have an account? <Link href="/login" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Log In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

const inputStyles = {
  width: '100%',
  padding: '12px 16px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--border-color)',
  backgroundColor: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  outline: 'none'
};
