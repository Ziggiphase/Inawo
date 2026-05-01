"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '../../components/Navbar';

interface Business {
  id: number;
  name: string;
  category: string;
  rating: number;
  brand_color: string;
}

export default function ExploreMarketplace() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:10000/api/public/businesses')
      .then(res => res.json())
      .then(data => {
        setBusinesses(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
      <Navbar />
      
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '64px 24px' }}>
        <div style={{ textAlign: 'center', marginBottom: '64px' }}>
          <h1 style={{ fontSize: '48px', fontWeight: 600, marginBottom: '16px' }}>Discover AI-Powered Brands</h1>
          <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
            Browse and interact with next-generation businesses powered by Inawo's 24/7 AI Agents.
          </p>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center' }}>Loading directory...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '32px' }}>
            {businesses.map(b => (
              <Link href={`/b/${b.id}`} key={b.id} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="glass-panel" style={{ overflow: 'hidden', transition: 'transform 0.2s', cursor: 'pointer' }} 
                     onMouseOver={e => e.currentTarget.style.transform = 'translateY(-4px)'}
                     onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
                  <div style={{ height: '120px', backgroundColor: b.brand_color }}></div>
                  <div style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <h3 style={{ fontSize: '20px', fontWeight: 600 }}>{b.name}</h3>
                      <span style={{ fontSize: '14px', color: '#f59e0b', fontWeight: 500 }}>★ {b.rating.toFixed(1)}</span>
                    </div>
                    <span style={{ display: 'inline-block', padding: '4px 12px', background: 'var(--bg-secondary)', borderRadius: '100px', fontSize: '12px' }}>
                      {b.category}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
