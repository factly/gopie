import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, X } from "lucide-react";
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
import { getLiveKitCredentials } from "./tts-button"; // Import the helper function

interface VoiceModeProps {
  isActive: boolean;
  onToggle: () => void;
  onSendMessage: (message: string) => Promise<void>;
  latestAssistantMessage: string | null;
  datasetId: string;
  isWaitingForResponse: boolean;
}

export function VoiceMode({
  isActive,
  onToggle,
  onSendMessage,
  latestAssistantMessage,
  datasetId,
  isWaitingForResponse,
}: VoiceModeProps) {
  const [token, setToken] = useState<string>("");
  const [serverUrl, setServerUrl] = useState<string>("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState<string>("");
  const [visualizerValues, setVisualizerValues] = useState<number[]>(
    Array(20).fill(5)
  );
  const visualizerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const shouldAutoStartRecording = useRef(false);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastTranscriptionUpdateRef = useRef<number>(Date.now());
  const prevAssistantMessageRef = useRef<string | null>(null);
  const autoSendTimeoutMs = 1500; // 1.5 seconds of silence to auto-send

  // Visualizer animation
  const startVisualizer = useCallback(() => {
    if (visualizerIntervalRef.current) {
      clearInterval(visualizerIntervalRef.current);
    }

    visualizerIntervalRef.current = setInterval(() => {
      setVisualizerValues((prev) =>
        prev.map(() => Math.floor(Math.random() * 20) + 5)
      );
    }, 100);
  }, []);

  const stopVisualizer = useCallback(() => {
    if (visualizerIntervalRef.current) {
      clearInterval(visualizerIntervalRef.current);
      visualizerIntervalRef.current = null;
    }
    setVisualizerValues(Array(20).fill(5));
  }, []);

  // Fetch LiveKit token
  const fetchToken = useCallback(async () => {
    try {
      const response = await fetch(`/api/livekit?datasetId=${datasetId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch token");
      }
      const data = await response.json();
      setToken(data.token);
      setServerUrl(data.serverUrl);
      return { token: data.token, serverUrl: data.serverUrl };
    } catch (error) {
      console.error("Error fetching LiveKit token:", error);
      toast.error("Failed to start voice mode");
      setIsConnecting(false);
      return null;
    }
  }, [datasetId]);

  // Cancel silence timer
  const cancelSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  // Helper to ensure clean room disconnection before switching modes
  const cleanupCurrentSession = useCallback(async () => {
    if (token && serverUrl) {
      console.log("Cleaning up current LiveKit session");
      // Give time for any ongoing operations to finish
      await new Promise((resolve) => setTimeout(resolve, 300));
      setToken("");
      setServerUrl("");
    }

    // Reset all state for a clean transition
    cancelSilenceTimer();
    stopVisualizer();
  }, [token, serverUrl, cancelSilenceTimer, stopVisualizer]);

  // Start recording
  const startRecording = useCallback(async () => {
    // Make sure any previous session is cleaned up
    await cleanupCurrentSession();

    setIsConnecting(true);
    setCurrentTranscription(""); // Reset transcription
    console.log("Fetching new token for recording");
    await fetchToken();
    setIsRecording(true);
    setIsConnecting(false);
    startVisualizer();
    lastTranscriptionUpdateRef.current = Date.now();
  }, [fetchToken, startVisualizer, cleanupCurrentSession]);

  // Stop recording and send message
  const stopRecording = useCallback(async () => {
    cancelSilenceTimer();
    setIsRecording(false);
    setToken("");
    setServerUrl("");
    stopVisualizer();

    // Send final transcription when stopping
    if (currentTranscription.trim()) {
      await onSendMessage(currentTranscription.trim());
    }
  }, [currentTranscription, onSendMessage, stopVisualizer, cancelSilenceTimer]);

  // Set up silence detection
  const resetSilenceTimer = useCallback(() => {
    cancelSilenceTimer();

    // Only set up the timer if we have some transcription
    if (currentTranscription.trim()) {
      silenceTimerRef.current = setTimeout(() => {
        console.log("Silence detected, auto-sending message");
        stopRecording();
      }, autoSendTimeoutMs);
    }
  }, [cancelSilenceTimer, currentTranscription, stopRecording]);

  // Handle transcription updates
  const handleTranscriptionUpdate = useCallback(
    (text: string) => {
      setCurrentTranscription(text);
      lastTranscriptionUpdateRef.current = Date.now();
      resetSilenceTimer();
    },
    [resetSilenceTimer]
  );

  // TTS for assistant messages
  const speakAssistantMessage = useCallback(async () => {
    if (!latestAssistantMessage || isSpeaking) return;

    // Skip if this is the same message we already processed
    if (latestAssistantMessage === prevAssistantMessageRef.current) {
      return;
    }

    // Make sure recording is stopped cleanly before speaking
    if (isRecording) {
      console.log("Stopping recording before speaking");
      setIsRecording(false);
      await cleanupCurrentSession();
    }

    prevAssistantMessageRef.current = latestAssistantMessage;

    try {
      setIsSpeaking(true);
      startVisualizer();

      if (!datasetId) {
        toast.error("Dataset ID is required for TTS");
        setIsSpeaking(false);
        stopVisualizer();
        return;
      }

      // Get LiveKit credentials
      console.log("Fetching token for TTS");
      const { token, serverUrl } = await getLiveKitCredentials(datasetId);
      if (!serverUrl || !token) {
        throw new Error("LiveKit configuration missing");
      }

      // Set token and server URL for the LiveKitRoom component
      setToken(token);
      setServerUrl(serverUrl);

      // We use a longer timeout as baseline for any message
      // This ensures even short messages have enough time to be spoken
      const minWaitTime = 3000; // minimum 3 seconds
      const waitTime = Math.max(
        minWaitTime,
        latestAssistantMessage.length * 90
      );
      console.log(`Speaking message (will wait ${waitTime}ms)...`);

      await new Promise((resolve) => setTimeout(resolve, waitTime));

      console.log("Speech completed, cleaning up");
      await cleanupCurrentSession();
      setIsSpeaking(false);

      // Auto-start recording after speech completes
      if (isActive) {
        console.log("Preparing to start recording again...");
        shouldAutoStartRecording.current = true;
      }
    } catch (error) {
      console.error("Failed to speak message:", error);
      toast.error("Failed to speak message");
      setIsSpeaking(false);
      await cleanupCurrentSession();
    }
  }, [
    latestAssistantMessage,
    isSpeaking,
    isRecording,
    datasetId,
    isActive,
    startVisualizer,
    cleanupCurrentSession,
  ]);

  // Periodic check for silence during recording
  useEffect(() => {
    if (isRecording && currentTranscription.trim()) {
      const intervalId = setInterval(() => {
        const now = Date.now();
        const timeSinceLastUpdate = now - lastTranscriptionUpdateRef.current;

        if (timeSinceLastUpdate > autoSendTimeoutMs) {
          console.log("Long silence detected, auto-sending message");
          stopRecording();
        }
      }, 500);

      return () => clearInterval(intervalId);
    }
  }, [isRecording, currentTranscription, stopRecording]);

  // Effect to speak assistant message when it arrives
  useEffect(() => {
    // Only speak if we have a new message, we're not already speaking or waiting,
    // and it's different from the previous message
    if (
      isActive &&
      latestAssistantMessage &&
      !isWaitingForResponse &&
      !isSpeaking &&
      latestAssistantMessage !== prevAssistantMessageRef.current
    ) {
      console.log(
        "New assistant message detected, speaking it:",
        latestAssistantMessage.slice(0, 50) + "..."
      );
      speakAssistantMessage();
    }
  }, [
    isActive,
    latestAssistantMessage,
    isWaitingForResponse,
    isSpeaking,
    speakAssistantMessage,
  ]);

  // Effect to auto-start recording after speaking
  useEffect(() => {
    if (
      shouldAutoStartRecording.current &&
      !isSpeaking &&
      isActive &&
      !isRecording &&
      !isWaitingForResponse
    ) {
      console.log("Auto-starting recording after speech");
      shouldAutoStartRecording.current = false;

      // Add a more significant delay to ensure speech is fully complete
      // and to give the user time to think about their response
      setTimeout(() => {
        if (isActive && !isRecording && !isSpeaking && !isWaitingForResponse) {
          console.log("Starting recording now...");
          startRecording();
        } else {
          console.log("State changed, not starting recording");
        }
      }, 1000);
    }
  }, [isSpeaking, isActive, isRecording, isWaitingForResponse, startRecording]);

  // Effect to start recording when voice mode is activated
  useEffect(() => {
    if (isActive && !isRecording && !isSpeaking && !isWaitingForResponse) {
      startRecording();
    }
  }, [isActive, isRecording, isSpeaking, isWaitingForResponse, startRecording]);

  // Cleanup on unmount or when deactivated
  useEffect(() => {
    return () => {
      stopVisualizer();
      cancelSilenceTimer();
    };
  }, [stopVisualizer, cancelSilenceTimer]);

  // Reset message reference when voice mode is deactivated
  useEffect(() => {
    if (!isActive) {
      prevAssistantMessageRef.current = null;
    }
  }, [isActive]);

  if (!isActive) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="fixed inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm z-50"
        onClick={(e) => {
          // Close when clicking outside the modal
          if (e.target === e.currentTarget) {
            onToggle();
          }
        }}
      >
        <motion.div
          className="bg-background rounded-3xl shadow-2xl p-8 max-w-md w-full mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold">Voice Assistant</h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="rounded-full"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Visualizer */}
          <div className="flex justify-center items-center h-32 mb-6">
            <div className="flex items-end justify-center gap-1 h-full w-full">
              {visualizerValues.map((value, index) => (
                <motion.div
                  key={index}
                  className="w-2 bg-primary rounded-full"
                  initial={{ height: 5 }}
                  animate={{ height: value }}
                  transition={{ duration: 0.1 }}
                />
              ))}
            </div>
          </div>

          {/* Status text */}
          <div className="text-center mb-6">
            {isWaitingForResponse ? (
              <p className="text-muted-foreground">Thinking...</p>
            ) : isSpeaking ? (
              <p className="text-primary">Speaking...</p>
            ) : isRecording ? (
              <p className="text-primary">Listening...</p>
            ) : (
              <p className="text-muted-foreground">Ready</p>
            )}
            {currentTranscription && isRecording && (
              <p className="mt-2 text-sm">{currentTranscription}</p>
            )}
          </div>

          {/* Control buttons */}
          <div className="flex justify-center">
            {isRecording ? (
              <Button
                size="lg"
                className="rounded-full h-16 w-16 bg-red-500 hover:bg-red-600"
                onClick={stopRecording}
                disabled={isWaitingForResponse || isSpeaking}
              >
                <MicOff className="h-6 w-6" />
              </Button>
            ) : (
              <Button
                size="lg"
                className="rounded-full h-16 w-16"
                onClick={startRecording}
                disabled={isWaitingForResponse || isSpeaking || isConnecting}
              >
                <Mic className="h-6 w-6" />
              </Button>
            )}
          </div>

          {/* LiveKit components */}
          {token && serverUrl && (
            <LiveKitRoom
              token={token}
              serverUrl={serverUrl}
              connect={true}
              audio={true}
              video={false}
              data-lk-theme="default"
            >
              {isRecording ? (
                <AudioPublisher
                  onTranscriptionReceived={handleTranscriptionUpdate}
                />
              ) : isSpeaking && latestAssistantMessage ? (
                <TTSPublisher text={latestAssistantMessage} />
              ) : null}
              <RoomAudioRenderer />
            </LiveKitRoom>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// Audio publisher component (similar to the one in audio-input.tsx)
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

// TTS publisher component
function TTSPublisher({ text }: { text: string }) {
  const room = useRoomContext();
  const [hasSentText, setHasSentText] = useState(false);
  const mounted = useRef(true);

  // Send the text to be converted to speech when the component mounts
  useEffect(() => {
    const startTTS = async () => {
      try {
        // Wait for room to be connected
        if (!room || room.state !== "connected") {
          await new Promise<void>((resolve) => {
            const onConnected = () => {
              resolve();
              room.off(RoomEvent.Connected, onConnected);
            };
            room.on(RoomEvent.Connected, onConnected);
          });
        }

        if (!mounted.current || hasSentText) return;

        console.log("Room connected, sending text for TTS...");

        // These are the exact same methods used in tts-button.tsx
        // Send text in all available formats to ensure the TTS server processes it
        await Promise.all([
          room.localParticipant.publishData(new TextEncoder().encode(text), {
            reliable: true,
          }),
          room.localParticipant.sendText(text),
          room.localParticipant.sendChatMessage(text),
        ]);

        console.log(
          "Text sent to LiveKit for TTS - audio should start playing"
        );
        setHasSentText(true);
      } catch (error) {
        console.error("Failed to send text for TTS:", error);
      }
    };

    startTTS();

    return () => {
      mounted.current = false;
    };
  }, [room, text, hasSentText]);

  return null;
}
