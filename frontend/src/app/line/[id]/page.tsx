"use client"
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ComparisonMatrix from '@/components/ComparisonMatrix';

export default function LinePage({ params }: { params: { id: string } }) {
  const [line, setLine] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchLine = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const res = await fetch(`${apiUrl}/lines/${params.id}`);
        if (res.ok) {
          setLine(await res.json());
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchLine();
  }, [params.id]);

  const handleSelect = async (sku: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const thread_id = line.thread_id;
      if (!thread_id) return alert('Workflow thread_id missing!');
      
      const res = await fetch(`${apiUrl}/workflow/runs/${thread_id}/resume`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'approved', selected_sku: sku })
      });
      if (res.ok) {
          router.back();
      } else {
          alert('Failed to resume workflow');
      }
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div>
      <button className="btn" onClick={() => router.back()} style={{ marginBottom: '1rem', background: 'var(--border)' }}>
        ← Back
      </button>
      
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2>Line Item Details</h2>
        {!line ? <p>Loading...</p> : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
            <div>
              <p><strong>Mark:</strong> {line.mark}</p>
              <p><strong>Description:</strong> {line.description}</p>
              <p><strong>Specified SKU:</strong> {line.specified_sku || 'N/A'}</p>
            </div>
            <div>
              <p><strong>Required Lumens:</strong> {line.pro?.photometric?.lumens_min} lm</p>
              <p><strong>Required CCT:</strong> {line.pro?.photometric?.cct} K</p>
            </div>
          </div>
        )}
      </div>

      <h2>Comparison Matrix</h2>
      {line && <ComparisonMatrix candidates={line.candidates} target={line.pro} onSelect={handleSelect} />}
    </div>
  );
}
