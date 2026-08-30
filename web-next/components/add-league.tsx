"use client";

import { useState } from "react";

export function AddLeague() {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  function request(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!/^\d+$/.test(id)) return;
    const text = `/requestleague ${id}${name.trim() ? ` ${name.trim()}` : ""}`;
    window.open(`https://t.me/Fplnaf_bot?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  }
  return <form className="add-league" aria-label="Request league tracking" onSubmit={request}><label className="sr-only" htmlFor="league-id">FPL league ID</label><input id="league-id" inputMode="numeric" value={id} onChange={(event) => setId(event.target.value.replace(/\D/g, ""))} placeholder="League ID" aria-describedby="league-help" required /><label className="sr-only" htmlFor="league-name">Optional league name</label><input id="league-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Optional name" /><button type="submit" disabled={!id}>Request tracking</button><small id="league-help">Opens Telegram with a tracking request. Your league ID and optional name are sent only when you submit there.</small></form>;
}
