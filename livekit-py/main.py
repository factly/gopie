import asyncio
import logging
import atexit

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    stt,
    transcription,
)
from livekit.plugins import openai, silero

load_dotenv()

logger = logging.getLogger("transcriber")
logger.setLevel(logging.INFO)

# Keep track of active tasks and streams for proper cleanup
active_tasks = set()
active_streams = set()


def cleanup_tasks():
    """Clean up any remaining tasks at program exit"""
    for task in active_tasks:
        if not task.done() and not task.cancelled():
            task.cancel()


# Register cleanup function
atexit.register(cleanup_tasks)


async def _forward_transcription(
    stt_stream: stt.SpeechStream, stt_forwarder: transcription.STTSegmentsForwarder
):
    """Forward the transcription to the client and log the transcript in the console"""
    try:
        async for ev in stt_stream:
            if ev.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
                # you may not want to log interim transcripts, they are not final and may be incorrect
                pass
            elif ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                print(" -> ", ev.alternatives[0].text)
            elif ev.type == stt.SpeechEventType.RECOGNITION_USAGE:
                logger.debug(f"metrics: {ev.recognition_usage}")

            stt_forwarder.update(ev)
    except asyncio.CancelledError:
        logger.debug("Transcription task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
    finally:
        if stt_stream in active_streams:
            active_streams.remove(stt_stream)


async def _handle_text_message(text: str, tts: openai.TTS, source: rtc.AudioSource):
    """Handle incoming text messages by converting them to speech"""
    try:
        logger.info(f'Converting text to speech: "{text}"')
        async for output in tts.synthesize(text):
            await source.capture_frame(output.frame)
    except asyncio.CancelledError:
        logger.debug("TTS task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in TTS: {e}")


def create_task(coro):
    """Create a task and track it for cleanup"""
    task = asyncio.create_task(coro)
    active_tasks.add(task)
    task.add_done_callback(
        lambda t: active_tasks.remove(t) if t in active_tasks else None
    )
    return task


async def entrypoint(ctx: JobContext):
    logger.info("starting transcriber and TTS agent")

    # Set up STT
    stt_impl = openai.STT()
    if not stt_impl.capabilities.streaming:
        stt_impl = stt.StreamAdapter(
            stt=stt_impl,
            vad=silero.VAD.load(
                min_silence_duration=0.3,
            ),
        )

    # Set up TTS
    tts = openai.TTS(model="tts-1", voice="nova")
    source = rtc.AudioSource(tts.sample_rate, tts.num_channels)
    tts_track = rtc.LocalAudioTrack.create_audio_track("agent-tts", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE

    async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
        try:
            audio_stream = rtc.AudioStream(track)
            stt_forwarder = transcription.STTSegmentsForwarder(
                room=ctx.room, participant=participant, track=track
            )

            stt_stream = stt_impl.stream()
            active_streams.add(stt_stream)

            # Create and track the transcription forwarding task
            forward_task = create_task(
                _forward_transcription(stt_stream, stt_forwarder)
            )

            async for ev in audio_stream:
                stt_stream.push_frame(ev.frame)

        except asyncio.CancelledError:
            logger.debug("Audio stream task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
        finally:
            # Ensure stream is properly closed and task is cancelled if needed
            if stt_stream in active_streams:
                active_streams.remove(stt_stream)
            if "forward_task" in locals() and not forward_task.done():
                forward_task.cancel()

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            create_task(transcribe_track(participant, track))

    @ctx.room.on("data_received")
    def on_message_received(data_packet: rtc.DataPacket):
        # Handle incoming text messages for TTS
        print("Received data packet: ", data_packet.data)
        create_task(_handle_text_message(data_packet.data.decode(), tts, source))

    # Connect and publish TTS track
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    publication = await ctx.room.local_participant.publish_track(tts_track, options)
    await publication.wait_for_subscription()
    logger.info("TTS track published and ready")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
