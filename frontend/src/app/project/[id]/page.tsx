"use client"
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<any>(null);
  const [pollCount, setPollCount] = useState(0);
  const [pollingError, setPollingError] = useState(false);
  const router = useRouter();

  useEffect(() => {
    let currentPoll = pollCount;
    const fetchProject = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const res = await fetch(`${apiUrl}/projects/${params.id}`);
        if (res.ok) {
          const data = await res.json();
          let stillProcessing = false;
          
          const updatedLines = await Promise.all(data.lines.map(async (line: any) => {
             if (line.thread_id && line.status !== 'finalized') {
                const stateRes = await fetch(`${apiUrl}/workflow/runs/${line.thread_id}/state`);
                if (stateRes.ok) {
                   const stateData = await stateRes.json();
                   if (stateData.values?.status === "no_match") {
                       line.workflow_status = "no_match";
                   } else if (stateData.next?.includes("human_approval_gate")) {
                       line.workflow_status = "action_required";
                   } else if (stateData.is_finished) {
                       line.workflow_status = "finalized";
                   } else {
                       line.workflow_status = "processing";
                       stillProcessing = true;
                   }
                }
             }
             return line;
          }));
          data.lines = updatedLines;
          
          if (updatedLines.length > 0 && updatedLines.every((l: any) => l.workflow_status === "finalized" || l.workflow_status === "no_match")) {
              data.all_finalized = true;
          }
          setProject(data);
          
          if (stillProcessing) {
             currentPoll += 1;
             setPollCount(currentPoll);
             if (currentPoll > 10) {
                 setPollingError(true);
             }
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    
    fetchProject();
    if (pollCount <= 10 && !project?.all_finalized) {
      const intervalId = setInterval(fetchProject, 3000);
      return () => clearInterval(intervalId);
    }
  }, [params.id, pollCount, project?.all_finalized]);

  const hasNoMatch = project?.lines?.some((l: any) => l.workflow_status === 'no_match');

  return (
    <div>
      <button className="btn" onClick={() => router.push('/')} style={{ marginBottom: '1rem', background: 'var(--border)' }}>
        ← Back
      </button>
      
      <h1>Project Details</h1>
      
      {pollingError && (
        <div className="card" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', marginBottom: '1rem' }}>
          <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ Polling timeout: Could not retrieve final status for some lines after multiple attempts.</p>
        </div>
      )}

      {hasNoMatch && (
        <div className="card" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', marginBottom: '1rem' }}>
          <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ Warning: Some line items have no viable matching candidates.</p>
        </div>
      )}
      
      {!project ? (
        <div className="card">Loading project...</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ margin: 0 }}>{project.name}</h2>
              <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                Status: <span className="badge badge-warning">{project.status}</span>
              </p>
            </div>
            {project.all_finalized && (
              <button className="btn" style={{ background: 'var(--success)' }} onClick={() => router.push(`/finalize/${project.id}`)}>
                Finalize BOM
              </button>
            )}
          </div>

          <h3>Line Items</h3>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="matrix">
              <thead>
                <tr>
                  <th>Mark</th>
                  <th>Quantity</th>
                  <th>Description</th>
                  <th>Workflow Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {project.lines?.map((line: any) => (
                  <tr key={line.id}>
                    <td><strong>{line.mark}</strong></td>
                    <td>{line.quantity}</td>
                    <td>{line.description}</td>
                    <td>
                      <span className={`badge ${line.workflow_status === 'finalized' ? 'badge-success' : line.workflow_status === 'action_required' ? 'badge-warning' : line.workflow_status === 'no_match' ? 'badge-danger' : 'badge-danger'}`}>
                        {line.workflow_status || line.status}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="btn" 
                        onClick={() => router.push(`/line/${line.id}`)}
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                        disabled={line.workflow_status === 'finalized' || line.workflow_status === 'no_match'}
                      >
                        {line.workflow_status === 'finalized' ? 'Selected' : line.workflow_status === 'no_match' ? 'No Match' : 'Compare'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
