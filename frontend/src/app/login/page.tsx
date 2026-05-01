"use client";

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:10000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      
      // Save JWT token locally
      localStorage.setItem('inawo_token', data.access_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', backgroundColor: 'var(--bg-primary)' }}>
      <div style={{ flex: 1, backgroundColor: 'var(--bg-secondary)', padding: '64px', display: 'flex', flexDirection: 'column', justifyContent: 'center', borderRight: '1px solid var(--border-color)' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '24px' }}>Welcome back to Inawo AI.</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '18px', maxWidth: '400px' }}>
          Access your dashboard, manage your AI agent, and view live customer interactions.
        </p>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '64px' }}>
        <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', padding: '40px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '32px', textAlign: 'center' }}>Log In</h2>
          
          {error && <div style={{ color: '#ef4444', marginBottom: '16px', fontSize: '14px', textAlign: 'center' }}>{error}</div>}
          
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Business Email</label>
              <input required type="email" placeholder="name@company.com" 
                value={email} onChange={e => setEmail(e.target.value)}
                style={{ width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none' }} />
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', fontWeight: 500 }}>Password</label>
              <input required type="password" placeholder="••••••••" 
                value={password} onChange={e => setPassword(e.target.value)}
                style={{ width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none' }} />
            </div>

            <button type="submit" disabled={loading} className="button-primary" style={{ width: '100%', marginTop: '12px' }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: 'var(--text-secondary)' }}>
            Don't have an account? <Link href="/signup" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>Create Business Profile</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
