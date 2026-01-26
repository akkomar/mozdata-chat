"use client";

interface BackendLoadingScreenProps {
  attemptCount: number;
  error: string | null;
  onRetry: () => void;
}

function getStatusMessage(attemptCount: number): string {
  if (attemptCount <= 5) {
    return "Connecting to backend...";
  } else if (attemptCount <= 15) {
    return "Warming up the assistant...";
  } else if (attemptCount <= 30) {
    return "Almost ready...";
  } else {
    return "Still working on it...";
  }
}

export function BackendLoadingScreen({
  attemptCount,
  error,
  onRetry,
}: BackendLoadingScreenProps) {
  const themeColor = "#52525b"; // zinc-600

  if (error) {
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
          <p className="text-xl opacity-90 mb-6">{error}</p>
          <button
            onClick={onRetry}
            className="bg-white text-zinc-700 font-semibold px-8 py-3 rounded-lg hover:bg-gray-50 hover:scale-[1.02] transition-all shadow-lg"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen flex justify-center items-center flex-col"
    >
      <div className="text-white text-center p-8 max-w-2xl">
        <h1
          className="text-4xl font-bold mb-6"
          style={{ textShadow: "0 2px 4px rgba(0,0,0,0.15)" }}
        >
          Mozdata Assistant
        </h1>

        {/* Animated bouncing dots */}
        <div className="flex justify-center gap-2 mb-6">
          <span
            className="w-3 h-3 bg-white rounded-full animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="w-3 h-3 bg-white rounded-full animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="w-3 h-3 bg-white rounded-full animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>

        <p className="text-xl opacity-90">{getStatusMessage(attemptCount)}</p>

        {attemptCount > 10 && (
          <p className="text-sm opacity-60 mt-4">
            This may take up to a minute on first load
          </p>
        )}
      </div>
    </div>
  );
}
