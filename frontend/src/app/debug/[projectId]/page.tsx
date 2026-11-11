'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';

export default function DebugPage() {
  const { projectId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/debug/project/${projectId}/extraction`)
      .then(r => r.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(e => {
        console.error("Failed to load debug data", e);
        setLoading(false);
      });
  }, [projectId]);

  if (loading) return <div style={{ padding: '2rem' }}>Chargement du debug...</div>;
  if (!data || !data.lines) return <div style={{ padding: '2rem' }}>Aucune donnée trouvée.</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: 'var(--text-main)' }}>
      <h1 style={{ marginBottom: '1rem', fontSize: '2rem' }}>Debug Extraction</h1>
      
      <div style={{ background: 'var(--bg-card)', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem', border: '1px solid var(--border)' }}>
        <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          <strong>Projet ID:</strong> {data.project_id}
        </p>
        <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          <strong>Total Lignes Extraites:</strong> {data.total_lines}
        </p>
        <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          <strong>Pages réelles dans le PDF:</strong> {data.pages_in_pdf}
        </p>
        <p style={{ color: 'var(--text-muted)' }}>
          <strong>Pages / Blocs passés à l'IA:</strong> {data.pages_processed}
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {data.lines.map((line: any, idx: number) => (
          <div key={`${line.mark}-${idx}`} style={{
            border: line.extraction_failed ? '2px solid var(--danger)' : '1px solid var(--success)',
            padding: '1.5rem',
            background: 'var(--bg-card)',
            borderRadius: '8px'
          }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '1.5rem' }}>Mark: {line.mark || 'N/A'}</span>
              {line.extraction_failed && (
                <span className="badge badge-danger">❌ EXTRACTION FAILED</span>
              )}
              {!line.extraction_failed && (
                <span className="badge badge-success">✅ OK</span>
              )}
            </h3>
            
            <div style={{ marginBottom: '1.5rem', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '4px' }}>
              <strong style={{ color: 'var(--text-muted)' }}>Description extraite du PDF (nettoyée) :</strong>
              <p style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>{line.description}</p>
            </div>

            {line.pro_json && line.pro_json._raw_source_text && (
              <div style={{ marginBottom: '1.5rem', background: 'rgba(255,0,0,0.05)', padding: '1rem', borderRadius: '4px', borderLeft: '4px solid var(--danger)' }}>
                <strong style={{ color: 'var(--danger)' }}>Source envoyée à l'IA (Texte brut du bloc/page) :</strong>
                <pre style={{ 
                  marginTop: '0.5rem', 
                  whiteSpace: 'pre-wrap', 
                  lineHeight: '1.5',
                  maxHeight: '300px',
                  overflowY: 'auto',
                  fontSize: '0.85rem'
                }}>{line.pro_json._raw_source_text}</pre>
              </div>
            )}

            <div>
              <strong style={{ color: 'var(--text-muted)' }}>pro_json (structuré par le LLM) :</strong>
              <pre style={{ 
                marginTop: '0.5rem', 
                background: 'var(--bg-dark)', 
                padding: '1rem', 
                borderRadius: '4px',
                overflowX: 'auto',
                fontSize: '0.9rem',
                border: '1px solid var(--border)'
              }}>
                {JSON.stringify({ ...line.pro_json, _raw_source_text: undefined }, null, 2)}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
