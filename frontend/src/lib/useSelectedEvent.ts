import { useEffect, useState } from "react";

const KEY = "safestage:event_id";

export function setStoredEventId(id: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(KEY, id);
}

export function useSelectedEvent() {
  const [eventId, setEventId] = useState<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem(KEY);
    if (stored) setEventId(stored);
  }, []);

  const select = (id: string) => {
    setEventId(id);
    setStoredEventId(id);
  };

  return { eventId, select };
}
