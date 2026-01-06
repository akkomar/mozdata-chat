"use client";

import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useAuth } from "@/components/AuthProvider";
import { CopilotKitProvider } from "@/components/CopilotKitProvider";
import { ToolRenderer } from "@/components/ToolRenderer";

export default function CopilotKitPage() {
  const { user, loading, signIn, signOut } = useAuth();
  const themeColor = "#475569"; // slate-600

  // Show loading state
  if (loading) {
    return (
      <div
        style={{ backgroundColor: themeColor }}
        className="h-screen flex justify-center items-center"
      >
        <div className="text-white text-center">
          <div className="animate-pulse text-2xl">Loading...</div>
        </div>
      </div>
    );
  }

  // Show sign-in page if not authenticated
  if (!user) {
    return (
      <div
        style={{ backgroundColor: themeColor }}
        className="h-screen flex justify-center items-center flex-col"
      >
        <div className="text-white text-center p-8 max-w-2xl">
          <h1 className="text-4xl font-bold mb-4">Mozdata Assistant</h1>
          <p className="text-xl opacity-90 mb-8">
            Ask questions about Mozilla telemetry, BigQuery datasets, Glean SDK,
            Looker, and data pipelines.
          </p>
          <button
            onClick={signIn}
            className="bg-white text-slate-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors shadow-lg"
          >
            Sign in with Google (@mozilla.com)
          </button>
        </div>
      </div>
    );
  }

  // Show main app for authenticated users - wrap with CopilotKitProvider
  return (
    <CopilotKitProvider>
      {/* ToolRenderer captures all tool calls and renders them in collapsible format */}
      <ToolRenderer />
      <main
        style={
          { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
        }
        className="h-screen flex flex-col"
      >
        {/* Header with user info and sign-out */}
        <header className="flex justify-between items-center p-4 border-b">
          <h1 className="text-lg font-semibold">Mozdata Assistant</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user.email}</span>
            <button
              onClick={signOut}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Sign out
            </button>
          </div>
        </header>

        {/* Full-screen chat */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full max-w-3xl mx-auto">
            <CopilotChat
              disableSystemMessage={true}
              labels={{
                title: "Mozdata Assistant",
                initial: "Hi! I can help you with Mozilla data documentation, BigQuery datasets, Glean SDK, writing SQL queries.",
              }}
              suggestions={[
                {
                  title: "Get Started",
                  message: "How do I get access to Mozilla's data warehouse and write my first BigQuery query?",
                },
                {
                  title: "Write a query",
                  message: "Write a query for Firefox Android DAU by country",
                },
              ]}
              className="h-full"
            />
          </div>
        </div>
      </main>
    </CopilotKitProvider>
  );
}
