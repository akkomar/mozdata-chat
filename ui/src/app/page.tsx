"use client";

import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useAuth } from "@/components/AuthProvider";
import { CopilotKitProvider } from "@/components/CopilotKitProvider";
import { ToolRenderer } from "@/components/ToolRenderer";

export default function CopilotKitPage() {
  const { user, loading, signIn, signOut } = useAuth();
  const themeColor = "#52525b"; // zinc-600 - warmer than slate

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
          <h1
            className="text-4xl font-bold mb-4"
            style={{ textShadow: "0 2px 4px rgba(0,0,0,0.15)" }}
          >
            Mozdata Assistant
          </h1>
          <p className="text-xl opacity-90 mb-8">
            Ask questions about Mozilla telemetry, BigQuery datasets, Glean SDK,
            Looker, and data pipelines. Get help writing SQL queries.
          </p>
          <button
            onClick={signIn}
            className="bg-white text-zinc-700 font-semibold px-8 py-3 rounded-lg hover:bg-gray-50 hover:scale-[1.02] transition-all shadow-lg flex items-center gap-3 mx-auto"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
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
        <header className="flex justify-between items-center px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
          <h1 className="text-lg font-semibold text-zinc-700">Mozdata Assistant</h1>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-zinc-600 flex items-center justify-center text-white text-xs font-medium">
                {user.email?.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-gray-600 hidden sm:inline">{user.email}</span>
            </div>
            <div className="w-px h-5 bg-gray-200" />
            <button
              onClick={signOut}
              className="text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 px-2 py-1 rounded transition-colors"
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
