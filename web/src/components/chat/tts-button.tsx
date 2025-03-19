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

  const handleTTS = async () => {
    if (!datasetId) {
      toast.error("Dataset ID is required for TTS");
      return;
    }

    if (isPlaying) {
      // Stop playback
      setIsPlaying(false);
      await room.disconnect();
      return;
    }

    try {
      setIsPlaying(true);
      // Get LiveKit credentials
      const { token, serverUrl } = await getLiveKitCredentials(datasetId);
      if (!serverUrl || !token) {
        throw new Error("LiveKit configuration missing");
      }

      // Connect to room and start TTS
      await room.connect(serverUrl, token);
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
          >
            {isPlaying ? (
              <VolumeX className="h-3 w-3" />
            ) : (
              <Volume2 className="h-3 w-3" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          {isPlaying ? "Stop speaking" : "Speak message"}
        </TooltipContent>
      </Tooltip>
      <RoomAudioRenderer />
    </>
  );
}

export function TTSButton({ text, role, datasetId }: TTSButtonProps) {
  // Only show TTS for assistant messages
  if (role !== "assistant") return null;

  return (
    <LiveKitRoom serverUrl="" token="" connect={false} audio={true}>
      <TTSInner text={text} datasetId={datasetId} />
    </LiveKitRoom>
  );
}
