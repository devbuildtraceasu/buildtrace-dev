import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";
import { apiRequest } from "@/lib/queryClient";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function AskPanel() {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const { result } = useComparisonStore();
  const [messages, setMessages] = useState<Array<{ id: string; role: "user" | "assistant"; content: string }>>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleQuickQuestion = async (type: "cost" | "schedule") => {
    if (!result?.id) {
      toast({ title: "Unavailable", description: "Run a comparison first.", variant: "destructive" });
      return;
    }
    setIsLoading(true);
    try {
      const prompt =
        type === "cost"
          ? "Provide a short paragraph summarizing the top 3 cost drivers from these changes."
          : "Provide a short paragraph summarizing the top schedule impacts from these changes.";
      const userMsg = { id: `m-${Date.now()}`, role: "user" as const, content: prompt };
      setMessages((prev) => [...prev, userMsg]);

      const res = await apiRequest('POST', '/api/assistants/followup', {
        comparison_id: result.id,
        message: prompt,
      });
      const data = await res.json();
      const assistant = String(data?.assistant_response || "No response available yet.");
      setMessages((prev) => [...prev, { id: `m-${Date.now()}-a`, role: "assistant", content: assistant }]);
    } catch (err) {
      toast({
        title: "Assistant error",
        description: err instanceof Error ? err.message : 'Failed to fetch analysis',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitQuestion = async () => {
    if (!question.trim() || !result?.id) return;
    setIsLoading(true);
    try {
      const content = question.trim();
      setMessages((prev) => [...prev, { id: `m-${Date.now()}`, role: "user", content }]);
      const res = await apiRequest('POST', '/api/assistants/followup', {
        comparison_id: result.id,
        message: content,
      });
      const data = await res.json();
      const assistant = String(data?.assistant_response || "No response available yet.");
      setMessages((prev) => [...prev, { id: `m-${Date.now()}-a`, role: "assistant", content: assistant }]);
      setQuestion("");
    } catch (err) {
      toast({
        title: "Assistant error",
        description: err instanceof Error ? err.message : 'Failed to send message',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-card p-6" data-testid="ask-panel">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Ask About Changes</h3>

      <div className="space-y-5">
        {/* Chat transcript */}
        <ScrollArea className="h-80 border rounded-2xl p-4 bg-gray-50">
          <div className="space-y-3 h-full">
            {messages.length === 0 && !isLoading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-gray-700 text-base mb-1">Ask questions about the drawing changes</p>
                  <p className="text-sm text-gray-500">Example: “What changed in the north wing?” or “Summarize door modifications”.</p>
                </div>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.role === 'user' ? (
                  <div className="max-w-[80%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap shadow-sm bg-blue-600 text-white">
                    {m.content}
                  </div>
                ) : (
                  <div className="max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm bg-white border prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl px-3 py-2 text-sm bg-white border text-gray-600">
                  Thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        {/* Quick prompts */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700">Quick Questions:</div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickQuestion("cost")}
              disabled={isLoading}
              className="rounded-full px-3"
              data-testid="button-cost-impact"
            >
              <span className="mr-1">💰</span> Cost Impact
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleQuickQuestion("schedule")}
              disabled={isLoading}
              className="rounded-full px-3"
              data-testid="button-schedule-impact"
            >
              <span className="mr-1">🗓️</span> Schedule Impact
            </Button>
          </div>
        </div>

        {/* Composer */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Input
              placeholder="Ask a question about the changes..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (!isLoading && question.trim() && result?.id) handleSubmitQuestion();
                }
              }}
              className="text-sm h-11 rounded-full focus-visible:ring-0 focus-visible:ring-offset-0 focus:ring-0 focus:outline-none focus:border-gray-300"
              data-testid="textarea-question"
            />
            <Button
              onClick={handleSubmitQuestion}
              disabled={isLoading || !question.trim() || !result?.id}
              className="shrink-0 h-11 w-11 rounded-full"
              size="icon"
              aria-label="Send"
              data-testid="button-ask-ai"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <div className="text-xs text-gray-500">Try asking: “Which walls were added?” or “Summarize all changes in the clouded areas.”</div>
        </div>
      </div>
    </div>
  );
}
