import React, { createContext, useContext, useState, useCallback } from "react";

const TicketDetailContext = createContext(null);

export function TicketDetailProvider({ children }) {
  const [ticketId, setTicketId] = useState(null);

  const openTicket = useCallback((id) => setTicketId(id), []);
  const closeTicket = useCallback(() => setTicketId(null), []);

  return (
    <TicketDetailContext.Provider value={{ ticketId, openTicket, closeTicket }}>
      {children}
    </TicketDetailContext.Provider>
  );
}

export function useTicketDetail() {
  const ctx = useContext(TicketDetailContext);
  if (!ctx) throw new Error("useTicketDetail must be used within a TicketDetailProvider");
  return ctx;
}
