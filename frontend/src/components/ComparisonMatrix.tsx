"use client"

export default function ComparisonMatrix({ candidates, target, onSelect }: { candidates: any[], target: any, onSelect: (sku: string) => void }) {
  if (!candidates || candidates.length === 0) {
    return <div className="card">No viable candidates found.</div>;
  }

  const renderDelta = (candidateValue: any, targetValue: any, type: string) => {
    if (!targetValue) return <span>{candidateValue}</span>;
    let color = 'var(--text-muted)';
    if (candidateValue === targetValue) color = 'var(--success)';
    else color = 'var(--warning)';
    return <span style={{ color }}>{candidateValue}</span>;
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: `200px repeat(${candidates.length}, 1fr)`, gap: '1rem', overflowX: 'auto' }}>
      {/* Labels Column */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingTop: '100px' }}>
        <div style={{ height: '50px', fontWeight: 600 }}>Score</div>
        <div style={{ height: '30px' }}>Brand / Family</div>
        <div style={{ height: '30px' }}>Lumens</div>
        <div style={{ height: '30px' }}>CCT</div>
        <div style={{ height: '30px' }}>Tier</div>
        <div style={{ height: '30px' }}>Margin</div>
        <div style={{ height: '30px' }}>Risk Flags</div>
        <div style={{ height: '50px' }}></div>
      </div>

      {/* Candidate Columns */}
      {candidates.map((c, idx) => (
        <div key={idx} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative', overflow: 'hidden' }}>
          {idx === 0 && <div style={{ position: 'absolute', top: 0, right: 0, background: 'var(--primary)', color: 'white', padding: '0.2rem 1rem', fontSize: '0.7rem', fontWeight: 700, borderBottomLeftRadius: '8px' }}>BEST MATCH</div>}
          
          <h3 style={{ fontSize: '1rem', wordBreak: 'break-all', height: '60px' }}>{c.sku}</h3>
          
          <div style={{ display: 'flex', justifyContent: 'center', height: '50px' }}>
            <div className={`score-circle ${c.final_score > 80 ? 'score-high' : c.final_score > 50 ? 'score-med' : 'score-low'}`}>
              {Math.round(c.final_score)}
            </div>
          </div>
          
          <div style={{ height: '30px', fontSize: '0.9rem' }}>{c.brand}</div>
          <div style={{ height: '30px', fontSize: '0.9rem' }}>{renderDelta(c.lumens, target?.photometric?.lumens_min, 'lumens')} lm</div>
          <div style={{ height: '30px', fontSize: '0.9rem' }}>{renderDelta(c.cct, target?.photometric?.cct, 'cct')} K</div>
          <div style={{ height: '30px', fontSize: '0.9rem' }}>Tier {c.tier}</div>
          <div style={{ height: '30px', fontSize: '0.9rem', color: 'var(--success)' }}>{(c.margin * 100).toFixed(1)}%</div>
          
          <div style={{ height: '30px', fontSize: '0.8rem' }}>
            {c.risk_flags?.length > 0 ? (
              <span className="badge badge-warning">⚠ {c.risk_flags.length} flags</span>
            ) : (
              <span className="badge badge-success">✓ Clear</span>
            )}
          </div>
          
          <div style={{ height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <button className="btn" style={{ width: '100%' }} onClick={() => onSelect(c.sku)}>Select</button>
          </div>
        </div>
      ))}
    </div>
  );
}
