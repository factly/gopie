import { Button } from "@/components/ui/button";
import { Volume2, VolumeX } from "lucide-react";
import {
  LiveKitRoom,
  useRoomContext,
  RoomAudioRenderer,
} from "@livekit/components-react";
import { useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";

interface TTSButtonProps {
  text: string;
  role: "user" | "assistant";
  datasetId?: string;
}

export async function getLiveKitCredentials(datasetId: string) {
  const response = await fetch(`/api/livekit?datasetId=${datasetId}`);
  if (!response.ok) {
    throw new Error("Failed to get LiveKit credentials");
  }
  return response.json();
}

function TTSInner({ text, datasetId }: { text: string; datasetId?: string }) {
  const room = useRoomContext();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleTTS = async () => {
    if (!datasetId) {
      toast.error("Dataset ID is required for TTS");
      return;
    }

    if (isPlaying) {
      // Stop playback
      setIsPlaying(false);
      return;
    }

    try {
      setIsPlaying(true);
      setIsConnecting(true);

      // Get LiveKit credentials and connect to room first
      const { token, serverUrl } = await getLiveKitCredentials(datasetId);
      if (!serverUrl || !token) {
        throw new Error("LiveKit configuration missing");
      }

      // Make sure we're connected before sending data
      if (room.state !== "connected") {
        console.log("Connecting to LiveKit room...");
        await room.connect(serverUrl, token);
        console.log("Connected to LiveKit room");
      }

      setIsConnecting(false);

      // Send the text to be converted to speech
      await room.localParticipant.publishData(new TextEncoder().encode(text), {
        reliable: true,
      });
      await room.localParticipant.sendText(text);
      await room.localParticipant.sendChatMessage(text);
      console.log("Text sent to LiveKit");
    } catch (error) {
      console.error("Failed to start TTS:", error);
      toast.error("Failed to start text-to-speech");
      setIsPlaying(false);
      setIsConnecting(false);
    }
  };

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={handleTTS}
            disabled={isConnecting}
          >
            {isConnecting ? (
              <span className="h-3 w-3 rounded-full bg-primary/50 animate-pulse" />
            ) : isPlaying ? (
              <VolumeX className="h-3 w-3" />
            ) : (
              <Volume2 className="h-3 w-3" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {isConnecting
            ? "Connecting..."
            : isPlaying
            ? "Stop speaking"
            : "Speak message"}
        </TooltipContent>
      </Tooltip>
      <RoomAudioRenderer />
    </>
  );
}

export function TTSButton({ text, role, datasetId }: TTSButtonProps) {
  // React hooks must be called before any conditional returns
  const [serverUrl] = useState("");
  const [token] = useState("");

  // Only show TTS for assistant messages
  if (role !== "assistant") return null;

  return (
    <LiveKitRoom
      serverUrl={serverUrl}
      token={token}
      connect={false}
      audio={true}
    >
      <TTSInner text={text} datasetId={datasetId} />
    </LiveKitRoom>
  );
}
