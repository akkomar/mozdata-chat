'use client';

import { useCopilotAction, CatchAllActionRenderProps } from '@copilotkit/react-core';
import { useState } from 'react';

/**
 * Collapsible tool call display component.
 * Shows tool calls in a compact, expandable format like Gemini's UI.
 */
function ToolCallDisplay({
  name,
  status,
  args,
}: {
  name: string;
  status: string;
  args: Record<string, unknown>;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format tool name for display (remove underscores, etc.)
  const displayName = name.replace(/_/g, ' ');

  // Get status indicator
  const statusIndicator = status === 'complete' ? '✓' : status === 'executing' ? '⟳' : '○';
  const statusColor = status === 'complete' ? 'text-green-600' : status === 'executing' ? 'text-blue-500' : 'text-gray-400';

  // Create compact args summary
  const argsSummary = Object.entries(args || {})
    .slice(0, 2)
    .map(([key, value]) => {
      const strValue = typeof value === 'string' ? value : JSON.stringify(value);
      const truncated = strValue.length > 30 ? strValue.substring(0, 30) + '...' : strValue;
      return `${key}: ${truncated}`;
    })
    .join(', ');

  return (
    <div className="my-1 text-sm border-l-2 border-gray-200 pl-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors w-full text-left"
      >
        <span className={`text-xs ${statusColor}`}>{statusIndicator}</span>
        <span className="font-medium">{displayName}</span>
        {!isExpanded && argsSummary && (
          <span className="text-gray-400 truncate text-xs">({argsSummary})</span>
        )}
        <span className="ml-auto text-gray-400 text-xs">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>

      {isExpanded && args && Object.keys(args).length > 0 && (
        <div className="mt-1 pl-4 text-xs text-gray-500 bg-gray-50 rounded p-2 overflow-auto max-h-32">
          <pre>{JSON.stringify(args, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

/**
 * Tool renderer component that captures all tool calls and renders them
 * in a collapsible format. Must be placed inside CopilotKitProvider.
 */
export function ToolRenderer() {
  useCopilotAction({
    name: '*', // Matches all tool calls
    render: ({ name, status, args }: CatchAllActionRenderProps<[]>) => (
      <ToolCallDisplay
        name={name}
        status={status}
        args={args as Record<string, unknown>}
      />
    ),
  });

  return null;
}
