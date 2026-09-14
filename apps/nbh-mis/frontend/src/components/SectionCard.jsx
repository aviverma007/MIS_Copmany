import React from "react";

export default function SectionCard({ title, subtitle, action, children, className = "", bodyClassName = "" }) {
  return (
    <div className={`card flex flex-col ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <div>
            {title && <h2 className="section-title">{title}</h2>}
            {subtitle && <p className="text-xs text-ink-500 mt-0.5">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={`flex-1 p-4 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
