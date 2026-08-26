"use client";

import { useState } from "react";

export function AddLeague() {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  function request() {
    if (!/^\d+$/.test(id)) return;
    const text = `/requestleague ${id}${name.trim() ? ` ${name.trim()}` : ""}`;
    window.open(`https://t.me/Fplnaf_bot?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  }
  return <div className="add-league" aria-label="Add tracked league"><input inputMode="numeric" value={id} onChange={(event) => setId(event.target.value.replace(/\D/g, ""))} placeholder="League ID" aria-label="FPL league ID" /><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Optional name" aria-label="Optional league name" /><button type="button" onClick={request} disabled={!id}>Request tracking</button></div>;
}
