"use client"
import { useState } from 'react';

export default function MarginSimulator({ initialMargin, cost }: { initialMargin: number, cost: number }) {
  const [sellPrice, setSellPrice] = useState(cost / (1 - initialMargin));
  const [discount, setDiscount] = useState(0);

  const currentMargin = (sellPrice * (1 - discount / 100) - cost) / (sellPrice * (1 - discount / 100));

  return (
    <div className="card" style={{ marginTop: '2rem' }}>
      <h3 style={{ marginBottom: '1.5rem' }}>Margin Simulator</h3>
      
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Sell Price ($)</label>
          <input 
            type="number" 
            value={sellPrice.toFixed(2)} 
            onChange={(e) => setSellPrice(Number(e.target.value))}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-dark)', color: 'white' }}
          />
        </div>
        
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Customer Discount (%)</label>
          <input 
            type="range" 
            min="0" 
            max="50" 
            value={discount} 
            onChange={(e) => setDiscount(Number(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>{discount}%</div>
        </div>
        
        <div style={{ flex: 1, textAlign: 'right' }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Effective Margin</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: currentMargin > 0.2 ? 'var(--success)' : 'var(--warning)' }}>
            {(currentMargin * 100).toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  );
}
