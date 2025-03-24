import { useState, useCallback, useEffect, useRef } from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  LiveKitRoom,
  useLocalParticipant,
  useTrackTranscription,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react";
import "@livekit/components-styles";
import type { TrackReference } from "@livekit/components-core";
import { createLocalAudioTrack, Track, RoomEvent } from "livekit-client";
import { toast } from "sonner";

interface AudioInputProps {
  onTranscriptionReceived: (text: string) => void;
  datasetId: string;
}

export function AudioInput({
  onTranscriptionReceived,
  datasetId,
}: AudioInputProps) {
  const [token, setToken] = useState<string>("");
  const [serverUrl, setServerUrl] = useState<string>("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState<string>("");

  // Fetch LiveKit token when starting recording
  const fetchToken = useCallback(async () => {
    try {
      const response = await fetch(`/api/livekit?datasetId=${datasetId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch token");
      }
      const data = await response.json();
      setToken(data.token);
      setServerUrl(data.serverUrl);
    } catch (error) {
      console.error("Error fetching LiveKit token:", error);
      toast.error("Failed to start recording");
      setIsConnecting(false);
    }
  }, [datasetId]);

  const handleStartRecording = useCallback(async () => {
    setIsConnecting(true);
    setCurrentTranscription(""); // Reset transcription when starting new recording
    await fetchToken();
    setIsRecording(true);
    setIsConnecting(false);
  }, [fetchToken]);

  const handleStopRecording = useCallback(() => {
    setIsRecording(false);
    setToken("");
    setServerUrl("");
    // Send final transcription when stopping
    if (currentTranscription) {
      onTranscriptionReceived(currentTranscription);
    }
  }, [currentTranscription, onTranscriptionReceived]);

  const handleTranscriptionUpdate = useCallback(
    (text: string) => {
      setCurrentTranscription(text);
      onTranscriptionReceived(text);
    },
    [onTranscriptionReceived]
  );

  if (!isRecording) {
    return (
      <Button
        variant="ghost"
        size="icon"
        onClick={handleStartRecording}
        disabled={isConnecting}
        id="start-recording-button"
      >
        <Mic className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={handleStopRecording}
        className="text-red-500"
      >
        <MicOff className="h-4 w-4" />
      </Button>
      {token && serverUrl && (
        <LiveKitRoom
          token={token}
          serverUrl={serverUrl}
          connect={true}
          audio={true}
          video={false}
          data-lk-theme="default"
        >
          <AudioPublisher onTranscriptionReceived={handleTranscriptionUpdate} />
          <RoomAudioRenderer />
        </LiveKitRoom>
      )}
    </>
  );
}

function AudioPublisher({
  onTranscriptionReceived,
}: {
  onTranscriptionReceived: (text: string) => void;
}) {
  const room = useRoomContext();
  const { localParticipant } = useLocalParticipant();
  const [audioTrack, setAudioTrack] = useState<TrackReference>();
  const transcriptionBuffer = useRef<string[]>([]);

  // Start publishing audio track when component mounts
  useEffect(() => {
    let mounted = true;
    let cleanup: (() => void) | undefined;

    async function startAudio() {
      if (!localParticipant || !room) return;

      try {
        // Wait for room to be connected
        if (room.state !== "connected") {
          await new Promise<void>((resolve) => {
            const onConnected = () => {
              resolve();
              room.off(RoomEvent.Connected, onConnected);
            };
            room.on(RoomEvent.Connected, onConnected);
          });
        }

        // Create and publish the track
        const track = await createLocalAudioTrack({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        });

        if (!mounted) {
          track.stop();
          return;
        }

        const publication = await localParticipant.publishTrack(track);

        if (!mounted) {
          publication.track?.stop();
          return;
        }

        setAudioTrack({
          participant: localParticipant,
          publication,
          source: Track.Source.Microphone,
        });

        cleanup = () => {
          track.stop();
          publication.track?.stop();
          localParticipant.unpublishTrack(track);
        };
      } catch (error) {
        console.error("Error publishing audio track:", error);
        toast.error("Failed to start audio recording");
      }
    }

    startAudio();

    return () => {
      mounted = false;
      cleanup?.();
      // Clear transcription buffer on cleanup
      transcriptionBuffer.current = [];
    };
  }, [localParticipant, room]);

  // Handle transcriptions with buffering
  useTrackTranscription(audioTrack, {
    bufferSize: 5,
    onTranscription: (newSegments) => {
      if (newSegments.length > 0) {
        const latestSegment = newSegments[newSegments.length - 1];
        if (latestSegment.text) {
          // Update buffer with new text
          transcriptionBuffer.current.push(latestSegment.text);
          // Keep only last 5 segments
          if (transcriptionBuffer.current.length > 5) {
            transcriptionBuffer.current.shift();
          }
          // Combine all segments and send
          const fullText = transcriptionBuffer.current.join(" ");
          onTranscriptionReceived(fullText);
        }
      }
    },
  });

  return null;
}
