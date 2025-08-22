import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
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
  const isStartingRecordingRef = useRef(false); // Ref to track if we're already starting recording

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

  // Helper to ensure clean room disconnection when disabling voice mode
  const cleanupCurrentSession = useCallback(async () => {
    // Cancel any pending operations
    cancelSilenceTimer();

    if (token && serverUrl) {
      console.log("Cleaning up LiveKit session on voice mode deactivation");
      try {
        // Wait for any ongoing operations to finish
        await new Promise((resolve) => setTimeout(resolve, 300));

        // Clear the token and server URL to disconnect
        setToken("");
        setServerUrl("");
        console.log("Successfully disconnected from LiveKit");
      } catch (error) {
        console.error("Error during LiveKit cleanup:", error);
      }
    }

    // Reset all state for a clean slate
    stopVisualizer();
    setIsRecording(false);
    setIsSpeaking(false);
    setCurrentTranscription("");
    prevAssistantMessageRef.current = null;
  }, [token, serverUrl, cancelSilenceTimer, stopVisualizer]);

  // Start recording
  const startRecording = useCallback(async () => {
    console.log("Starting recording with isRecording:", isRecording);

    // If we're already in the process of starting recording, don't start another one
    if (isStartingRecordingRef.current) {
      console.log(
        "Already starting a recording session, ignoring duplicate call"
      );
      return;
    }

    // Set the flag to indicate we're starting recording
    isStartingRecordingRef.current = true;

    try {
      // Don't disconnect, just stop recording if it's active
      if (isRecording) {
        console.log("Recording is already active, stopping first");
        cancelSilenceTimer();
        setIsRecording(false);
        stopVisualizer();

        // Clear the flag since we're not continuing with this recording attempt
        isStartingRecordingRef.current = false;

        // Don't automatically restart - this was causing infinite loops
        return;
      }

      // If we don't have an active connection, establish one
      if (!token || !serverUrl) {
        console.log("No active LiveKit connection, establishing one now");
        setCurrentTranscription(""); // Reset transcription

        // Fetch new credentials
        const credentials = await fetchToken();

        if (!credentials) {
          console.error("Failed to get LiveKit credentials");
          toast.error("Failed to start voice recording");
          isStartingRecordingRef.current = false;
          return;
        }

        // Wait a moment for credentials to be set before proceeding
        await new Promise((resolve) => setTimeout(resolve, 300));
      } else {
        console.log("Using existing LiveKit connection");
        setCurrentTranscription(""); // Reset transcription
      }

      // Set recording state
      setIsRecording(true);
      startVisualizer();
      lastTranscriptionUpdateRef.current = Date.now();

      console.log(
        "Successfully started recording session with token:",
        token ? "present" : "missing"
      );

      // Clear the flag now that we've successfully started recording
      isStartingRecordingRef.current = false;
    } catch (error) {
      console.error("Error starting recording:", error);
      isStartingRecordingRef.current = false;
    }
  }, [
    fetchToken,
    startVisualizer,
    cancelSilenceTimer,
    isRecording,
    token,
    serverUrl,
    stopVisualizer,
  ]);

  // Stop recording and send message
  const stopRecording = useCallback(async () => {
    cancelSilenceTimer();
    setIsRecording(false);
    stopVisualizer();

    // Send final transcription when stopping
    if (currentTranscription.trim()) {
      await onSendMessage(currentTranscription.trim());
    }

    // Don't disconnect from LiveKit, just stop recording
    console.log("Stopped recording but maintaining LiveKit connection");
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
  useEffect(() => {
    // Only speak if we have a new message, we're not already speaking or waiting
    if (
      isActive &&
      latestAssistantMessage &&
      !isWaitingForResponse &&
      !isSpeaking
    ) {
      // Don't speak messages we've already processed
      if (latestAssistantMessage === prevAssistantMessageRef.current) {
        console.log("Ignoring already processed message");
        return;
      }

      console.log(
        "New assistant message detected, speaking it:",
        latestAssistantMessage.slice(0, 50) + "..."
      );

      // Ensure recording is stopped without disconnecting
      if (isRecording) {
        console.log("Stopping recording before starting TTS");
        setIsRecording(false);
        cancelSilenceTimer();
        stopVisualizer();

        // Give time for recording to fully stop
        setTimeout(() => {
          startTTS();
        }, 500);
      } else {
        startTTS();
      }

      // Function to start TTS process
      async function startTTS() {
        try {
          setIsSpeaking(true);
          startVisualizer();

          // Set the message as processed
          prevAssistantMessageRef.current = latestAssistantMessage;

          if (!datasetId) {
            toast.error("Dataset ID is required for TTS");
            setIsSpeaking(false);
            stopVisualizer();
            return;
          }

          // Ensure we have an active LiveKit connection before proceeding
          if (!token || !serverUrl) {
            console.log(
              "No active LiveKit connection, establishing one for TTS"
            );
            const credentials = await fetchToken();
            if (!credentials) {
              console.error("Failed to get LiveKit credentials for TTS");
              toast.error("Failed to start text-to-speech");
              setIsSpeaking(false);
              stopVisualizer();
              return;
            }
          }

          // Find and click the most recent "Speak message" button
          console.log("Looking for the Speak message button to click...");

          // Give the DOM time to update with the new message and any previous LiveKit connections to be cleaned up
          await new Promise((resolve) => setTimeout(resolve, 500));

          // Try to find the button inside the latest assistant message
          const assistantMessages = document.querySelectorAll(
            '[data-message-role="assistant"]'
          );
          if (assistantMessages.length === 0) {
            console.warn("No assistant messages found in the DOM");
            setIsSpeaking(false);
            stopVisualizer();
            return;
          }

          // Get the last assistant message element
          const latestMessageElement =
            assistantMessages[assistantMessages.length - 1];
          console.log(
            "Found latest assistant message with ID:",
            latestMessageElement.getAttribute("id")
          );

          // Find the TTS button within this message by container ID
          const messageId =
            latestMessageElement.getAttribute("data-message-id");
          const ttsButtonContainer = document.getElementById(
            `tts-button-container-${messageId}`
          );

          if (!ttsButtonContainer) {
            console.warn(
              "Could not find TTS button container for message ID:",
              messageId
            );
            setIsSpeaking(false);
            stopVisualizer();
            return;
          }

          // Find the actual button within the container and ensure it's not disabled
          let ttsButton = ttsButtonContainer.querySelector(
            "button:not([disabled])"
          );

          // If button is not found or is disabled, wait a bit longer and try again
          if (!ttsButton) {
            console.log("TTS button is not ready yet, waiting...");
            await new Promise((resolve) => setTimeout(resolve, 1000));
            ttsButton = ttsButtonContainer.querySelector(
              "button:not([disabled])"
            );

            if (!ttsButton) {
              console.warn("Could not find enabled TTS button after waiting");
              setIsSpeaking(false);
              stopVisualizer();
              return;
            }

            console.log("Found Speak message button after waiting");
          }

          // Click the button to start TTS
          console.log("Clicking Speak message button...");
          (ttsButton as HTMLButtonElement).click();

          // Calculate wait time based on message length
          const wordsPerMinute = 150;
          const wordCount = latestAssistantMessage
            ? latestAssistantMessage.split(/\s+/).length
            : 0;
          const estimatedReadingTime = (wordCount / wordsPerMinute) * 60 * 1000;
          const waitTime = Math.max(3000, estimatedReadingTime);

          console.log(
            `Waiting ${Math.round(waitTime)}ms for speech to complete...`
          );
          await new Promise((resolve) => setTimeout(resolve, waitTime));

          // Clear speaking state when TTS is done
          setIsSpeaking(false);

          // Auto-start recording after speech completes
          if (isActive) {
            console.log("Scheduling recording to start after speech");
            shouldAutoStartRecording.current = true;

            // Force a new LiveKit connection to reset the STT service
            if (token && serverUrl) {
              console.log("Resetting LiveKit connection for recording");

              // First disconnect
              try {
                console.log("Disconnecting from current LiveKit session");
                // Remove token/serverUrl briefly to force a clean disconnect
                setToken("");
                setServerUrl("");

                // Wait for disconnection to complete
                await new Promise((resolve) => setTimeout(resolve, 500));

                // Then fetch new token and reconnect
                console.log("Fetching new LiveKit credentials for recording");
                const newCredentials = await fetchToken();

                // Log the result of fetching new credentials
                if (newCredentials) {
                  console.log("Successfully obtained new LiveKit credentials");
                } else {
                  console.warn(
                    "Could not obtain new LiveKit credentials, but will try to continue"
                  );
                }

                // Wait for the new credentials to be set
                await new Promise((resolve) => setTimeout(resolve, 500));

                // Wait a moment before starting a new recording session
                // Use a single timeout to start recording rather than multiple paths
                if (!isStartingRecordingRef.current) {
                  setTimeout(async () => {
                    if (
                      isActive &&
                      !isRecording &&
                      !isSpeaking &&
                      !isWaitingForResponse &&
                      !isStartingRecordingRef.current
                    ) {
                      console.log("Starting recording after TTS completed");
                      await startRecording();
                    } else {
                      console.log(
                        "Conditions not met for starting recording after TTS",
                        {
                          isActive,
                          isRecording,
                          isSpeaking,
                          isWaitingForResponse,
                          isStartingRecordingRef:
                            isStartingRecordingRef.current,
                        }
                      );
                    }
                  }, 1000);
                }
              } catch (error) {
                console.error("Error resetting LiveKit connection:", error);
                // Only attempt to restart if not already starting a recording session
                if (!isStartingRecordingRef.current) {
                  setTimeout(async () => {
                    if (
                      isActive &&
                      !isRecording &&
                      !isSpeaking &&
                      !isWaitingForResponse &&
                      !isStartingRecordingRef.current
                    ) {
                      console.log("Starting recording after error with reset");
                      await startRecording();
                    } else {
                      console.log(
                        "Conditions not met for starting recording after error",
                        {
                          isActive,
                          isRecording,
                          isSpeaking,
                          isWaitingForResponse,
                          isStartingRecordingRef:
                            isStartingRecordingRef.current,
                        }
                      );
                    }
                  }, 1000);
                }
              }
            }
          }
        } catch (error) {
          console.error("Failed to speak message:", error);
          toast.error("Failed to speak message");
          setIsSpeaking(false);
          stopVisualizer();
        }
      }
    }
  }, [
    isActive,
    latestAssistantMessage,
    isWaitingForResponse,
    isSpeaking,
    isRecording,
    datasetId,
    startVisualizer,
    stopVisualizer,
    token,
    serverUrl,
    fetchToken,
    cancelSilenceTimer,
    startRecording,
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

  // Auto-start recording after speech completes
  useEffect(() => {
    if (
      shouldAutoStartRecording.current &&
      !isSpeaking &&
      isActive &&
      !isRecording &&
      !isWaitingForResponse &&
      !isStartingRecordingRef.current
    ) {
      console.log("Auto-starting recording after speech");
      shouldAutoStartRecording.current = false;

      // Add a delay to ensure speech is fully complete
      // and to give the user time to think about their response
      setTimeout(() => {
        if (
          isActive &&
          !isRecording &&
          !isSpeaking &&
          !isWaitingForResponse &&
          !isStartingRecordingRef.current
        ) {
          console.log("Starting recording now...");
          // We don't need to reconnect, just start recording with existing connection
          startRecording();
        } else {
          console.log("State changed, not starting recording", {
            isActive,
            isRecording,
            isSpeaking,
            isWaitingForResponse,
            isStartingRecordingRef: isStartingRecordingRef.current,
          });
        }
      }, 1000);
    }
  }, [isSpeaking, isActive, isRecording, isWaitingForResponse, startRecording]);

  // Effect to handle voice mode activation/deactivation
  useEffect(() => {
    if (isActive) {
      // Only establish connection when voice mode is activated if we're not already speaking
      if (
        (!token || !serverUrl) &&
        !isSpeaking &&
        !isStartingRecordingRef.current
      ) {
        console.log("Voice mode activated, establishing LiveKit connection");
        fetchToken().then(() => {
          if (
            !isSpeaking &&
            !isWaitingForResponse &&
            !isStartingRecordingRef.current
          ) {
            startRecording();
          }
        });
      } else if (
        !isRecording &&
        !isSpeaking &&
        !isWaitingForResponse &&
        !isStartingRecordingRef.current
      ) {
        startRecording();
      }
    } else {
      // Clean up completely when voice mode is deactivated
      console.log("Voice mode deactivated, cleaning up completely");
      cleanupCurrentSession();
    }
  }, [
    isActive,
    token,
    serverUrl,
    fetchToken,
    startRecording,
    cleanupCurrentSession,
    isRecording,
    isSpeaking,
    isWaitingForResponse,
  ]);

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

  // Monitor connection status and ensure we're in the right state
  useEffect(() => {
    let checkInterval: NodeJS.Timeout | null = null;

    if (isActive) {
      // Check every 2 seconds if our connection and state are aligned
      checkInterval = setInterval(() => {
        // If voice mode is active but we don't have a connection, establish one
        if (!token || !serverUrl) {
          console.log(
            "Voice mode active but no LiveKit connection, establishing one"
          );
          fetchToken();
          return;
        }

        // If we should be recording but aren't, restart recording
        if (
          !isRecording &&
          !isSpeaking &&
          !isWaitingForResponse &&
          !isStartingRecordingRef.current
        ) {
          console.log("Should be recording but not - starting recording");
          startRecording();
        }
      }, 2000);
    }

    return () => {
      if (checkInterval) {
        clearInterval(checkInterval);
      }
    };
  }, [
    isActive,
    isRecording,
    token,
    serverUrl,
    isSpeaking,
    isWaitingForResponse,
    fetchToken,
    startRecording,
  ]);

  if (!isActive) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 flex items-center justify-center bg-black/70 z-40"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            onToggle();
          }
        }}
      >
        <motion.div
          className="relative flex flex-col items-center justify-center"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          transition={{ type: "spring", damping: 25 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="absolute -top-12 right-0 h-8 w-8 bg-white/10 hover:bg-white/20 z-10"
          >
            <X className="h-4 w-4 text-white" />
          </Button>

          {/* Main container */}
          <div className="bg-black/30 backdrop-blur-md w-[300px] overflow-hidden border border-white/10">
            {/* Status area */}
            <div className="flex flex-col items-center justify-center py-6 px-4">
              {currentTranscription && isRecording ? (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-white/90 text-center mb-4 text-sm max-h-20 overflow-y-auto"
                >
                  {currentTranscription}
                </motion.p>
              ) : (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-white/90 text-center mb-4 text-sm"
                >
                  {isWaitingForResponse
                    ? "Thinking..."
                    : isSpeaking
                    ? "Speaking..."
                    : "Listening..."}
                </motion.p>
              )}
            </div>

            {/* Waveform visualization */}
            <div className="w-full h-16 flex items-center justify-center bg-black/40 px-6 py-3">
              <div className="w-full h-full flex items-center justify-center gap-[2px]">
                {visualizerValues.map((value, index) => {
                  const height = `${Math.max(4, value)}px`;
                  return (
                    <motion.div
                      key={index}
                      className="bg-white/70 w-1"
                      style={{ height }}
                      initial={{ height: "4px" }}
                      animate={{ height }}
                      transition={{ duration: 0.1 }}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          {/* LiveKitRoom components */}
          {token && serverUrl && (
            <LiveKitRoom
              token={token}
              serverUrl={serverUrl}
              connect={true}
              audio={true}
              video={false}
              data-lk-theme="default"
              onConnected={() =>
                console.log("LiveKit room connected successfully")
              }
              onDisconnected={() => {
                console.log("LiveKit room disconnected");
                if (isRecording) {
                  console.log(
                    "Disconnected while recording - will attempt to reconnect"
                  );
                  startRecording();
                }
              }}
            >
              {isRecording ? (
                <AudioPublisher
                  onTranscriptionReceived={handleTranscriptionUpdate}
                />
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
  const localTranscriptionBuffer = useRef<string[]>([]);
  const lastTranscriptionTime = useRef<number>(Date.now());
  const hasReceivedTranscription = useRef<boolean>(false);

  // Start publishing audio track when component mounts
  useEffect(() => {
    let mounted = true;
    let cleanup: (() => void) | undefined;

    async function startAudio() {
      if (!localParticipant || !room) return;

      try {
        console.log("AudioPublisher: Starting audio track publishing");

        // Wait for room to be connected
        if (room.state !== "connected") {
          console.log("AudioPublisher: Waiting for room connection...");
          await new Promise<void>((resolve) => {
            const onConnected = () => {
              resolve();
              room.off(RoomEvent.Connected, onConnected);
            };
            room.on(RoomEvent.Connected, onConnected);
          });
          console.log(
            "AudioPublisher: Room connected, proceeding with audio setup"
          );
        }

        // Create and publish the track
        console.log("AudioPublisher: Creating local audio track");
        const track = await createLocalAudioTrack({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        });

        if (!mounted) {
          track.stop();
          return;
        }

        console.log("AudioPublisher: Publishing track to LiveKit");
        const publication = await localParticipant.publishTrack(track);

        if (!mounted) {
          publication.track?.stop();
          return;
        }

        console.log("AudioPublisher: Audio track published successfully");
        setAudioTrack({
          participant: localParticipant,
          publication,
          source: Track.Source.Microphone,
        });

        // Set up a check to see if we're receiving transcriptions
        const transcriptionCheckInterval = setInterval(() => {
          const now = Date.now();
          const timeSinceLastTranscription =
            now - lastTranscriptionTime.current;

          // After 5 seconds of no transcriptions while recording, log a warning
          if (timeSinceLastTranscription > 5000) {
            console.warn(
              `AudioPublisher: No transcription received in ${Math.round(
                timeSinceLastTranscription / 1000
              )}s`
            );

            // If we've never received a transcription after 10 seconds, try reconnecting
            if (
              !hasReceivedTranscription.current &&
              timeSinceLastTranscription > 10000
            ) {
              console.error(
                "AudioPublisher: Never received any transcription, may need to reconnect"
              );
            }
          }
        }, 5000);

        cleanup = () => {
          console.log("AudioPublisher: Cleaning up audio track");
          if (transcriptionCheckInterval) {
            clearInterval(transcriptionCheckInterval);
          }
          track.stop();
          publication.track?.stop();
          localParticipant.unpublishTrack(track);
        };
      } catch (error) {
        console.error("Error publishing audio track:", error);
        toast.error("Failed to start audio recording");

        // Try to restart after a short delay if there was an error
        setTimeout(() => {
          if (mounted) {
            console.log(
              "AudioPublisher: Attempting to restart audio after error"
            );
            startAudio();
          }
        }, 2000);
      }
    }

    startAudio();

    return () => {
      mounted = false;
      cleanup?.();
      // Clear transcription buffer on cleanup
      localTranscriptionBuffer.current = [];
      hasReceivedTranscription.current = false;
    };
  }, [localParticipant, room]);

  // Handle transcriptions with buffering
  useTrackTranscription(audioTrack, {
    bufferSize: 5,
    onTranscription: (newSegments) => {
      if (newSegments.length > 0) {
        const latestSegment = newSegments[newSegments.length - 1];
        if (latestSegment.text) {
          console.log(
            "AudioPublisher: Received transcription:",
            latestSegment.text
          );

          // Mark that we've received a transcription and update the time
          hasReceivedTranscription.current = true;
          lastTranscriptionTime.current = Date.now();

          // Update buffer with new text
          localTranscriptionBuffer.current.push(latestSegment.text);
          // Keep only last 5 segments
          if (localTranscriptionBuffer.current.length > 5) {
            localTranscriptionBuffer.current.shift();
          }
          // Combine all segments and send
          const fullText = localTranscriptionBuffer.current.join(" ");
          console.log("AudioPublisher: Sending full transcription:", fullText);
          onTranscriptionReceived(fullText);
        }
      }
    },
  });

  return null;
}
