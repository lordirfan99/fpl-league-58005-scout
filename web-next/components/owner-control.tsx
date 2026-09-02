"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, LockKeyhole, Send, ShieldCheck } from "lucide-react";

declare global {
  interface Window { google?: { accounts: { id: { initialize: (options: Record<string, unknown>) => void; renderButton: (element: HTMLElement, options: Record<string, unknown>) => void } } } }
}

type Status = { target_gameweek: number; deadline: string; session_connector: string; telegram: string; google_sign_in: string; automation_locked: boolean };

export function OwnerControl({ clientId, targetGameweek, captain }: { clientId: string; targetGameweek: number; captain?: { name: string; element: number } }) {
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!clientId) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => window.google?.accounts.id.initialize({ client_id: clientId, callback: (result: { credential?: string }) => setToken(result.credential ?? "") });
    document.head.appendChild(script);
    return () => script.remove();
  }, [clientId]);

  useEffect(() => {
    if (!token) return;
    void loadStatus();
  }, [token]);

  async function api(path: string, init?: RequestInit) {
    const response = await fetch(`/api/control/${path}`, { ...init, headers: { ...init?.headers, authorization: `Bearer ${token}`, "content-type": "application/json" } });
    const body = await response.json() as Record<string, unknown>;
    if (!response.ok) throw new Error(String(body.detail ?? body.error ?? "Request failed"));
    return body;
  }

  async function loadStatus() {
    try { setStatus(await api("status") as Status); setMessage(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not load control status"); }
  }

  async function createCaptainAction() {
    if (!captain) return;
    setLoading(true);
    try {
      const body = await api("actions", { method: "POST", body: JSON.stringify({ target_gameweek: targetGameweek, changes: { captain: captain.element }, summary: `Captain ${captain.name}` }) });
      const action = body.action as { expires_at: string; action_id: string };
      setMessage(`Approval card created for ${captain.name}. It expires ${new Date(action.expires_at).toLocaleTimeString("en-MY", { timeStyle: "short" })}.`);
      await loadStatus();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Action could not be created"); }
    finally { setLoading(false); }
  }

  async function setLock(locked: boolean) {
    setLoading(true);
    try { await api("emergency-lock", { method: "POST", body: JSON.stringify({ locked, reason: "owner_dashboard" }) }); await loadStatus(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Lock state could not be changed"); }
    finally { setLoading(false); }
  }

  if (!clientId) return <section className="surface owner-control"><LockKeyhole /><div><span>PRIVATE CONTROL</span><h2>Google sign-in needs setup</h2><p>Add the Google OAuth client ID and owner email as deployment secrets. The action system remains locked until then.</p></div></section>;
  if (!token) return <section className="surface owner-control"><ShieldCheck /><div><span>PRIVATE CONTROL</span><h2>Sign in to manage actions</h2><p>Only the allowlisted Google account can create action cards or change the emergency lock.</p><div ref={(node) => { if (node && window.google) window.google.accounts.id.renderButton(node, { theme: "outline", size: "large", text: "signin_with" }); }} /></div></section>;
  return <section className="surface owner-control"><div><span>PRIVATE CONTROL</span><h2>{status?.automation_locked ? "Automation is locked" : "Approval control ready"}</h2><p>Telegram confirmations expire in 15 minutes. Chips require a second confirmation.</p></div><div className="control-statuses"><small>Session: <b>{status?.session_connector ?? "checking"}</b></small><small>Telegram: <b>{status?.telegram ?? "checking"}</b></small></div>{captain ? <button disabled={loading || Boolean(status?.automation_locked)} onClick={createCaptainAction}><Send size={15} /> Create captain approval: {captain.name}</button> : null}<button className="quiet" disabled={loading} onClick={() => void setLock(!status?.automation_locked)}>{status?.automation_locked ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}{status?.automation_locked ? "Unlock automation" : "Emergency lock"}</button>{message ? <p className="control-message">{message}</p> : null}</section>;
}
