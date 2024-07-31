import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./App.css";
import QueueStatus from "./QueueStatus";

import "@xyflow/react/dist/style.css";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <QueueStatus></QueueStatus>
    </QueryClientProvider>
  );
}
