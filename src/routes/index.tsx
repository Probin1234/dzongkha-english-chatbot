import { createFileRoute } from "@tanstack/react-router";
import { ChatDesk } from "@/components/chat-desk";

export const Route = createFileRoute("/")({
  component: Home,
});

function Home() {
  return <ChatDesk />;
}
